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


class Recorder:
    """Client gia cho `event_flow_run.run_step`. Nhan het, khong lam gi.

    Dung o hai file test flow nen de day thay vi khai lai o tung file.
    """

    def __init__(self, dump: str) -> None:
        self.dump, self.done = dump, []

    async def dump_ui(self, serial):
        return self.dump

    async def force_stop(self, serial, package):
        self.done.append("force_stop")

    async def launch(self, serial, package):
        self.done.append("launch")

    async def input_tap(self, serial, x, y):
        self.done.append(f"tap:{x:.0f},{y:.0f}")

    async def input_swipe(self, serial, x1, y1, x2, y2, duration_ms=300):
        self.done.append("swipe")

    async def input_keyevent(self, serial, name):
        self.done.append(f"key:{name}")

    async def input_text(self, serial, text):
        self.done.append(f"type:{text}")


@pytest.fixture
def recorder(spike_xml) -> Recorder:
    return Recorder(spike_xml)


@pytest.fixture
def flow_yaml() -> str:
    """Flow mau dung chung. Selector trong day khop voi spike-dump.xml."""
    return (FIXTURES / "flow-rating.yaml").read_text(encoding="utf-8")


@pytest.fixture
def no_sleep(monkeypatch):
    """Bo het cho doi - test flow khong duoc ngoi dem giay."""
    from usv import event_flow_run

    async def instant(_s):
        return None
    monkeypatch.setattr(event_flow_run.asyncio, "sleep", instant)
