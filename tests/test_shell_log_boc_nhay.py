"""Nhan moc phai toi logcat NGUYEN VAN.

Do tren may that (Pixel 7): `adb shell` ghep cac tham so lai roi dua cho
/system/bin/sh, nen nhan `widget_view | popup Add Widget` bi sh doc dau `|`
thanh ONG - logcat chi nhan duoc `widget_view`. Hau qua day chuyen: note bay
mat -> cua so cua case lai hut khong con khop de bo -> event bi cham tren mot
man chua bao gio lai toi -> **FAIL oan**. Da xay ra that o lan chay E2E dau.
"""

from __future__ import annotations

import asyncio

import pytest

from usv.adb_logcat import LogcatMixin, _boc_nhay
from usv.event_window import mark_label, split_label


class FakeAdb(LogcatMixin):
    adb = "/fake/adb"

    def __init__(self) -> None:
        self.args: tuple = ()

    async def _run(self, *args, **kw):
        self.args = args
        return ("", "", 0)


def run(coro):
    return asyncio.run(coro)


@pytest.mark.parametrize("nhan", [
    "widget_view | popup Add Widget sau paywall",
    "rating_placement_viewed | tại home",
    "e | ghi chú có 'nháy đơn'",
    "e | ; rm -rf /sdcard",
    "e | $(reboot)",
])
def test_nhan_di_nguyen_van_qua_shell(nhan):
    adb = FakeAdb()
    run(adb.shell_log("S1", "USV_MARK", nhan))
    gui = adb.args[-1]
    assert gui == _boc_nhay(nhan)
    # Boc xong phai boc lai ra dung chuoi cu: mo/dong nhay don theo POSIX.
    assert _go_nhay(gui) == nhan


def _go_nhay(boc: str) -> str:
    """Giai ma kieu boc nhay don cua POSIX sh."""
    assert boc.startswith("'") and boc.endswith("'")
    return boc[1:-1].replace("'\\''", "'")


def test_nhan_co_dau_ong_van_tach_lai_dung_event_va_note():
    nhan = mark_label("widget_view", "popup Add Widget sau paywall")
    assert split_label(nhan) == ("widget_view", "popup Add Widget sau paywall")
    assert _go_nhay(_boc_nhay(nhan)) == nhan
