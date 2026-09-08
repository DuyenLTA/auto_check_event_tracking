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
