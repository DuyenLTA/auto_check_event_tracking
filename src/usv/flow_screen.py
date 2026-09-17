"""Doc man hinh cho flow: lay cay UI, cho mot chuoi, cho mot nut hien ra.

Tach khoi `event_flow_run` vi day la phan DOC, con ben kia la phan LAM. Moi lan
doc ton ~2.2s (`uiautomator dump`) nen cache va vong cho deu nam o day - sua mot
cho, ca hai loai man chan duong (quang cao, dialog quyen) huong theo.
"""

from __future__ import annotations

import asyncio
import time

from .models import DeviceNode
from .ui_cache import CayUI
from .ui_dump import parse_dump

# Chu ky doc lai cay UI khi cho. `uiautomator dump` da mat ~2.2s tren may that
# nen ban than no la cai ham nhip; ngu them nua chi keo dai luot cham.
POLL = 0.15


async def nodes(client, serial: str, metrics, cay: CayUI | None = None
                 ) -> list[DeviceNode]:
    if cay is not None and cay.con_dung_duoc():
        return cay.nodes
    nodes = parse_dump(await client.dump_ui(serial), metrics)
    if cay is not None:
        cay.giu(nodes)
    return nodes


async def wait_text(client, serial: str, metrics, needle: str,
                     timeout: float, cay: CayUI | None = None) -> bool:
    """Cho mot chuoi xuat hien tren man. Het gio -> False, nguoi goi tu xu."""
    folded = needle.casefold()
    # Dem bang DONG HO THAT, khong tru dan theo POLL: mot vong lap ton
    # (dump 2.2s + POLL) nhung chi tru POLL, nen `timeout: 25` tung chay
    # ~390 giay that - do dung mot luot cham 611s.
    het_gio = time.monotonic() + max(0.0, timeout)
    while True:
        if cay is not None:
            cay.bo()          # cho thi phai doc lai that, khong dung cay cu
        for node in await nodes(client, serial, metrics, cay):
            if folded in node.text.casefold() or folded in node.content_desc.casefold():
                return True
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
