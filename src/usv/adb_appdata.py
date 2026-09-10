"""Doc/ghi file trong thu muc rieng cua app qua `run-as`.

DIEU KIEN SONG CHET: app phai la build DEBUGGABLE. May khong root thi `adb shell`
khong vao duoc /data/data/<pkg> cua app khac, va `run-as` tu choi:

    run-as: package not debuggable: <pkg>

Do that tren may 99261FFAZ0077C (Pixel 4, khong root): 17/85 app cai them la
debuggable. Cac ban release tu Play Store thi KHONG. Nen tool phai kiem truoc va
bao BLOCKED - khong duoc de flow chay tiep roi ra ket qua vo nghia.

Ghi file: `run-as <pkg> sh -c 'cat > duong/dan'` roi day noi dung qua stdin.
Khong dung `echo` trong dong lenh: noi dung JSON/XML co dau nhay va ky tu dac
biet, nhet vao dong lenh la vo.
"""

from __future__ import annotations

import asyncio
import re

from .adb_parsers import AdbError, check_package, check_serial

# Duong dan TUONG DOI trong thu muc app. Chan '..' va duong dan tuyet doi -
# moi thu nay di vao mot dong lenh shell tren may.
_REL_PATH = re.compile(r"[A-Za-z0-9_.:@\-]+(?:/[A-Za-z0-9_.:@\-]+)*")
_NOT_DEBUGGABLE = "not debuggable"


class AppDataMixin:
    """Doi hoi `self._run` cua AdbClient."""

    @staticmethod
    def _check_path(path: str) -> str:
        if ".." in path or path.startswith("/") or not _REL_PATH.fullmatch(path):
            raise AdbError(
                f"Đường dẫn trong app không hợp lệ: {path!r}. Phải là đường dẫn "
                "tương đối, vd 'files/frc_x.json' hoặc 'shared_prefs/y.xml'.")
        return path

    async def is_debuggable(self, serial: str, package: str) -> bool:
        """True khi `run-as` vao duoc. Kiem TRUOC khi lam gi khac."""
        check_serial(serial)
        check_package(package)
        out, err, code = await self._run(
            "-s", serial, "shell", "run-as", package, "true")
        return code == 0 and _NOT_DEBUGGABLE not in (out + err)

    async def app_read(self, serial: str, package: str, path: str) -> str:
        """Noi dung file. Khong co file -> chuoi rong, KHONG raise.

        Khong co file la trang thai binh thuong: app chua fetch RC lan nao thi
        chua co frc_*.json.
        """
        check_serial(serial)
        check_package(package)
        self._check_path(path)
        out, err, code = await self._run(
            "-s", serial, "shell", "run-as", package, "cat", path)
        if code != 0:
            if _NOT_DEBUGGABLE in err:
                raise AdbError(_blocked_message(package))
            return ""
        return out

    async def app_list(self, serial: str, package: str, folder: str) -> list[str]:
        check_serial(serial)
        check_package(package)
        self._check_path(folder)
        out, err, code = await self._run(
            "-s", serial, "shell", "run-as", package, "ls", folder)
        if code != 0:
            if _NOT_DEBUGGABLE in err:
                raise AdbError(_blocked_message(package))
            return []
        return [line.strip() for line in out.splitlines() if line.strip()]

    async def app_write(self, serial: str, package: str, path: str,
                        content: str) -> None:
        """Ghi de file. Noi dung di qua STDIN, khong qua dong lenh."""
        check_serial(serial)
        check_package(package)
        self._check_path(path)
        args = ("-s", serial, "shell", "run-as", package, "sh", "-c",
                f"cat > {path}")
        try:
            proc = await asyncio.create_subprocess_exec(
                self.adb, *args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError as exc:
            raise AdbError(f"Không chạy được adb: {exc}") from exc
        _, err = await proc.communicate(content.encode("utf-8"))
        stderr = err.decode("utf-8", "replace")
        if _NOT_DEBUGGABLE in stderr:
            raise AdbError(_blocked_message(package))
        if proc.returncode:
            raise AdbError(f"Ghi {path} thất bại: {stderr.strip() or 'không rõ'}")

    async def device_time_ms(self, serial: str) -> int:
        """Gio cua MAY theo mili-giay.

        Phai lay gio MAY chu khong phai gio host: SDK Remote Config so moc
        throttle voi System.currentTimeMillis() tren may. Host lech gio la
        throttle khong an, patch bi ghi de ma khong ro tai sao.

        Nam o mixin nay vi chi viec sua Remote Config can den no.
        """
        check_serial(serial)
        out, _, code = await self._run("-s", serial, "shell", "date", "+%s%3N")
        digits = out.strip()
        if code != 0 or not digits.isdigit():
            raise AdbError(f"Không đọc được giờ trên máy: {out.strip()!r}")
        return int(digits)

    async def app_remove(self, serial: str, package: str, path: str) -> None:
        """Xoa file. Khong co file cung coi la xong - `rm -f`."""
        check_serial(serial)
        check_package(package)
        self._check_path(path)
        _, err, code = await self._run(
            "-s", serial, "shell", "run-as", package, "rm", "-f", path)
        if code != 0 and _NOT_DEBUGGABLE in err:
            raise AdbError(_blocked_message(package))


def _blocked_message(package: str) -> str:
    return (
        f"App {package} khong phai build debuggable nen khong vao duoc thu muc "
        "rieng cua no (may cung khong root). Khong reset duoc trang thai giua "
        "cac case.\n"
        "  - Dung build debug/internal de test, hoac\n"
        "  - Bo buoc `reset` trong flow va tu dua app ve trang thai can test."
    )
