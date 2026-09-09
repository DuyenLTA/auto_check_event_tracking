"""Che do NHANH: khong danh dau tung buoc, gom ca phien thanh mot cua so.

Danh doi co y - mat kha nang biet event ban dung luc hay khong. Nen hai thu
BAT BUOC:
  - `duplicate` phai TAT: mot phien dai vao ra cung mot man thi event do ban
    lai la dung, bat len la bao oan.
  - Report va xlsx PHAI noi ra da chay che do nay, khong thi nguoi doc tuong
    da kiem ca thoi diem.
"""

from __future__ import annotations

from pathlib import Path

from usv import report_event_html
from usv.check_config import load as load_config
from usv.check_models import Verdict
from usv.event_spec_parse import parse_paste
from usv.event_window import WHOLE_SESSION, whole_session
from usv.fa_event_parse import parse_log

FIXTURES = Path(__file__).parent / "fixtures"
RAW_LOG = (FIXTURES / "fa-events-aip922.log").read_text(encoding="utf-8")
SPEC_TSV = (FIXTURES / "event-spec-rating.tsv").read_text(encoding="utf-8")
CONFIG = load_config()

EVENTS = [e for e in parse_log(RAW_LOG)[0] if e.from_app]


# --- gom cua so ---

def test_moi_event_trong_spec_mot_cua_so():
    windows = whole_session(("rating_placement_viewed", "rating_star_clicked"), EVENTS)
    assert [w.spec_event for w in windows] == [
        "rating_placement_viewed", "rating_star_clicked"]


def test_cua_so_nao_cung_trum_toan_bo_event_cua_phien():
    windows = whole_session(("rating_placement_viewed",), EVENTS)
    assert len(windows[0].events) == len(EVENTS)


def test_nhan_cua_so_noi_ro_la_ca_phien():
    windows = whole_session(("ev_a",), EVENTS)
    assert windows[0].note == WHOLE_SESSION


def test_spec_rong_thi_khong_co_cua_so():
    assert whole_session((), EVENTS) == ()


def test_phien_khong_co_event_nao_van_tao_duoc_cua_so():
    """Khong co event -> cua so rong -> check bao FAIL_MISSING, dung."""
    windows = whole_session(("ev_a",), [])
    assert len(windows) == 1 and windows[0].events == ()


def test_khong_co_gia_tri_case_doi_hoi():
    """Che do nhanh khong co case nen khong co gi de doi hoi chinh xac."""
    assert whole_session(("ev_a",), EVENTS)[0].expect_params == {}


# --- tat duplicate ---

def test_with_option_tat_duplicate_ma_khong_dung_den_file_config():
    quick = CONFIG.with_option("event_presence", "duplicate", False)
    assert quick.checks["event_presence"].options["duplicate"] is False
    assert CONFIG.checks["event_presence"].options["duplicate"] is True, \
        "khong duoc sua config goc"


def test_with_option_giu_nguyen_enabled_va_severity():
    quick = CONFIG.with_option("event_presence", "duplicate", False)
    goc, moi = CONFIG.checks["event_presence"], quick.checks["event_presence"]
    assert (moi.enabled, moi.severity) == (goc.enabled, goc.severity)


def test_with_option_voi_check_khong_ton_tai_thi_khong_lam_gi():
    assert CONFIG.with_option("khong_co", "x", 1) is CONFIG


def test_tat_duplicate_thi_event_ban_nhieu_lan_khong_thanh_fail():
    """`track_ad_request` ban 17 lan trong mot lan mo app."""
    from usv import event_check_runner

    spec = parse_paste(
        "Event_Name\tParams\tValue Type\tValue\n"
        "track_ad_request\tad_format\tString\t\n")
    windows = whole_session(("track_ad_request",), EVENTS)
    quick = CONFIG.with_option("event_presence", "duplicate", False)

    results, _ = event_check_runner.run(spec, windows, quick)
    assert not [r for r in results if r.verdict is Verdict.FAIL_DUPLICATE]

    bat, _ = event_check_runner.run(spec, windows, CONFIG)
    assert [r for r in bat if r.verdict is Verdict.FAIL_DUPLICATE], \
        "bat duplicate len thi phai bao - de chung minh test tren co y nghia"


# --- report phai noi ra ---

def test_report_noi_ro_da_chay_che_do_nhanh():
    from usv import event_check_runner

    spec = parse_paste(SPEC_TSV)
    windows = whole_session(tuple(e.name for e in spec.events), EVENTS)
    results, summary = event_check_runner.run(
        spec, windows, CONFIG.with_option("event_presence", "duplicate", False))
    page = report_event_html.build(spec, results, summary, quick=True)
    assert "chế độ nhanh" in page.lower()
    assert "không</b> kết luận event bắn đúng lúc" in page


def test_report_binh_thuong_khong_co_canh_bao_do():
    from usv import event_check_runner

    spec = parse_paste(SPEC_TSV)
    windows = whole_session(tuple(e.name for e in spec.events), EVENTS)
    results, summary = event_check_runner.run(spec, windows, CONFIG)
    page = report_event_html.build(spec, results, summary, quick=False)
    assert "Chạy ở chế độ nhanh" not in page
