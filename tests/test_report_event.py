"""Report event HTML. Kiem nhung thu SAI THI KHONG AI THAY:
  - mau so scorecard tron NOT_TESTED/EXTRA vao -> ti le sai, app trong nhu hong hon
  - thieu mot tang theme -> mot nua nguoi xem doc chu mau nay tren nen mau kia
  - khong escape gia tri tu log -> HTML vo, hoac chen duoc script
"""

from __future__ import annotations

import re
from pathlib import Path

from usv import event_check_runner, report_event_html
from usv.check_config import load as load_config
from usv.check_models import CheckResult, Summary, Verdict
from usv.event_spec_parse import parse_paste
from usv.event_window import cut_log, mark_label

FIXTURES = Path(__file__).parent / "fixtures"
RAW_LOG = (FIXTURES / "fa-events-aip922.log").read_text(encoding="utf-8")
SPEC_TSV = (FIXTURES / "event-spec-rating.tsv").read_text(encoding="utf-8")
CONFIG = load_config()

MARKS = [
    "09-08 15:40:26.100 I/USV_MARK( 9): "
    + mark_label("rating_placement_viewed", "Khi màn rating hiển thị"),
    "09-08 15:40:29.100 I/USV_MARK( 9): "
    + mark_label("rating_star_clicked", "Khi user click rate"),
]


def _build(spec_tsv: str = SPEC_TSV, **kwargs) -> str:
    spec = parse_paste(spec_tsv)
    windows = cut_log("\n".join([*RAW_LOG.splitlines(), *MARKS]))
    results, summary = event_check_runner.run(spec, windows, CONFIG)
    return report_event_html.build(spec, results, summary, package="com.x",
                                   event_count=67, **kwargs)


HTML = _build()


def test_render_ra_html_co_tieu_de():
    assert "<title>Event Tracking Diff</title>" in HTML
    assert "Event Tracking Diff" in HTML


def test_du_ba_tang_theme():
    """Thieu tang nao la mot nua nguoi xem doc sai mau."""
    assert ":root{" in HTML
    assert "@media (prefers-color-scheme: dark)" in HTML
    assert ':root:not([data-theme="light"])' in HTML
    assert ':root[data-theme="dark"]' in HTML


def test_body_co_background_tu_token():
    """Body trong suot thi no vay nen cua trang chu -> sai theme."""
    assert "background:var(--paper)" in HTML


def test_khong_mau_nao_chi_ton_tai_trong_media_query():
    """Moi ten token phai duoc dinh nghia o :root tran truoc."""
    root = HTML.split(":root{", 1)[1].split("}", 1)[0]
    declared = set(re.findall(r"(--[a-z-]+):", root))
    used = set(re.findall(r"var\((--[a-z-]+)\)", HTML))
    assert used <= declared, f"token chua khai o :root: {used - declared}"


def test_bang_rong_co_the_cuon_ngang_rieng():
    assert "overflow-x:auto" in HTML


def test_mau_so_scorecard_KHONG_gom_not_tested_va_extra():
    """Day la cai de sai nhat: tron vao thi bao mot ti le sai."""
    spec = parse_paste(SPEC_TSV)
    results = [
        CheckResult(element="a", check="event_presence", verdict=Verdict.PASS),
        CheckResult(element="b", check="event_presence", verdict=Verdict.FAIL_MISSING),
        CheckResult(element="c", check="event_presence", verdict=Verdict.NOT_TESTED),
        CheckResult(element="d", check="event_presence", verdict=Verdict.EXTRA),
    ]
    summary = Summary()
    for item in results:
        summary.add(item)
    page = report_event_html.build(spec, results, summary)
    assert "/ 2 khớp" in page, "mau so phai la 2 (1 pass + 1 fail), khong phai 4"


def test_chua_test_va_app_co_them_hien_thanh_chip_rieng():
    spec = parse_paste(SPEC_TSV)
    results = [CheckResult(element="c", check="event_presence",
                           verdict=Verdict.NOT_TESTED)]
    summary = Summary()
    summary.add(results[0])
    page = report_event_html.build(spec, results, summary)
    assert "chưa test" in page


def test_du_bon_class_trang_thai_khi_co_du_verdict():
    spec = parse_paste(SPEC_TSV)
    results = [
        CheckResult(element="a.p", check="event_params", verdict=Verdict.PASS),
        CheckResult(element="b.p", check="event_params", verdict=Verdict.FAIL_VALUE),
        CheckResult(element="c.p", check="event_params", verdict=Verdict.NOT_VERIFIABLE),
        CheckResult(element="d", check="event_presence", verdict=Verdict.NOT_TESTED),
    ]
    summary = Summary()
    for item in results:
        summary.add(item)
    page = report_event_html.build(spec, results, summary)
    for cls in ("status pass", "status fail", "status pending", "status muted"):
        assert cls in page, f"thieu class {cls}"


def test_dong_fail_duoc_danh_dau_row_fail():
    spec = parse_paste(SPEC_TSV)
    results = [CheckResult(element="a.p", check="event_params",
                           verdict=Verdict.FAIL_VALUE)]
    summary = Summary()
    summary.add(results[0])
    assert 'class="row-fail"' in report_event_html.build(spec, results, summary)


def test_callout_fa_silent_xuat_hien():
    page = _build(fa_silent=True)
    assert "Không đọc được log Firebase" in page
    assert "không phải" in page.lower() or "KHÔNG phải" in page


def test_khong_fa_silent_thi_khong_co_callout_do():
    assert "Không đọc được log Firebase" not in HTML


def test_callout_near_edge_xuat_hien_va_noi_khong_tu_doi():
    page = _build(near_edge=("rating_star_clicked",))
    assert "sát mốc đánh dấu" in page
    assert "không</b> tự đổi bước" in page


def test_bao_cao_khong_liet_ke_event_la_cua_app():
    """Chi bao ve event co trong spec. Log that day event khong lien quan
    (track_ad_request 22 lan, screen_view, ad_query...) - liet ke het thi thu
    can doc bi chim."""
    assert "track_ad_request" not in HTML
    assert "screen_view" not in HTML


def test_param_la_van_vao_callout_khong_tinh_vao_fail():
    """Param duoc coi la global param cua app thi bao rieng, khong tinh fail -
    duong nay con dung, chi tang EVENT la bo di."""
    from usv.check_models import CheckResult, Summary, Verdict
    extra = CheckResult(element="rating_star_clicked.ga_extra", check="event_params",
                        verdict=Verdict.EXTRA, actual="x",
                        message="Param nay co o moi event. Không tính vào fail.")
    summary = Summary()
    summary.add(extra)
    page = report_event_html.build(parse_paste(SPEC_TSV), [extra], summary)
    assert "Không tính vào fail" in page


def test_gia_tri_tu_log_duoc_escape():
    """Gia tri log la du lieu KHONG kiem soat."""
    spec = parse_paste(SPEC_TSV)
    results = [CheckResult(
        element="evil.param", check="event_params", verdict=Verdict.FAIL_VALUE,
        actual="<script>alert(1)</script>", expected="<b>x</b>",
        message="loi & nguy hiem <img>")]
    summary = Summary()
    summary.add(results[0])
    page = report_event_html.build(spec, results, summary)
    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;" in page
    assert "&amp;" in page


def test_van_xuoi_cot_triggered_hien_lam_nhan():
    assert "Khi màn rating hiển thị" in HTML


def test_section_chia_theo_screen_name():
    assert "Home" in HTML


def test_section_toan_chua_test_noi_chua_test_chu_khong_phai_0_tren_0():
    """'0/0 khớp' la vo nghia voi nguoi doc."""
    spec = parse_paste(
        "Screen Name\tEvent_Name\tParams\tValue Type\tValue\n"
        "Result\trating_dismissed\tplacement_name\tString\thome\n")
    results = [CheckResult(element="rating_dismissed", check="event_presence",
                           verdict=Verdict.NOT_TESTED)]
    summary = Summary()
    summary.add(results[0])
    page = report_event_html.build(spec, results, summary)
    assert "0/0 khớp" not in page
    assert "chưa test (1)" in page


def test_callout_stream_dut_xuat_hien():
    """Phien ghi chet ma bao cao im lang thi nguoi doc ket luan sai ve app."""
    page = _build(stream_died=True)
    assert "đứt giữa đường" in page
    # Phai noi ro: "khong bat duoc" o day KHONG tinh la loi app.
    assert "không tính là lỗi app" in page


def test_khong_dut_thi_khong_co_callout_do():
    assert "đứt giữa đường" not in HTML


def test_ten_event_khong_lap_lai_o_dong_param():
    """Spec 2 event ma bang 5 dong (2 dong event + 3 dong param) - lap ten
    event o moi dong thi doc vao tuong 5 event, va nguoi doc di hoi "5 event o
    dau ra". Chi in ten o dong DAU cua moi event."""
    page = _build()
    assert page.count("<code>rating_star_clicked</code>") == 1, (
        "ten event chi duoc in mot lan cho ca nhom dong cua no")
    assert page.count("<code>rating_placement_viewed</code>") == 1


def test_bao_cao_noi_ro_bao_nhieu_event_va_bao_nhieu_muc_kiem():
    """Con so dau tien nguoi doc thay phai la SO EVENT, khong phai so dong."""
    page = _build()
    assert "2 event trong spec" in page


def test_callout_app_khong_chay_xuat_hien():
    page = _build(app_seen=False)
    assert "không chạy lần nào" in page
    assert "app khác" in page


def test_app_co_chay_thi_khong_co_callout_do():
    assert "không chạy lần nào" not in HTML
