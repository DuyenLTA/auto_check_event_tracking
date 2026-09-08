"""Phan logcat cua AdbClient: property, stream, marker, force-stop.

Tach khoi adb_client.py de moi file duoi 200 LOC. La MIXIN chu khong phai ham
roi: nhung viec nay dung chung `self._run` va `self.adb` cua AdbClient, truyen
client qua tham so chi lam ro rang hon ma khong loi gi.
"""

from __future__ import annotations

import asyncio
import re

from .adb_parsers import AdbError, check_package, check_serial

# Chan chuoi la di vao dong lenh adb. Cung ly do voi check_serial/check_package
# trong adb_parsers: moi arg di rieng vao subprocess nhung ten van phai sach.
_PROP_KEY = re.compile(r"[A-Za-z0-9_.\-]{1,64}")
_PROP_VALUE = re.compile(r"[A-Za-z0-9_.\-]{0,64}")
_LOG_TAG = re.compile(r"[A-Za-z0-9_\-]{1,32}")

# Tag chua event Firebase. Do that tren AIP922: 67/67 dong `Logging event` nam o
# FA-SVC; tag FA chi in `Logging telemetry` khong kem params.
FA_TAG = "FA-SVC"
MARK_TAG = "USV_MARK"


class LogcatMixin:
    """Doi hoi `self._run` va `self.adb` cua AdbClient."""

    async def setprop(self, serial: str, key: str, value: str) -> None:
        """Dat system property. Dung cho `log.tag.FA-SVC VERBOSE`.

        KHONG song qua reboot, va app phai KHOI DONG LAI sau khi dat vi property
        duoc doc luc process start. Nen luon goi lai truoc moi lan Ghi.
        """
        check_serial(serial)
        if not _PROP_KEY.fullmatch(key) or not _PROP_VALUE.fullmatch(value):
            raise AdbError(f"Ten/gia tri property khong hop le: {key}={value}")
        await self._run("-s", serial, "shell", "setprop", key, value)

    async def getprop(self, serial: str, key: str) -> str:
        check_serial(serial)
        if not _PROP_KEY.fullmatch(key):
            raise AdbError(f"Ten property khong hop le: {key}")
        out, _, _ = await self._run("-s", serial, "shell", "getprop", key)
        return out.strip()

    async def logcat_clear(self, serial: str) -> None:
        check_serial(serial)
        await self._run("-s", serial, "logcat", "-c")

    async def logcat_spawn(self, serial: str, tags: tuple[str, ...]):
        """Mo stream logcat da LOC THEO TAG, tra ve process cho caller doc dan.

        Loc o tang tag chu khong grep tren host: `adb logcat -s` loc ngay tren
        dien thoai nen tiet kiem ca duong truyen. Do that: 12 964 dong ca buffer
        -> 1 259 dong khi chi lay FA-SVC.

        KHONG loc `origin=app` o day du no ngan nhat (42 dong): mat dong
        USV_MARK nen khong cat duoc cua so, mat kha nang phan biet "FA khong in
        log" voi "app khong ban event", va mat ga_screen_class.
        """
        check_serial(serial)
        for tag in tags:
            if not _LOG_TAG.fullmatch(tag):
                raise AdbError(f"Tag logcat khong hop le: {tag!r}")
        args = ["-s", serial, "logcat", "-v", "time", "-s", *tags]
        try:
            return await asyncio.create_subprocess_exec(
                self.adb, *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError as exc:
            raise AdbError(f"Khong mo duoc stream logcat: {exc}") from exc

    async def shell_log(self, serial: str, tag: str, message: str) -> None:
        """Chen mot dong vao logcat -> moc cat cua so.

        Dong nay nam CHUNG timeline voi event nen khong phai dong bo gio giua
        host va device. Da verify tren may that.
        """
        check_serial(serial)
        if not _LOG_TAG.fullmatch(tag):
            raise AdbError(f"Tag logcat khong hop le: {tag!r}")
        await self._run("-s", serial, "shell", "log", "-p", "i", "-t", tag, message)

    async def force_stop(self, serial: str, package: str) -> None:
        """Dung app. Can truoc khi mo lai de property log.tag co hieu luc."""
        check_serial(serial)
        check_package(package)
        await self._run("-s", serial, "shell", "am", "force-stop", package)
