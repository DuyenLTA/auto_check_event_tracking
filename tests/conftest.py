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
