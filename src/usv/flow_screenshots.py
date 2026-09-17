"""Chup man lam bang chung cho tung case.

Anh la bang chung NGU CANH, khong phai bang chung thoi diem: Firebase ban event
bat dong bo nen tam anh "sau buoc cuoi" co the som hon luc event that su ban
vai tram mili-giay. Report phai noi ro dieu do - xem report_event_shots.

Chup hong KHONG duoc lam sap luot cham. Mat mot tam anh con hon mat ca bao cao,
nhat la khi may vua rot khoi USB o case cuoi.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .adb_parsers import AdbError

log = logging.getLogger(__name__)

PNG_MAGIC = b"\x89PNG"


@dataclass(frozen=True, slots=True)
class Shot:
    moment: str          # "trước bước cuối" | "sau bước cuối" | "lúc lái hụt"
    png: bytes


@dataclass(slots=True)
class Album:
    """Gom anh theo nhan case, giu dung thu tu chup."""

    adb: object
    serial: str
    shots: dict[str, list[Shot]] = field(default_factory=dict)

    async def snap(self, case_label: str, moment: str) -> None:
        png = await self._chup()
        if not png:
            return
        self.shots.setdefault(case_label, []).append(
            Shot(moment=moment, png=png))

    async def _chup(self) -> bytes:
        try:
            # Man tat -> screencap ra anh DEN ma khong bao loi. Danh thuc truoc,
            # khong thi bang chung nhin nhu that ma rong khong.
            if not await self.adb.is_awake(self.serial):
                await self.adb.wake(self.serial)
            png = await self.adb.screencap(self.serial)
        except AdbError as exc:
            log.warning("Chup man that bai: %s", exc)
            return b""
        return png if png.startswith(PNG_MAGIC) else b""

    def recorder(self, case_label: str):
        """Callback cho `run_case`: no goi `await ghi(moment)`."""
        async def ghi(moment: str) -> None:
            await self.snap(case_label, moment)
        return ghi
