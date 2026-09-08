"""Verdict cho domain event tracking.

Khoa mot regression THAT, khong phai phong xa: `Summary.add` ket thuc bang
`else: self.failed += 1`, `exporter._tone` va `render.js` cung roi xuong nhanh
fail mac dinh. Nen them NOT_TESTED ma khong sua 4 cho do thi no bi dem thanh
FAIL - vi pham nguyen tac 1 cua repo (khong ghep duoc / chua test KHONG phai loi
cua app).
"""

from __future__ import annotations

import pytest

from usv import exporter
from usv.check_models import (
    FAIL_VERDICTS, CheckResult, Summary, Verdict, icon, verdict_label,
)

NEW_FAILS = ["FAIL_VALUE", "FAIL_TYPE", "FAIL_DUPLICATE", "FAIL_PARAM_EXTRA"]
# Gia tri enum di vao file xlsx xuat ra va vao report da luu - doi la cac ban cu
# doc khong khop nua. Xem check_models.py phan VERDICT_LABEL.
ALL_VERDICTS = [
    "PASS", "FAIL_MISSING", "FAIL_VALUE", "FAIL_TYPE", "FAIL_DUPLICATE",
    "FAIL_PARAM_EXTRA", "NOT_VERIFIABLE", "NOT_TESTED", "EXTRA",
]


def _result(verdict: Verdict) -> CheckResult:
    return CheckResult(element="rating_placement_viewed", check="event_presence",
                       verdict=verdict, message="x")


def test_verdict_moi_ton_tai():
    for name in NEW_FAILS + ["NOT_TESTED"]:
        assert hasattr(Verdict, name), f"thieu Verdict.{name}"


def test_gia_tri_verdict_khong_doi():
    """Doi gia tri enum -> xlsx va report da luu doc khong khop nua."""
    for name in ALL_VERDICTS:
        assert str(getattr(Verdict, name)) == name


def test_khong_con_verdict_cua_tool_UI():
    """Tool nay khong so UI voi design nua - de lai la tu vung chet gay nham."""
    for name in ("FAIL_POSITION", "FAIL_SIZE", "FAIL_GAP", "FAIL_PADDING",
                 "FAIL_TEXT", "FAIL_COLOR", "FAIL_ORDER", "UNMATCHED"):
        assert not hasattr(Verdict, name), f"Verdict.{name} con sot lai"


def test_not_tested_khong_tinh_vao_fail():
    """Chua test KHONG phai loi cua app - nguyen tac 1."""
    summary = Summary()
    summary.add(_result(Verdict.NOT_TESTED))
    assert summary.failed == 0, "NOT_TESTED bi dem thanh FAIL"
    assert summary.not_tested == 1
    assert summary.passed == 0
    assert summary.not_verifiable == 0


def test_fail_moi_co_tinh_vao_fail():
    for name in NEW_FAILS:
        summary = Summary()
        summary.add(_result(getattr(Verdict, name)))
        assert summary.failed == 1, f"{name} phai tinh vao failed"


def test_fail_verdicts_chua_4_fail_moi_va_khong_chua_not_tested():
    for name in NEW_FAILS:
        assert getattr(Verdict, name) in FAIL_VERDICTS, f"{name} thieu trong FAIL_VERDICTS"
    assert Verdict.NOT_TESTED not in FAIL_VERDICTS


def test_checkresult_failed_dung_cho_verdict_moi():
    assert _result(Verdict.FAIL_VALUE).failed is True
    assert _result(Verdict.NOT_TESTED).failed is False


def test_tone_xlsx_not_tested_khac_fail():
    """O xlsx cua NOT_TESTED khong duoc to do nhu loi that."""
    assert exporter._tone(Verdict.NOT_TESTED) != exporter._tone(Verdict.FAIL_VALUE)


def test_tone_xlsx_fail_moi_la_fail():
    for name in NEW_FAILS:
        assert exporter._tone(getattr(Verdict, name)) == exporter._tone(Verdict.FAIL_VALUE)


def test_nhan_tieng_viet_cho_ca_5_verdict_moi():
    """Thieu nhan -> in ra ten enum tho, tester doc khong hieu."""
    for name in NEW_FAILS + ["NOT_TESTED"]:
        verdict = getattr(Verdict, name)
        assert verdict_label(verdict) != name, f"{name} chua co nhan tieng Viet"


def test_icon_not_tested_khong_phai_do():
    """icon() mac dinh tra 🔴 - NOT_TESTED khong duoc do."""
    assert icon(Verdict.NOT_TESTED) != "🔴"


@pytest.mark.parametrize("name", NEW_FAILS)
def test_icon_fail_moi_la_do(name):
    assert icon(getattr(Verdict, name)) == "🔴"


def test_headline_noi_ra_so_chua_test():
    summary = Summary()
    summary.add(_result(Verdict.NOT_TESTED))
    assert "chua test" in summary.headline().lower() \
        or "chưa test" in summary.headline().lower()
