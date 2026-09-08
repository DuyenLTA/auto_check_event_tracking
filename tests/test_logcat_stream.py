"""Phien ghi logcat. Chay KHONG can may - AdbClient duoc thay bang ban gia.

Kiem hai thu khong the bo:
  - THU TU cac buoc trong start(): setprop -> logcat -c -> stream -> mo app.
    Sai thu tu la mat event dau tien hoac an ca log.
  - fa_silent: phan biet "app khong ban event" voi "FA khong in log" (R3).
"""

from __future__ import annotations

import asyncio

import pytest

from usv import logcat_stream
from usv.adb_parsers import AdbError
from usv.logcat_stream import Recording, drain, enable_fa, mark, start, stop


class FakeStdout:
    def __init__(self, lines: list[bytes]) -> None:
        self.queue = list(lines)

    async def readline(self) -> bytes:
        if not self.queue:
            raise asyncio.TimeoutError
        return self.queue.pop(0)


class FakeProcess:
    def __init__(self, lines: list[bytes]) -> None:
        self.stdout = FakeStdout(lines)
        self.returncode = None
        self.killed = False

    def kill(self) -> None:
        self.killed = True
        self.returncode = -9

    async def wait(self) -> int:
        return self.returncode or 0


class FakeClient:
    def __init__(self, lines: list[bytes] | None = None, prop: str = "VERBOSE") -> None:
        self.calls: list[str] = []
        self.props: dict[str, str] = {}
        self.logs: list[tuple[str, str]] = []
        self.lines = lines or []
        self.prop_value = prop
        self.process: FakeProcess | None = None

    async def setprop(self, serial, key, value):
        self.calls.append("setprop")
        self.props[key] = value

    async def getprop(self, serial, key):
        self.calls.append("getprop")
        return self.prop_value

    async def logcat_clear(self, serial):
        self.calls.append("clear")

    async def logcat_spawn(self, serial, tags):
        self.calls.append("spawn")
        self.tags = tags
        self.process = FakeProcess(self.lines)
        return self.process

    async def shell_log(self, serial, tag, message):
        self.calls.append("log")
        self.logs.append((tag, message))

    async def force_stop(self, serial, package):
        self.calls.append("force_stop")

    async def launch(self, serial, package):
        self.calls.append("launch")


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    async def instant(_seconds):
        return None
    monkeypatch.setattr(logcat_stream.asyncio, "sleep", instant)


def test_enable_fa_dat_ca_hai_property():
    client = FakeClient()
    assert asyncio.run(enable_fa(client, "S1")) is True
    assert client.props == {"log.tag.FA-SVC": "VERBOSE", "log.tag.FA": "VERBOSE"}


def test_enable_fa_bao_that_bai_khi_doc_lai_khong_dung():
    client = FakeClient(prop="")
    assert asyncio.run(enable_fa(client, "S1")) is False


def test_thu_tu_start_dung():
    """setprop TRUOC khi mo app (property doc luc process start);
    stream TRUOC khi mo app (de bat first_open/session_start)."""
    client = FakeClient()
    asyncio.run(start(client, "S1", "com.x"))
    order = [c for c in client.calls if c in
             {"setprop", "clear", "spawn", "force_stop", "launch"}]
    assert order.index("setprop") < order.index("spawn")
    assert order.index("clear") < order.index("spawn")
    assert order.index("spawn") < order.index("launch")
    assert order.index("force_stop") < order.index("launch")


def test_from_launch_tat_thi_khong_dong_app():
    client = FakeClient()
    asyncio.run(start(client, "S1", "com.x", from_launch=False))
    assert "force_stop" not in client.calls
    assert "launch" not in client.calls


def test_loc_dung_tag_va_co_ca_USV_MARK():
    """Thieu USV_MARK trong tag la mat moc -> khong cat duoc cua so."""
    client = FakeClient()
    asyncio.run(start(client, "S1", "com.x"))
    assert "USV_MARK" in client.tags
    assert "FA-SVC" in client.tags


def test_drain_doc_het_dong_dang_cho():
    client = FakeClient(lines=[b"dong 1\n", b"dong 2\n"])
    recording = asyncio.run(start(client, "S1", "com.x"))
    asyncio.run(drain(recording))
    assert recording.lines == ["dong 1", "dong 2"]


def test_mark_chen_dung_tag_va_ghi_lai_nhan():
    client = FakeClient()
    recording = asyncio.run(start(client, "S1", "com.x"))
    asyncio.run(mark(client, recording, "buoc 1"))
    assert client.logs == [("USV_MARK", "buoc 1")]
    assert recording.marks == ["buoc 1"]


def test_mark_sau_khi_dung_thi_bao_loi():
    client = FakeClient()
    recording = asyncio.run(start(client, "S1", "com.x"))
    asyncio.run(stop(recording))
    with pytest.raises(AdbError):
        asyncio.run(mark(client, recording, "buoc 2"))


def test_stop_kill_process_va_danh_dau_stopped():
    client = FakeClient(lines=[b"x\n"])
    recording = asyncio.run(start(client, "S1", "com.x"))
    process = client.process
    asyncio.run(stop(recording))
    assert process.killed is True
    assert recording.stopped is True
    assert recording.process is None


def test_fa_silent_khi_khong_co_dong_FA_nao():
    """R3: build strip log Firebase. KHONG duoc ket luan app thieu event."""
    recording = Recording(serial="S1", package="com.x",
                          lines=["09-08 15:00:00.000 D/CHRE ( 1): rac"])
    assert recording.fa_silent is True


def test_khong_fa_silent_khi_co_dong_FA():
    recording = Recording(
        serial="S1", package="com.x",
        lines=["09-08 15:40:15.733 I/FA (1): App measurement initialized"])
    assert recording.fa_silent is False


def test_payload_noi_ra_fa_silent():
    recording = Recording(serial="S1", package="com.x", lines=[])
    assert recording.payload()["fa_silent"] is True
