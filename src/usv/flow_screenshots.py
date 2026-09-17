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
from .png_nho import RawError, tu_raw

log = logging.getLogger(__name__)

PNG_MAGIC = b"\x89PNG"


@dataclass(frozen=True, slots=True)
class Shot:
    moment: str          # "trước bước cuối" | "sau bước cuối" | "lúc lái hụt"
    png: bytes


# Tran byte anh THO cho ca luot. Base64 phinh ~33%, nen 6 MB anh -> ~8 MB
# trong report, con cach tran artifact 16 MB mot quang an toan. Vuot tran thi
# BO anh tiep theo chu khong bo case: mat anh con hon mat ket qua cham.
MAX_BYTES = 6_000_000


@dataclass(slots=True)
class Album:
    """Gom anh theo nhan case, giu dung thu tu chup."""

    adb: object
    serial: str
    shots: dict[str, list[Shot]] = field(default_factory=dict)
    da_dung: int = 0
    bo_bot: int = 0        # so tam bi bo vi het tran

    async def snap(self, case_label: str, moment: str) -> None:
        if self.da_dung >= MAX_BYTES:
            self.bo_bot += 1
            return
        png = await self._chup()
        if not png:
            return
        self.da_dung += len(png)
        self.shots.setdefault(case_label, []).append(
            Shot(moment=moment, png=png))

    async def _chup(self) -> bytes:
        try:
            # Man tat -> screencap ra anh DEN ma khong bao loi. Danh thuc truoc,
            # khong thi bang chung nhin nhu that ma rong khong.
            if not await self.adb.is_awake(self.serial):
                await self.adb.wake(self.serial)
            png = await self._nho()
        except AdbError as exc:
            log.warning("Chup man that bai: %s", exc)
            return b""
        return png if png.startswith(PNG_MAGIC) else b""

    async def _nho(self) -> bytes:
        """Raw + thu nho. May tra raw la thu khong hieu -> quay ve `screencap -p`
        (to hon nhieu, nhung co anh con hon khong)."""
        try:
            return tu_raw(await self.adb.screencap_raw(self.serial))
        except (RawError, AttributeError) as exc:
            log.warning("Raw khong dung duoc (%s) - quay ve screencap -p", exc)
            return await self.adb.screencap(self.serial)

    def recorder(self, case_label: str):
        """Callback cho `run_case`: no goi `await ghi(moment)`."""
        async def ghi(moment: str) -> None:
            await self.snap(case_label, moment)
        return ghi
