"""Step `watch_ads`: xem rewarded ad cho toi khi cong mo khoa bien mat.

So ad can xem KHONG co dinh: AIP922 3.5.0 doi tu "Watch Ads (0/3)" sang
"(0/5)" theo Remote Config, flow viet cung 3 lan xem thi gen khong chay va ca
chuoi Result phia sau lai hut. Nen vong lap doc chinh man: con nut thi xem
tiep, nut bien mat (app tu gen) thi xong.

Ad khong ve (bam nut ma khong co man quang cao nao hien) thi MUA SUB TEST thay
vi ngoi cho: may test la license tester, sheet Play ghi "Test card, always
approves", khong mat tien that. Mua xong app gen thang.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time

from .adb_parsers import AdbError
from .device_actions import Selector, tap
from .flow_screen import dong_man_chan, man_chan, nodes, wait_text
from .ui_cache import CayUI

log = logging.getLogger(__name__)

# Chan tren so vong: cong mo khoa thuc te can 3-5 ad; qua muc nay la man ket.
TOI_DA_AD = 12
# Bam nut roi cho man quang cao hien. Rewarded load cham hon interstitial.
CHO_AD_HIEN = 15.0
# Rewarded dai ~30s, nut dong hien tre; cho rong tay roi moi bao loi.
CHO_AD_XONG = 75.0
# Lan kiem nut dau tien: nut Watch Ads hien tre hon sheet (cho rewarded tai).
CHO_NUT_DAU = 15.0
# Ad ket khong dong duoc bang nut: so lan bam BACK truoc khi bao loi.
BACK_TOI_DA = 3
# Kiem nut con khong: sheet hien lai sau khi dong ad mat 1-2s.
CHO_NUT = 6.0

# Duong mua sub: nut Premium tren sheet -> paywall RevenueCat -> sheet Play.
NUT_PREMIUM = Selector(text="Unlock With Premium", alt=("Go Pro*", "Go Premium"))
DUONG_MUA = (
    Selector(text="Weekly"),
    Selector(text="Subscribe Now", alt=("Continue",)),
    # Sheet Play dich theo ngon ngu tai khoan, khong theo app.
    Selector(text="Subscribe", alt=("Đăng ký",)),
)
CHO_SHEET_PLAY = 20.0
# Chu "Subscribe" cung nam trong "Subscribe Now" cua paywall: cho dau hieu
# rieng cua sheet Play roi moi bam, khong thi bam truot luc paywall chua dong.
DAU_SHEET_PLAY = ("Test card", "Thẻ thử nghiệm")


async def _cho_ad_hien(client, serial: str) -> bool:
    het = time.monotonic() + CHO_AD_HIEN
    while time.monotonic() < het:
        if (await man_chan(client, serial))["man_ads"]:
            return True
        await asyncio.sleep(1.0)
    return False


async def _bam(client, serial, metrics, cay: CayUI, sel: Selector,
               timeout: float, cho: tuple[str, ...] = ()) -> None:
    """Cho `cho` (mac dinh chinh nut) hien roi bam nut. Het gio -> AdbError."""
    cho = cho or tuple(x.rstrip("*") for x in sel.needles)
    if not await wait_text(client, serial, metrics, cho, timeout, cay,
                           don_man_chan=False):
        raise AdbError(f"Mua sub: không thấy nút {sel.label()} sau {timeout:g}s.")
    cay.bo()
    await tap(client, serial, await nodes(client, serial, metrics, cay), sel)
    cay.bo()
    await asyncio.sleep(2.0)


async def mua_sub_neu_chua_co(client, serial: str, metrics, cay: CayUI) -> str:
    """Step `buy_sub`: sheet mo khoa dang hien thi mua sub, khong thi da co sub.

    Dung cho case CAN sub (vd limit_reached_view voi sub_daily_limit): khong co
    sub thi app hien sheet ads thay vi bao het luot.
    """
    if not await wait_text(client, serial, metrics,
                           tuple(x.rstrip("*") for x in NUT_PREMIUM.needles),
                           CHO_NUT, cay, don_man_chan=False):
        return "không thấy sheet mở khoá - đã có sub"
    await mua_sub(client, serial, metrics, cay)
    return "đã mua sub test"


async def mua_sub(client, serial: str, metrics, cay: CayUI) -> None:
    """Bam Premium tren sheet roi mua goi Weekly bang the test."""
    log.info("Ad khong ve - mua sub test")
    await _bam(client, serial, metrics, cay, NUT_PREMIUM, CHO_NUT)
    await _bam(client, serial, metrics, cay, DUONG_MUA[0], 15.0)
    await _bam(client, serial, metrics, cay, DUONG_MUA[1], 5.0)
    await _bam(client, serial, metrics, cay, DUONG_MUA[2], CHO_SHEET_PLAY,
               DAU_SHEET_PLAY)
    # Mua xong sheet mo khoa VAN NAM DE len man (chi con nut Premium) va chan
    # moi cu bam sau - do that 05/10 o luong nhac. BACK dong no (ban
    # unlock_sheet_close) va tra ve man/popup truoc do.
    await asyncio.sleep(3.0)
    cay.bo()
    if await wait_text(client, serial, metrics,
                       tuple(x.rstrip("*") for x in NUT_PREMIUM.needles),
                       CHO_NUT, cay, don_man_chan=False):
        await client.input_keyevent(serial, "BACK")
        cay.bo()
        await asyncio.sleep(2.0)


# "Watch Ads (3/5)" -> (3, 5). Nut khong ghi so thi khong biet ad nao la cuoi.
SO_AD = re.compile(r"(\d+)\s*/\s*(\d+)")


async def _dem(client, serial, metrics, cay: CayUI,
               nut: tuple[str, ...]) -> tuple[int, int] | None:
    for node in await nodes(client, serial, metrics, cay):
        if any(node.text.casefold().startswith(n.casefold()) for n in nut):
            khop = SO_AD.search(node.text)
            return (int(khop[1]), int(khop[2])) if khop else None
    return None


async def xem_ads(client, serial: str, metrics, nut: tuple[str, ...],
                  cay: CayUI, de_lai_cuoi: bool = False, truoc_dong_cuoi=None) -> str:
    """Xem ad toi khi nut `nut` bien mat. Tra mo ta duong da di (ghi notes).

    `de_lai_cuoi`: bam ad CUOI roi tra ve ngay khi no hien, KHONG dong - buoc
    sau ngat mang trong luc ad dang chay de ep gen_fail no_network.

    `truoc_dong_cuoi`: goi NGAY TRUOC cu dong ad cuoi (hoac sau khi mua sub) -
    moc cu kich hoat cua gen_start.
    """
    da_xem = 0
    for vong in range(TOI_DA_AD):
        cay.bo()
        # Lan dau cho lau hon: sheet hien truoc, nut Watch Ads chi hien khi
        # rewarded ad tai xong (do that 05/10: sheet chi co nut Premium).
        if not await wait_text(client, serial, metrics, nut,
                               CHO_NUT_DAU if vong == 0 else CHO_NUT, cay,
                               don_man_chan=False):
            premium = await wait_text(
                client, serial, metrics,
                tuple(x.rstrip("*") for x in NUT_PREMIUM.needles), 1.0, cay,
                don_man_chan=False)
            if premium and de_lai_cuoi:
                raise AdbError("Sheet mở khoá không có nút Watch Ads (ad chưa tải) - "
                               "không giữ được ad cuối để ngắt mạng.")
            if premium:
                await mua_sub(client, serial, metrics, cay)
                if truoc_dong_cuoi is not None:
                    await truoc_dong_cuoi()
                return f"xem {da_xem} ad, sheet hết nút Watch Ads - đã mua sub test"
            if de_lai_cuoi:
                raise AdbError(f"Nút {nut[0]!r} biến mất trước ad cuối "
                               f"(đã xem {da_xem}) - không còn ad để giữ lại.")
            return f"xem {da_xem} ad thì cổng mở"
        dem = await _dem(client, serial, metrics, cay, nut)
        cuoi = dem is not None and dem[0] + 1 >= dem[1]
        sel = Selector(text=f"{nut[0]}*")
        await tap(client, serial, await nodes(client, serial, metrics, cay), sel)
        cay.bo()
        if not await _cho_ad_hien(client, serial):
            if de_lai_cuoi:
                raise AdbError("Ad cuối không về - không ép được gen_fail lúc đang xem ad.")
            await mua_sub(client, serial, metrics, cay)
            if truoc_dong_cuoi is not None:
                await truoc_dong_cuoi()
            return f"xem {da_xem} ad rồi ad không về - đã mua sub test"
        if de_lai_cuoi and cuoi:
            return f"xem {da_xem} ad, ad cuối ({dem[1]}/{dem[1]}) để chạy, chưa đóng"
        try:
            await dong_man_chan(client, serial, metrics, cay, CHO_AD_XONG,
                                truoc_bam=truoc_dong_cuoi if cuoi else None)
        except AdbError:
            # Vai rewarded ad bam X ma khong thoat (do that 05/10, ket 75s) -
            # BACK thuong thoat duoc. So ad that van doc lai tu nut o vong sau.
            log.info("Ad khong dong duoc bang nut - bam BACK")
        for _ in range(BACK_TOI_DA):
            if not (await man_chan(client, serial))["man_ads"]:
                break
            await client.input_keyevent(serial, "BACK")
            cay.bo()
            await asyncio.sleep(2.0)
        if (await man_chan(client, serial))["man_ads"]:
            raise AdbError(f"Ad thứ {da_xem + 1} chờ {CHO_AD_XONG:g}s, bấm BACK "
                           f"{BACK_TOI_DA} lần vẫn không thoát.")
        da_xem += 1
        if cuoi:
            # Biet chac la ad cuoi thi tra ve NGAY: ngoi cho them CHO_NUT de
            # thay nut bien mat thi gen_start/gen_success da ban xong trong luc
            # do - roi vao cua so case nay thay vi case sau (do that 05/10).
            return f"xem {da_xem} ad ({dem[1]}/{dem[1]}) thì cổng mở"
    raise AdbError(f"Xem {TOI_DA_AD} ad mà nút {nut[0]!r} vẫn còn.")
