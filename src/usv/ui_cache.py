"""Cay UI doc gan day, dung lai duoc khi khong co thao tac nao xen vao.

Do tren may that (Pixel 7): mot `uiautomator dump` mat **2.2s**, va mot case goi
6-8 lan - phan lon thoi gian lai may nam o day, khong phai o cho bam. Hai buoc
lien tiep cung nhin mot man khong doi (vd cho chu hien ra roi bam vao no, hay
hai buoc tuy chon deu khong tim thay) thi doc lai la tra tien hai lan cho cung
mot thu.

An toan dua tren mot luat duy nhat: **bat ky thao tac nao cung xoa cache ngay**.
Cay chi song qua nhung lan CHI DOC.
"""

from __future__ import annotations

import time

from .models import DeviceNode

CAY_TTL = 3.0


class CayUI:
    """Cay UI doc gan day. Khong phai toi uu vi vui: bo cai nay thi moi buoc
    tim-khong-thay lai tra them 2.2s cho cung mot man hinh khong doi."""

    __slots__ = ("nodes", "moc")

    def __init__(self) -> None:
        self.nodes: list[DeviceNode] | None = None
        self.moc = 0.0

    def con_dung_duoc(self) -> bool:
        return self.nodes is not None and (time.monotonic() - self.moc) < CAY_TTL

    def giu(self, nodes: list[DeviceNode]) -> None:
        self.nodes, self.moc = nodes, time.monotonic()

    def bo(self) -> None:
        """Goi NGAY SAU moi thao tac: man da doi, cay cu la cay cua qua khu."""
        self.nodes = None
