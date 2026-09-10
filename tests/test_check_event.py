"""Cham check event tren LOG THAT + SPEC THAT.

Sau case duoi day da chay trong spike truoc khi viet code. Case A la quan trong
nhat: spec dung -> KHONG duoc co fail oan nao. Do la thu quyet dinh tool co dung
duoc hay khong; cac case sau chi co nghia neu case A xanh.
"""

from __future__ import annotations

from pathlib import Path

from usv import event_check_runner
from usv.check_config import load as load_config
from usv.check_models import Verdict
from usv.event_spec_parse import parse_paste
from usv.event_window import cut_log, mark_label

FIXTURES = Path(__file__).parent / "fixtures"
RAW_LOG = (FIXTURES / "fa-events-aip922.log").read_text(encoding="utf-8")
SPEC_TSV = (FIXTURES / "event-spec-rating.tsv").read_text(encoding="utf-8")

CONFIG = load_config()

# Hai event rating trong fixture ban luc 15:40:26.202 va 15:40:29.545.
# Chen moc ngay truoc moi cai -> hai cua so.
MARK_VIEWED = (f"09-08 15:40:26.100 I/USV_MARK( 999): "
               f"{mark_label('rating_placement_viewed', 'Khi màn rating hiển thị')}")
MARK_STAR = (f"09-08 15:40:29.100 I/USV_MARK( 999): "
             f"{mark_label('rating_star_clicked', 'Khi user click rate')}")


def _log(*extra: str) -> str:
    lines = RAW_LOG.splitlines()
    return "\n".join([*lines, MARK_VIEWED, MARK_STAR, *extra])


def _run(spec_tsv: str = SPEC_TSV, log_text: str | None = None,
         *, fa_silent: bool = False, stream_died: bool = False):
    spec = parse_paste(spec_tsv)
    assert spec.errors == (), spec.errors
    windows = cut_log(log_text if log_text is not None else _log())
    return event_check_runner.run(spec, windows, CONFIG, fa_silent=fa_silent,
                                  stream_died=stream_died)


def _by_verdict(results):
    out: dict[str, list] = {}
    for item in results:
        out.setdefault(str(item.verdict), []).append(item)
    return out


# --- Case A: spec dung ---

def test_A_spec_dung_khong_co_fail_oan():
    """3 param dung -> 3 PASS. Va KHONG mot fail nao.

    Neu param he thong (`ga_event_origin`, `ga_screen_class`, `ga_screen_id`)
    khong bi loc thi day la cho no lo ra: moi event se co FAIL_PARAM_EXTRA.
    """
    results, summary = _run()
    assert summary.failed == 0, [
        (r.element, str(r.verdict), r.message) for r in results if r.failed]
    param_pass = [r for r in results
                  if r.check == "event_params" and r.verdict is Verdict.PASS]
    assert len(param_pass) == 3


def test_A_hai_event_deu_PASS_o_presence():
    results, _ = _run()
    presence = [r for r in results if r.check == "event_presence"
                and r.verdict is Verdict.PASS]
    assert {r.element for r in presence} == {
        "rating_placement_viewed", "rating_star_clicked"}


def test_A_param_he_thong_khong_bi_bao_thua():
    results, _ = _run()
    extras = [r.element for r in results
              if r.verdict is Verdict.FAIL_PARAM_EXTRA]
    assert extras == []


def test_A_event_ngoai_spec_khong_lam_bao_cao_thanh_fail():
    """Log that day event khong lien quan (track_ad_request, screen_view,
    ad_query...). Chung khong duoc lam bao cao xau di - va tu ban 260910 cung
    khong duoc liet ke ra nua, xem test_khong_liet_ke_event_la_cua_app."""
    _, summary = _run()
    assert summary.failed == 0


def test_A_ban_17_lan_trong_phien_khong_thanh_FAIL_DUPLICATE():
    """`track_ad_request` ban 17x/phien. Cham theo cua so nen khong phai fail."""
    results, _ = _run()
    assert not [r for r in results if r.verdict is Verdict.FAIL_DUPLICATE]


# --- Case B..E: gai loi ---

def test_B_gia_tri_ngoai_danh_sach():
    spec = SPEC_TSV.replace("result, exit_click, app_shortcut, home",
                            "result, exit_click, app_shortcut")
    results, _ = _run(spec)
    fails = [r for r in results if r.verdict is Verdict.FAIL_VALUE]
    assert len(fails) == 2
    assert all("home" in r.actual for r in fails)


def test_C_sai_kieu_spec_Number_ma_app_gui_chu():
    spec = SPEC_TSV.replace("placement_name\t\tString", "placement_name\t\tNumber")
    results, _ = _run(spec)
    fails = [r for r in results if r.verdict is Verdict.FAIL_TYPE]
    assert len(fails) == 2


def test_D_spec_khai_param_app_khong_gui():
    spec = SPEC_TSV + "\t\t\trating_source\t\tString\tpopup, menu\tNguồn\n"
    results, _ = _run(spec)
    fails = [r for r in results if r.verdict is Verdict.FAIL_MISSING
             and "rating_source" in r.element]
    assert len(fails) == 1


def test_E_spec_ghi_sai_ten_event():
    spec = SPEC_TSV.replace("rating_star_clicked", "rating_star_click")
    log_text = _log().replace(mark_label("rating_star_clicked", "Khi user click rate"),
                              mark_label("rating_star_click", "Khi user click rate"))
    results, _ = _run(spec, log_text)
    fails = [r for r in results if r.verdict is Verdict.FAIL_MISSING
             and r.element.startswith("rating_star_click")]
    assert fails, "spec sai ten event phai ra FAIL_MISSING"


def test_F_String_mang_gia_tri_so_ra_NOT_VERIFIABLE():
    """`error_code=3`, spec khai String -> khong phan biet duoc Long va "3"."""
    spec = ("Event_Name\tTriggered\tParams\tValue Type\tValue\n"
            "ump_request_failed\tKhi UMP that bai\terror_code\tString\t\n")
    mark = ("09-08 15:40:16.200 I/USV_MARK( 999): "
            + mark_label("ump_request_failed", "Khi UMP that bai"))
    log_text = "\n".join([*RAW_LOG.splitlines(), mark])
    results, _ = _run(spec, log_text)
    nv = [r for r in results if r.verdict is Verdict.NOT_VERIFIABLE
          and "error_code" in r.element]
    assert len(nv) == 1
    assert "String hay Number" in nv[0].message


# --- Cac guard ---

def test_event_khong_co_moc_nao_ra_NOT_TESTED_khong_phai_fail():
    results, summary = _run(log_text=RAW_LOG)   # log khong co USV_MARK nao
    not_tested = [r for r in results if r.verdict is Verdict.NOT_TESTED]
    assert len(not_tested) == 2
    assert summary.failed == 0
    assert summary.not_tested == 2


def test_ban_trung_trong_CUNG_MOT_cua_so_thanh_FAIL_DUPLICATE():
    dupe = ("09-08 15:40:27.000 V/FA-SVC  ( 9320): Logging event: origin=app,"
            "name=rating_placement_viewed,params=Bundle[{placement_name=home}]")
    results, _ = _run(log_text=_log() + "\n" + dupe)
    fails = [r for r in results if r.verdict is Verdict.FAIL_DUPLICATE]
    assert len(fails) == 1
    assert "2 lần" in fails[0].actual


def test_fa_silent_thi_khong_ket_luan_app_thieu_event():
    """R3: build strip log Firebase. Bao NOT_VERIFIABLE, khong bao FAIL_MISSING."""
    only_marks = "\n".join([MARK_VIEWED, MARK_STAR])
    results, summary = _run(log_text=only_marks, fa_silent=True)
    assert summary.failed == 0
    nv = [r for r in results if r.verdict is Verdict.NOT_VERIFIABLE]
    assert nv and any("strip log" in r.message for r in nv)


def test_khong_fa_silent_thi_van_bao_thieu_event():
    only_marks = "\n".join([MARK_VIEWED, MARK_STAR])
    results, summary = _run(log_text=only_marks, fa_silent=False)
    assert summary.failed == 2
    assert all(r.verdict is Verdict.FAIL_MISSING
               for r in results if r.check == "event_presence" and r.failed)


def test_dong_bi_cat_ra_NOT_VERIFIABLE_khong_bao_thieu_param():
    cut = ("09-08 15:40:26.202 V/FA-SVC  ( 9320): Logging event: origin=app,"
           "name=rating_placement_viewed,params=Bundle[{placement_na")
    log_text = "\n".join([MARK_VIEWED, cut, MARK_STAR])
    results, _ = _run(log_text=log_text)
    nv = [r for r in results if r.verdict is Verdict.NOT_VERIFIABLE
          and r.check == "event_params"]
    assert nv and "bị logcat cắt" in nv[0].message


# --- case tu dong: cham theo gia tri CASE doi hoi, chat hon spec ---

def _window_with_expect(place: str, expect: dict[str, str]):
    """Cua so co event ban ra `place`, va case doi hoi `expect`."""
    from usv.event_window import cut_log, mark_label, with_expectations
    log = "\n".join([
        "09-08 15:00:01.000 I/USV_MARK( 9): "
        + mark_label("rating_placement_viewed", "case X"),
        "09-08 15:00:02.000 V/FA-SVC ( 9): Logging event: origin=app,"
        f"name=rating_placement_viewed,params=Bundle[{{placement_name={place}}}]",
    ])
    return with_expectations(cut_log(log), {"case X": expect})


def test_case_bat_duoc_loi_ma_SPEC_KHONG_bat_duoc():
    """Lỗi thật hay gặp: màn Result nhưng app gửi placement_name=home.

    Spec cho phép cả result LẪN home nên chấm theo spec là PASS. Case thì lái
    app tới đúng màn Result nên nó biết lần này PHẢI là 'result'.
    """
    spec = parse_paste(SPEC_TSV)
    windows = _window_with_expect("home", {"placement_name": "result"})
    results, _ = event_check_runner.run(spec, windows, CONFIG)
    fails = [r for r in results if r.verdict is Verdict.FAIL_VALUE]
    assert len(fails) == 1
    assert "result" in fails[0].expected and "home" in fails[0].actual


def test_khong_cham_theo_spec_thi_dung_la_PASS():
    """Chung minh cau tren: cung du lieu, khong co expect thi spec cho qua."""
    spec = parse_paste(SPEC_TSV)
    windows = _window_with_expect("home", {})
    results, _ = event_check_runner.run(spec, windows, CONFIG)
    assert not [r for r in results if r.verdict is Verdict.FAIL_VALUE]


def test_case_dung_gia_tri_thi_PASS():
    spec = parse_paste(SPEC_TSV)
    windows = _window_with_expect("home", {"placement_name": "home"})
    results, _ = event_check_runner.run(spec, windows, CONFIG)
    assert not [r for r in results if r.failed]


def test_case_doi_hoi_gia_tri_NGOAI_spec_van_bao_sai():
    """Case ghi sai thì cũng phải lộ ra, không im lặng cho qua."""
    spec = parse_paste(SPEC_TSV)
    windows = _window_with_expect("home", {"placement_name": "khong_co_trong_spec"})
    results, _ = event_check_runner.run(spec, windows, CONFIG)
    assert [r for r in results if r.verdict is Verdict.FAIL_VALUE]


def test_stream_dut_thi_khong_ket_luan_app_thieu_event():
    """May rot khoi USB giua phien -> phan sau khong duoc ghi.

    Do that: may rot luc 14:31, tester bam tiep 69 phut, log dong bang o 315
    dong, va tool bao 2 FAIL_MISSING - mot ket luan sai ve app tren mot phien
    ghi da chet. Cung nguyen tac voi fa_silent: khong doc duoc thi khong ket
    luan, chu khong bao FAIL.
    """
    only_marks = "\n".join([MARK_VIEWED, MARK_STAR])
    results, summary = _run(log_text=only_marks, stream_died=True)
    assert summary.failed == 0
    nv = [r for r in results if r.verdict is Verdict.NOT_VERIFIABLE]
    assert nv and any("đứt giữa đường" in r.message for r in nv)


def test_stream_khong_dut_thi_van_bao_thieu_event():
    """Chieu nguoc lai - thieu test nay thi mot bug lam co luon-bat cung xanh."""
    only_marks = "\n".join([MARK_VIEWED, MARK_STAR])
    results, summary = _run(log_text=only_marks, stream_died=False)
    assert summary.failed == 2


def test_khong_liet_ke_event_la_cua_app():
    """Chi cham event CO TRONG SPEC.

    App that ban hang chuc event khong lien quan (ad_load 22 lan,
    track_ad_request 22 lan, splash_view, session_start...). Liet ke het ra thi
    bao cao loang, va thu can doc bi chim giua dong event vo thuong vo phat.
    """
    results, summary = _run()
    la = [r for r in results if r.verdict is Verdict.EXTRA]
    assert not la, f"khong duoc liet ke event la: {[r.element for r in la]}"
    assert summary.extra == 0
    trong_spec = {"rating_placement_viewed", "rating_star_clicked"}
    for item in results:
        goc = item.element.split(".")[0].split(" (")[0]
        assert goc in trong_spec, f"{item.element!r} khong co trong spec"


def test_van_cham_du_event_trong_spec():
    """Chieu nguoc lai - bo loc qua tay thi mat luon event can cham."""
    results, _ = _run()
    assert {r.element.split(".")[0].split(" (")[0] for r in results} == {
        "rating_placement_viewed", "rating_star_clicked"}
