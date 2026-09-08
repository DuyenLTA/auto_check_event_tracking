"""Doi don vi px <-> dp. So doi chieu lay tu may that da do luc spike."""

from __future__ import annotations

from usv.density import ScreenMetrics
from usv.models import Bounds


def test_scale_may_that(metrics):
    assert metrics.scale == 2.75
    assert metrics.width_dp == 392.7
    assert metrics.height_dp == 829.1


def test_to_dp_va_nguoc_lai(metrics):
    assert metrics.to_dp(1080) == 392.7
    assert metrics.to_px(100) == 275.0


def test_bounds_sang_dp_khop_so_do_tay(metrics):
    # borderContainer trong dump that: [57,315][504,762] -> 162.5 x 162.5 dp
    dp = metrics.bounds_to_dp(Bounds(57, 315, 504, 762))
    # size lay tu so chinh xac roi moi lam tron - KHONG tu canh da lam tron
    assert dp.size_tuple() == (162.5, 162.5)
    assert dp.as_tuple()[:2] == (20.7, 114.5)


def test_size_khong_phu_thuoc_vi_tri(metrics):
    """Cung mot kich thuoc px phai ra cung mot size dp du nam o dau.

    Bug that da gap: lam tron tung canh roi tru ra width -> element 447px cho
    162.5 hoac 162.6 tuy toa do. Tolerance +-2dp se chay khong nhat quan.
    """
    sizes = {
        metrics.bounds_to_dp(Bounds(x, 0, x + 447, 447)).size_tuple()
        for x in range(0, 600, 7)
    }
    assert len(sizes) == 1, f"size doi theo vi tri: {sorted(sizes)}"


def test_mdpi_scale_bang_1():
    m = ScreenMetrics(width_px=360, height_px=640, density=160)
    assert m.scale == 1.0
    assert m.width_dp == 360.0
