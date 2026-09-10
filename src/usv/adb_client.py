"""Client adb bat dong bo: liet ke device/package, doc kich thuoc man hinh,
dump cay UI, chup screenshot.

KHONG dung shell=True o bat ky dau - moi arg di rieng vao asyncio subprocess.
Ten package/serial deu qua check_package/check_serial truoc khi vao dong lenh
(xem docstring adb_parsers).
"""

from __future__ import annotations

import asyncio
import logging

from .adb_appdata import AppDataMixin
from .adb_input import InputMixin
from .adb_logcat import LogcatMixin
from .adb_parsers import (
    AdbError, AdbTransportError, Device, check_package, check_serial, find_adb,
    parse_current_focus, parse_devices, parse_packages, parse_wm_density, parse_wm_size,
)

log = logging.getLogger(__name__)

CMD_TIMEOUT = 8.0
# uiautomator dump tren may cham co the mat vai giay - cho lau hon lenh thuong.
DUMP_TIMEOUT = 30.0
# Screenshot 1080x2280 PNG ~ 1MB; de rong cho may cham.
SCREENCAP_TIMEOUT = 40.0

# Dau hieu adb mat ket noi -> AdbTransportError chu khong phai loi nghiep vu.
_TRANSPORT_HINTS = (
    "device not found", "device offline", "no devices", "device unauthorized",
    "protocol fault", "connection reset", "daemon not running",
)


class AdbClient(LogcatMixin, InputMixin, AppDataMixin):
    def __init__(self, adb_path: str | None = None) -> None:
        self.adb = find_adb(adb_path)

    async def _run(
        self, *args: str, timeout: float | None = None
    ) -> tuple[str, str, int]:
        """Tra (stdout, stderr, returncode). KHONG raise khi returncode != 0 -
        nguoi goi tu quyet dinh, vi nhieu lenh 'that bai' la binh thuong.

        Doc CMD_TIMEOUT luc GOI chu khong lam default cua tham so, de test doi
        duoc ma khong phai cho that.
        """
        timeout = CMD_TIMEOUT if timeout is None else timeout
        try:
            proc = await asyncio.create_subprocess_exec(
                self.adb, *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError as exc:
            raise AdbError(f"Khong chay duoc adb ({self.adb}): {exc}") from exc

        try:
            out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError as exc:
            proc.kill()
            await proc.wait()
            raise AdbError(f"adb {' '.join(args)} qua {timeout:g}s khong tra ve.") from exc

        stderr = err.decode("utf-8", "replace")
        self._raise_if_transport(stderr)
        return out.decode("utf-8", "replace"), stderr, proc.returncode or 0

    async def _run_binary(self, *args: str, timeout: float) -> bytes:
        """Nhu _run nhung giu stdout dang bytes - dung cho screencap PNG."""
        try:
            proc = await asyncio.create_subprocess_exec(
                self.adb, *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError as exc:
            raise AdbError(f"Khong chay duoc adb ({self.adb}): {exc}") from exc

        try:
            out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError as exc:
            proc.kill()
            await proc.wait()
            raise AdbError(f"adb {' '.join(args)} qua {timeout:g}s khong tra ve.") from exc

        self._raise_if_transport(err.decode("utf-8", "replace"))
        return out

    @staticmethod
    def _raise_if_transport(stderr: str) -> None:
        low = stderr.lower()
        for hint in _TRANSPORT_HINTS:
            if hint in low:
                raise AdbTransportError(
                    f"Mat ket noi voi device: {stderr.strip()}\n"
                    "Kiem tra cap USB, bat lai USB debugging, hoac bam Allow tren may."
                )

    # --- API nghiep vu --------------------------------------------------------

    async def devices(self) -> list[Device]:
        out, _, _ = await self._run("devices", "-l")
        return parse_devices(out)

    async def packages(self, serial: str) -> list[str]:
        """Chi liet ke app cai them (-3), khong lay app he thong."""
        check_serial(serial)
        out, _, _ = await self._run("-s", serial, "shell", "pm", "list", "packages", "-3")
        return parse_packages(out)

    async def screen_metrics(self, serial: str) -> tuple[tuple[int, int], int]:
        """Tra ((rong_px, cao_px), density). Raise neu khong doc duoc - moi phep
        doi px<->dp phia sau deu dua vao 2 so nay, doan bua la sai het report."""
        check_serial(serial)
        size_out, _, _ = await self._run("-s", serial, "shell", "wm", "size")
        density_out, _, _ = await self._run("-s", serial, "shell", "wm", "density")
        size = parse_wm_size(size_out)
        density = parse_wm_density(density_out)
        if size is None or density is None:
            raise AdbError(
                "Khong doc duoc kich thuoc/density man hinh.\n"
                f"  wm size    -> {size_out.strip()!r}\n"
                f"  wm density -> {density_out.strip()!r}"
            )
        return size, density

    async def current_focus(self, serial: str) -> str | None:
        """Package (hoac ten window) dang giu focus. None neu khong doc duoc."""
        check_serial(serial)
        out, _, _ = await self._run("-s", serial, "shell", "dumpsys", "window")
        return parse_current_focus(out)

    async def is_awake(self, serial: str) -> bool:
        """False khi man hinh dang tat/doze - luc do screencap ra anh den."""
        check_serial(serial)
        out, _, _ = await self._run("-s", serial, "shell", "dumpsys", "power")
        for line in out.splitlines():
            if "mWakefulness=" in line:
                return "Awake" in line
        return True  # khong doc duoc thi cho di, dung chan tester

    async def wake(self, serial: str) -> None:
        check_serial(serial)
        await self._run("-s", serial, "shell", "input", "keyevent", "KEYCODE_WAKEUP")

    async def dump_ui(self, serial: str) -> str:
        """`uiautomator dump` roi doc file ve. Tra noi dung XML.

        Doc bang `cat` thay vi `adb pull` de khong phai tao file tam tren host.
        """
        check_serial(serial)
        remote = "/sdcard/usv-dump.xml"
        out, err, _ = await self._run(
            "-s", serial, "shell", "uiautomator", "dump", remote, timeout=DUMP_TIMEOUT
        )
        if "dumped to" not in out.lower() and "dumped to" not in err.lower():
            raise AdbError(
                "uiautomator dump khong thanh cong.\n"
                f"  stdout: {out.strip()!r}\n  stderr: {err.strip()!r}\n"
                "Thuong do man hinh dang tat, hoac dang o man hinh khong cho dump."
            )
        xml, _, _ = await self._run("-s", serial, "shell", "cat", remote, timeout=DUMP_TIMEOUT)
        if "<hierarchy" not in xml:
            raise AdbError("Doc duoc file dump nhung khong phai XML hierarchy.")
        return xml

    async def screencap(self, serial: str) -> bytes:
        """PNG bytes. `exec-out` de khong bi CRLF lam hong binary."""
        check_serial(serial)
        png = await self._run_binary(
            "-s", serial, "exec-out", "screencap", "-p", timeout=SCREENCAP_TIMEOUT
        )
        if not png.startswith(b"\x89PNG"):
            raise AdbError("screencap khong tra ve PNG hop le.")
        return png

    async def launch(self, serial: str, package: str) -> None:
        """Mo app. Chi dung khi tester bam nut - tool KHONG tu dieu huong flow.

        PHAI doc stdout: `monkey` in "No activities found to run" nhung tra
        EXIT CODE 0, nen chi xem returncode thi mo app that bai trong im lang -
        roi phien ghi bat log cua app dang mo san va bao cao gan event cua no
        cho app dang test.
        """
        check_serial(serial)
        check_package(package)
        out, err, _ = await self._run(
            "-s", serial, "shell", "monkey", "-p", package,
            "-c", "android.intent.category.LAUNCHER", "1",
        )
        if "No activities found to run" in (out + err):
            raise AdbError(
                f"Khong mo duoc {package}: may bao khong co man nao de mo. "
                "App chua cai, hoac khong co launcher activity.")
