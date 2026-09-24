"""Doc man hinh cho flow: lay cay UI, cho mot chuoi, cho mot nut hien ra.

Tach khoi `event_flow_run` vi day la phan DOC, con ben kia la phan LAM. Moi lan
doc ton ~2.2s (`uiautomator dump`) nen cache va vong cho deu nam o day - sua mot
cho, ca hai loai man chan duong (quang cao, dialog quyen) huong theo.
"""

from __future__ import annotations

import asyncio
import logging
import time

from .tu_dien_man_he_thong import no_bien_the
from .ad_close import tim_nut_dong
from .adb_parsers import AdbError
from .adb_foreground_parse import la_man_paywall, la_man_quang_cao
from .models import DeviceNode
from .ui_cache import CayUI
from .ui_dump import parse_dump

log = logging.getLogger(__name__)

# Chu ky doc lai cay UI khi cho. `uiautomator dump` da mat ~2.2s tren may that
# nen ban than no la cai ham nhip; ngu them nua chi keo dai luot cham.
POLL = 0.15

# So man chan duong toi da ma `wait_text` tu don trong mot lan cho. Quang cao
# app nay xep hang: splash -> interstitial -> paywall. Khong chan so lan thi
# mot chuoi quang cao vo tan giu vong cho song mai.
MAN_CHAN_TOI_DA = 3
# Cho animation dong chay xong roi hay doc lai cay UI: doc ngay la doc duoc
# lop dang bay ra, va lan sau lai thay "con nut dong" o day.
DONG_SETTLE = 1.0
# Nut X cua paywall hien TRE vai giay - co khi da nam trong cay UI nhung bam
# chua an. Dang o paywall thi cho it nhat chung nay, du `close_ad` khai
# timeout ngan hon: paywall khong tu bien mat, di tiep la ca case ket.
PAYWALL_CHO_X = 15.0


async def nodes(client, serial: str, metrics, cay: CayUI | None = None
                 ) -> list[DeviceNode]:
    if cay is not None and cay.con_dung_duoc():
        return cay.nodes
    nodes = parse_dump(await client.dump_ui(serial), metrics)
    if cay is not None:
        cay.giu(nodes)
    return nodes


async def man_chan(client, serial: str) -> dict[str, bool]:
    """Man dang hien la quang cao hay paywall, doc tu TEN ACTIVITY.

    Tra ve dung kwargs cua `tim_nut_dong` (`man_ads`, `man_paywall`). Doc
    `dumpsys activity activities` chu khong doc focus: man quang cao va paywall
    chay TRONG process app nen package van la package app. Ten activity khong
    doi theo ngon ngu, con chu tren man thi co. Loi -> coi nhu man app.
    """
    try:
        activity = await client.top_activity(serial)
    except Exception:            # noqa: BLE001 - khong doc duoc thi cu coi la man app
        activity = None
    return {"man_ads": la_man_quang_cao(activity),
            "man_paywall": la_man_paywall(activity)}


async def bam_node(client, serial: str, node: DeviceNode) -> None:
    """Bam vao TAM node - goc tren-trai co the nam ngoai vung bam duoc."""
    box = node.bounds_px
    await client.input_tap(serial, (box.left + box.right) / 2,
                           (box.top + box.bottom) / 2)


async def wait_text(client, serial: str, metrics, needle,
                     timeout: float, cay: CayUI | None = None, *,
                     don_man_chan: bool = True) -> bool:
    """Cho mot chuoi xuat hien tren man. Het gio -> False, nguoi goi tu xu.

    `needle` la mot chuoi, hoac nhieu BIEN THE NGON NGU cua cung mot thu -
    thay cai nao cung tinh la thay. Chuoi tren man he thong doi theo locale
    cua MAY: do duoc tren may vi-VN, picker anh hien "Ảnh được chụp lúc..."
    trong khi flow cho "Photo taken on" va ngoi het 30 giay.

    Man chan duong (quang cao, paywall) co the len SAU khi cac buoc `close_ad`
    da het han cho, va luc do vong cho nay chi biet ngoi nhin no het gio roi
    bao "khong thay chu" - do duoc tren may that: paywall len muon, case bao
    Chua test trong khi app chang sai gi. Nen thay vi ngoi nhin, thay nut dong
    thi bam luon.

    Chi don man chan theo mau CHAC (`chi_chac=True`): man dang cho co the co
    nut "Close" cua chinh no - popup Add Widget la vi du - bam vao do la tu tay
    dong cai man vua doi duoc.

    Dong duoc mot man thi GIA HAN them `timeout`: cai man chan da an mat phan
    lon han cho, khong gia han thi vua don xong da het gio. Chan bang
    MAN_CHAN_TOI_DA de mot chuoi quang cao vo tan khong giu vong nay song mai.
    """
    bien_the = (needle,) if isinstance(needle, str) else tuple(needle)
    # No them cac thu tieng khac cua cung chuoi do: `wait_text: Xong` tren may
    # en-US van thay "Done". Chu khong co trong tu dien thi giu nguyen.
    bien_the = tuple(dict.fromkeys(
        x for chu in bien_the for x in no_bien_the(chu)))
    folded = [x.casefold() for x in bien_the if x]
    # Dem bang DONG HO THAT, khong tru dan theo POLL: mot vong lap ton
    # (dump 2.2s + POLL) nhung chi tru POLL, nen `timeout: 25` tung chay
    # ~390 giay that - do dung mot luot cham 611s.
    het_gio = time.monotonic() + max(0.0, timeout)
    da_don = 0
    da_gia_han_paywall = False
    while True:
        if cay is not None:
            cay.bo()          # cho thi phai doc lai that, khong dung cay cu
        tren_man = await nodes(client, serial, metrics, cay)
        for node in tren_man:
            chu = node.text.casefold()
            mo_ta = node.content_desc.casefold()
            if any(f in chu or f in mo_ta for f in folded):
                return True
        if don_man_chan and da_don < MAN_CHAN_TOI_DA:
            man = await man_chan(client, serial)
            nut = tim_nut_dong(tren_man, chi_chac=True, **man)
            if nut is not None:
                log.info("Cho %s: don man chan bang %s", bien_the, nut.label)
                await bam_node(client, serial, nut)
                # Paywall: X hien tre, bam som thi khong an va van dung o
                # paywall. Khong tinh vao MAN_CHAN_TOI_DA (khong thi ba cu bam
                # hut da het suat), va chi gia han MOT lan de khong cho mai.
                if man["man_paywall"]:
                    if not da_gia_han_paywall:
                        da_gia_han_paywall = True
                        het_gio = max(het_gio, time.monotonic() + PAYWALL_CHO_X)
                else:
                    da_don += 1
                    het_gio = time.monotonic() + max(0.0, timeout)
                if cay is not None:
                    cay.bo()
                await asyncio.sleep(DONG_SETTLE)
                continue
        if time.monotonic() >= het_gio:
            return False
        await asyncio.sleep(POLL)


async def dong_man_chan(client, serial: str, metrics, cay: CayUI | None,
                        timeout: float) -> DeviceNode | None:
    """Cho roi dong quang cao / paywall dang chan duong. Tra nut da bam, hoac
    None neu het `timeout` ma man van sach - khong co gi chan la binh thuong.

    Xet lai TEN ACTIVITY moi vong, khong chot tu dau: paywall hay len sau
    interstitial, luc buoc nay bat dau man con la quang cao hoac man app.

    Rieng paywall: cho X toi thieu PAYWALL_CHO_X, bam xong phai THOAT khoi
    activity paywall moi tinh la dong - X hien tre, bam som la khong an. Het
    gio ma van ket o paywall thi bao loi ngay tai day, thay vi de buoc sau
    ngoi cho sau lung paywall roi bao "khong thay chu".
    """
    het_gio = time.monotonic() + max(0.0, timeout)
    da_gia_han = False
    da_bam: DeviceNode | None = None
    while True:
        man = await man_chan(client, serial)
        if man["man_paywall"] and not da_gia_han:
            da_gia_han = True
            het_gio = max(het_gio, time.monotonic() + PAYWALL_CHO_X)
        if da_bam is not None and not man["man_paywall"]:
            return da_bam                   # bam X xong da ra khoi paywall
        if cay is not None:
            cay.bo()
        nut = tim_nut_dong(await nodes(client, serial, metrics, cay), **man)
        if nut is not None:
            await bam_node(client, serial, nut)
            log.info("Da dong %s bang %s",
                     "paywall" if man["man_paywall"] else "quang cao", nut.label)
            if cay is not None:
                cay.bo()
            await asyncio.sleep(DONG_SETTLE)
            if not man["man_paywall"]:
                return nut
            da_bam = nut                    # vong sau kiem da thoat chua
        if time.monotonic() >= het_gio:
            if man["man_paywall"]:
                ly_do = ("bấm nút X mà vẫn chưa thoát" if da_bam is not None
                         else "không tìm ra nút X")
                raise AdbError(f"Kẹt ở paywall: chờ {PAYWALL_CHO_X:g}s, {ly_do}.")
            return None
        await asyncio.sleep(POLL)


async def cho_nut(client, serial: str, metrics, cay, timeout: float, tim):
    """Node dau tien ma `tim` nhan ra, cho toi `timeout` giay. Het gio -> None.

    `tim` la ham loc tren cay UI (tim_nut_dong, tim_nut_cho_phep...). Truyen vao
    thay vi viet cung: hai loai man chan duong (quang cao va dialog quyen) can
    y het mot vong cho, chi khac cai nhin vao cay.
    """
    het_gio = time.monotonic() + max(0.0, timeout)
    while True:
        if cay is not None:
            cay.bo()
        node = tim(await nodes(client, serial, metrics, cay))
        if node is not None or time.monotonic() >= het_gio:
            return node
        await asyncio.sleep(POLL)
