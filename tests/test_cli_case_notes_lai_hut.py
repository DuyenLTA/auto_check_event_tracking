"""Case lai hut phai HIEN RA. Kiem nhung thu SAI THI KHONG AI THAY:
  - event co case PASS lan case hut -> case hut bien mat, bao cao doc nhu da do het
  - them dong nhung quen dem lai -> bang co dong ma con so `not_tested` van 0
  - ke hai lan khi ca event khong do duoc -> phong dai so case hong
"""

from __future__ import annotations

from usv import cli_case_notes, event_check_runner
from usv.check_models import CheckResult, Verdict
from usv.event_flow_models import FlowCase
from usv.event_flow_run import CaseResult


def _case(event: str, name: str, status: str = "not_tested",
          reason: str = "step `tap` thất bại") -> CaseResult:
    return CaseResult(case=FlowCase(event=event, name=name),
                      status=status, reason=reason)


def _pass(element: str) -> CheckResult:
    return CheckResult(element=element, check="event_presence",
                       verdict=Verdict.PASS, expected="event được bắn ra",
                       actual="bắn 1 lần: 09-19 15:00:00.000")


def test_case_hut_van_hien_du_event_do_co_case_khac_pass():
    """Chinh la loi cu: event co cua so tu case khac nen nhanh NOT_TESTED
    khong chay, case hut bien mat khoi bang."""
    results = [_pass("rating_placement_viewed (popup o home)")]
    cases = [_case("rating_placement_viewed", "popup o home", status="ok"),
             _case("rating_placement_viewed", "popup o man result")]
    ra = cli_case_notes.them_dong_lai_hut(results, cases)
    hut = [r for r in ra if r.verdict is Verdict.NOT_TESTED]
    assert len(hut) == 1
    assert hut[0].element == "rating_placement_viewed (popup o man result)"
    assert "Lái hụt" in hut[0].message


def test_con_so_not_tested_dem_ca_dong_moi_them():
    results = [_pass("rating_placement_viewed (popup o home)")]
    cases = [_case("rating_placement_viewed", "popup o home", status="ok"),
             _case("rating_placement_viewed", "popup o man result")]
    ra = cli_case_notes.them_dong_lai_hut(results, cases)
    _, summary = event_check_runner.tong_hop(ra)
    assert summary.not_tested == 1
    assert summary.passed == 1


def test_khong_ke_hai_lan_khi_ca_event_khong_do_duoc():
    """Ca event khong co cua so -> event_presence da de lai mot dong gop."""
    results = [CheckResult(element="rating_star_clicked",
                           check="event_presence", verdict=Verdict.NOT_TESTED,
                           expected="event được bắn ra")]
    cases = [_case("rating_star_clicked", "cham 1 sao"),
             _case("rating_star_clicked", "cham 2 sao")]
    ra = cli_case_notes.them_dong_lai_hut(results, cases)
    assert len(ra) == 1


def test_case_blocked_ghi_dung_la_tien_de_chua_dat():
    results = [_pass("e (a)")]
    cases = [_case("e", "a", status="ok"),
             _case("e", "b", status="blocked", reason="reset không ăn")]
    ra = cli_case_notes.them_dong_lai_hut(results, cases)
    hut = [r for r in ra if r.verdict is Verdict.NOT_TESTED]
    assert "Tiền đề chưa đạt" in hut[0].message


def test_case_chay_duoc_thi_khong_them_dong():
    results = [_pass("e (a)")]
    ra = cli_case_notes.them_dong_lai_hut(results, [_case("e", "a", status="ok")])
    assert ra == results
