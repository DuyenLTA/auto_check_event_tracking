"""Doc man hinh cho flow: lay cay UI, cho mot chuoi, cho mot nut hien ra.

Tach khoi `event_flow_run` vi day la phan DOC, con ben kia la phan LAM. Moi lan
doc ton ~2.2s (`uiautomator dump`) nen cache va vong cho deu nam o day - sua mot
cho, ca hai loai man chan duong (quang cao, dialog quyen) huong theo.
"""

from __future__ import annotations

import asyncio
import logging
import time

from .ad_close import tim_nut_dong
from .adb_foreground_parse import la_man_quang_cao
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


async def nodes(client, serial: str, metrics, cay: CayUI | None = None
                 ) -> list[DeviceNode]:
    if cay is not None and cay.con_dung_duoc():
        return cay.nodes
    nodes = parse_dump(await client.dump_ui(serial), metrics)
    if cay is not None:
        cay.giu(nodes)
    return nodes


async def dang_trong_quang_cao(client, serial: str) -> bool:
    """Man dang hien co phai man cua SDK quang cao khong. Loi -> coi nhu khong.

    Doc `dumpsys activity activities` chu khong doc focus: man quang cao chay
    TRONG process app nen package van la package app.
    """
    try:
        return la_man_quang_cao(await client.top_activity(serial))
    except Exception:            # noqa: BLE001 - khong doc duoc thi cu coi la man app
        return False


async def bam_node(client, serial: str, node: DeviceNode) -> None:
    """Bam vao TAM node - goc tren-trai co the nam ngoai vung bam duoc."""
    box = node.bounds_px
    await client.input_tap(serial, (box.left + box.right) / 2,
                           (box.top + box.bottom) / 2)


async def wait_text(client, serial: str, metrics, needle: str,
                     timeout: float, cay: CayUI | None = None, *,
                     don_man_chan: bool = True) -> bool:
    """Cho mot chuoi xuat hien tren man. Het gio -> False, nguoi goi tu xu.

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
    folded = needle.casefold()
    # Dem bang DONG HO THAT, khong tru dan theo POLL: mot vong lap ton
    # (dump 2.2s + POLL) nhung chi tru POLL, nen `timeout: 25` tung chay
    # ~390 giay that - do dung mot luot cham 611s.
    het_gio = time.monotonic() + max(0.0, timeout)
    da_don = 0
    while True:
        if cay is not None:
            cay.bo()          # cho thi phai doc lai that, khong dung cay cu
        tren_man = await nodes(client, serial, metrics, cay)
        for node in tren_man:
            if folded in node.text.casefold() or folded in node.content_desc.casefold():
                return True
        if don_man_chan and da_don < MAN_CHAN_TOI_DA:
            nut = tim_nut_dong(
                tren_man, chi_chac=True,
                man_ads=await dang_trong_quang_cao(client, serial))
            if nut is not None:
                log.info("Cho %r: don man chan bang %s", needle, nut.label)
                await bam_node(client, serial, nut)
                da_don += 1
                het_gio = time.monotonic() + max(0.0, timeout)
                if cay is not None:
                    cay.bo()
                await asyncio.sleep(DONG_SETTLE)
                continue
        if time.monotonic() >= het_gio:
            return False
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
