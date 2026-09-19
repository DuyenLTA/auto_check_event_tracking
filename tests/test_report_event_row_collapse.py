"""Gop dong trung trong bang report. Kiem nhung thu SAI THI KHONG AI THAY:
  - gop nham hai dong khac gia tri -> giau mat mot sai lech dang le phai doc duoc
  - gop roi tru luon vao "n/m khop" -> bao cao noi doi ve so luong da kiem
  - quen huy hieu xN -> nhin tuong chi co mot case cham, khong biet co nam
"""

from __future__ import annotations

from usv import report_event_html
from usv.check_models import CheckResult, Summary, Verdict
from usv.report_event_row_collapse import gop_dong_trung


def _dong(actual: str, *, element: str = "rating_star_clicked.placement_name",
          verdict: Verdict = Verdict.PASS, message: str = "") -> CheckResult:
    return CheckResult(element=element, check="event_params", verdict=verdict,
                       expected="String: exit_click, home", actual=actual,
                       message=message)


def test_dong_giong_het_nhau_gop_lam_mot_kem_so_lan():
    ra = gop_dong_trung([_dong("exit_click") for _ in range(5)])
    assert [(r.actual, n) for r, n in ra] == [("exit_click", 5)]


def test_khac_gia_tri_thi_khong_gop():
    ra = gop_dong_trung([_dong("exit_click"), _dong("home"), _dong("exit_click")])
    assert [(r.actual, n) for r, n in ra] == [("exit_click", 2), ("home", 1)]


def test_khac_ket_luan_thi_khong_gop():
    """Cung gia tri nhung mot dong FAIL - gop vao la mat han dong FAIL."""
    ra = gop_dong_trung([
        _dong("exit_click"),
        _dong("exit_click", verdict=Verdict.FAIL_VALUE, message="sai cho nay"),
    ])
    assert len(ra) == 2
    assert any(r.verdict is Verdict.FAIL_VALUE for r, _ in ra)


def test_khac_ghi_chu_thi_khong_gop():
    ra = gop_dong_trung([_dong("exit_click", message="a"),
                         _dong("exit_click", message="b")])
    assert len(ra) == 2


def test_dong_presence_khong_lan_vao_dong_param():
    """Cung element, khac `check` -> hai dong rieng."""
    a = _dong("exit_click")
    b = CheckResult(element=a.element, check="event_presence",
                    verdict=Verdict.PASS, expected=a.expected,
                    actual=a.actual)
    assert len(gop_dong_trung([a, b])) == 2


def test_giu_thu_tu_gap_dau_tien():
    ra = gop_dong_trung([_dong("home"), _dong("exit_click"), _dong("home")])
    assert [r.actual for r, _ in ra] == ["home", "exit_click"]


def _html(rows: list[CheckResult]) -> str:
    return report_event_html.build(
        _spec(), rows,
        Summary(passed=len(rows), failed=0),
        package="x.y.z")


def _spec():
    from usv.event_spec_parse import parse_paste
    return parse_paste(
        "Event Name\tParameter Name\tType\tValues\tDescription\n"
        "rating_star_clicked\tplacement_name\tString\texit_click, home\tvi tri\n")


def test_bang_in_mot_dong_kem_huy_hieu_nhung_ti_le_van_dem_du():
    """Gop 5 dong -> bang con 1 dong 'x5', nhung van la 5/5 khop."""
    html = _html([_dong("exit_click") for _ in range(5)])
    # Bang con dung mot dong param, nhung ti le van tinh du nam ket qua.
    assert html.count("placement_name") == 1
    assert "×5" in html
    # Scorecard van phai noi da kiem 5 muc, khong phai 1.
    assert "/ 5 mục đã kiểm" in html
