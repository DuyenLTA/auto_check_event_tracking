"""Fixture dung chung."""

from __future__ import annotations

from pathlib import Path

import pytest

from usv.density import ScreenMetrics

FIXTURES = Path(__file__).parent / "fixtures"

# Thong so may that dung khi spike: 1080x2280 @440dpi -> scale 2.75 -> 392.7dp.
# Moi assert ve dp trong suite deu dua vao bo so nay.
REAL_METRICS = ScreenMetrics(width_px=1080, height_px=2280, density=440)


@pytest.fixture
def metrics() -> ScreenMetrics:
    return REAL_METRICS


@pytest.fixture
def spike_xml() -> str:
    """Dump UI that luc spike. Dung de phan giai selector (bam theo resource-id)."""
    return (FIXTURES / "spike-dump.xml").read_text(encoding="utf-8")


@pytest.fixture
def client():
    """TestClient gia lap request tu loopback.

    Mac dinh TestClient dung Host 'testserver' va client host 'testclient' -> bi
    middleware loopback_only tra 403. Ep ve 127.0.0.1 de test CHAY QUA middleware
    that thay vi vo hieu hoa no (xem test_middleware_chan_non_loopback).
    """
    from fastapi.testclient import TestClient

    from usv import main
    from usv.event_state import state

    state.reset()
    with TestClient(main.app, base_url="http://127.0.0.1",
                    client=("127.0.0.1", 50000)) as test_client:
        yield test_client
    state.reset()


# --- adb gia, dung chung cho moi test khong can may that ---
#
# Nam o conftest chu khong o mot file test: hai duong (web va CLI) cung can, va
# de o file test nay thi file test kia phai import cheo - mot rang buoc im lang
# vo ra dung hom file kia bi xoa.

import asyncio  # noqa: E402
import re  # noqa: E402

RAW_LOG = (FIXTURES / "fa-events-aip922.log").read_text(encoding="utf-8")

_LINE = re.compile(r"Logging event: origin=app,name=([^,(]+)[^,]*,params=Bundle\[\{(.*)\}\]")
# Ten event -> phan params, lay tu log THAT.
PARAMS = {m.group(1): m.group(2) for m in
          (_LINE.search(line) for line in RAW_LOG.splitlines()) if m}


class FakeStdout:
    """Doi khi rong thi CHO chu khong tra EOF - stream that cung vay.

    Tra EOF ngay khi rong thi task doc ket thuc som, roi moc chen sau do khong
    ai doc nua.
    """

    def __init__(self) -> None:
        self.queue: list[bytes] = []
        self.closed = False

    async def readline(self) -> bytes:
        while not self.queue and not self.closed:
            await asyncio.sleep(0.001)
        return self.queue.pop(0) if self.queue else b""


class FakeProcess:
    def __init__(self) -> None:
        self.stdout = FakeStdout()
        self.returncode = None

    def kill(self) -> None:
        self.stdout.closed = True
        self.returncode = -9

    async def wait(self) -> int:
        return -9


class FakeAdb:
    """AdbClient gia. shell_log chen moc RO! roi bom luon event cua buoc do -
    dung thu tu that: bam moc -> thao tac -> app ban event."""

    adb = "/fake/adb"

    def __init__(self) -> None:
        self.process = FakeProcess()
        self.step = 0
        self.marks: list[str] = []
        # Thu tu goi co y nghia: logcat -c -> spawn -> force_stop -> launch.
        # Sai thu tu la mat cac event dau tien (first_open, session_start).
        self.calls: list[str] = []

    async def setprop(self, serial, key, value): return None
    async def getprop(self, serial, key): return "VERBOSE"
    async def logcat_clear(self, serial):
        self.calls.append("clear")
        return None
    async def force_stop(self, serial, package):
        self.calls.append("force_stop")
        return None

    foreground: str | None = None

    async def foreground_package(self, serial):
        return self.foreground

    async def home_package(self, serial):
        return "com.launcher"

    running: set | None = None

    async def app_running(self, serial, package):
        # Mac dinh: app "dang chay" khi co trong danh sach cai dat - du de phan
        # biet app that voi app go sai ten. Test doi `running` de dung ca app
        # co cai ma khong chay.
        if self.running is not None:
            return package in self.running
        return package in await self.packages(serial)
    async def launch(self, serial, package):
        self.calls.append("launch")
        return None

    async def logcat_spawn(self, serial, tags):
        self.calls.append("spawn")
        # Ong MOI moi lan spawn, y nhu `adb logcat` that. Tra lai ong cu thi
        # phien ghi thu hai thua luon trang thai dong cua phien truoc.
        self.process = FakeProcess()
        return self.process

    async def shell_log(self, serial, tag, message):
        self.marks.append(message)
        self.step += 1
        stamp = f"09-08 15:00:{self.step:02d}"
        self.process.stdout.queue.append(
            f"{stamp}.000 I/USV_MARK( 9): {message}\n".encode())
        name = message.split(" | ")[0]
        if name in PARAMS:
            self.process.stdout.queue.append(
                (f"{stamp}.500 V/FA-SVC ( 9): Logging event: origin=app,"
                 f"name={name},params=Bundle[{{{PARAMS[name]}}}]\n").encode())

    async def devices(self):
        from usv.adb_parsers import Device
        return [Device(serial="FAKE1", state="device", model="Pixel")]

    async def packages(self, serial):
        return ["com.example.app", "com.other.app"]

