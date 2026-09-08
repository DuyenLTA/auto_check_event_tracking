"""Bam / quet / go chu tren may qua `adb shell input`.

Toa do luon la PIXEL VAT LY - dung y nguyen `bounds_px` cua DeviceNode, khong
doi sang dp. `uiautomator dump` va `input tap` cung mot he toa do.

Moi arg di rieng vao subprocess, va so duoc ep sang int truoc khi vao dong lenh.
"""

from __future__ import annotations

from .adb_parsers import AdbError, check_serial

# Ten keyevent cho phep. Danh sach trang thay vi chuoi tuy y: ten keyevent di
# thang vao dong lenh, va vai keyevent (POWER, SLEEP) lam hong ca phien test.
KEYEVENTS = {
    "BACK": "KEYCODE_BACK",
    "HOME": "KEYCODE_HOME",
    "ENTER": "KEYCODE_ENTER",
    "TAB": "KEYCODE_TAB",
    "DEL": "KEYCODE_DEL",
    "ESCAPE": "KEYCODE_ESCAPE",
    "APP_SWITCH": "KEYCODE_APP_SWITCH",
}

MAX_COORD = 20000       # chan so vo ly do loi tinh toan
SWIPE_MS = 300


class InputMixin:
    """Doi hoi `self._run` cua AdbClient."""

    @staticmethod
    def _coord(value: float, name: str) -> int:
        number = int(round(value))
        if not 0 <= number <= MAX_COORD:
            raise AdbError(f"{name}={value!r} ngoai khoang cho phep.")
        return number

    async def input_tap(self, serial: str, x: float, y: float) -> None:
        check_serial(serial)
        await self._run(
            "-s", serial, "shell", "input", "tap",
            str(self._coord(x, "x")), str(self._coord(y, "y")),
        )

    async def input_swipe(self, serial: str, x1: float, y1: float,
                          x2: float, y2: float, duration_ms: int = SWIPE_MS) -> None:
        check_serial(serial)
        millis = max(50, min(int(duration_ms), 5000))
        await self._run(
            "-s", serial, "shell", "input", "swipe",
            str(self._coord(x1, "x1")), str(self._coord(y1, "y1")),
            str(self._coord(x2, "x2")), str(self._coord(y2, "y2")), str(millis),
        )

    async def input_keyevent(self, serial: str, name: str) -> None:
        check_serial(serial)
        key = KEYEVENTS.get(name.strip().upper())
        if key is None:
            raise AdbError(
                f"keyevent {name!r} khong duoc phep. Chi nhan: "
                + ", ".join(sorted(KEYEVENTS)))
        await self._run("-s", serial, "shell", "input", "keyevent", key)

    async def input_text(self, serial: str, text: str) -> None:
        """Go chu. `input text` khong nhan khoang trang nen doi thanh %s."""
        check_serial(serial)
        if "'" in text or '"' in text:
            raise AdbError("Chuoi go vao khong duoc chua dau nhay.")
        await self._run(
            "-s", serial, "shell", "input", "text", text.replace(" ", "%s"))
