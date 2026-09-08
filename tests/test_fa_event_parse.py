"""Parse dong logcat FA-SVC. Chay tren fixture THAT, khong mock.

Fixture tests/fixtures/fa-events-aip922.log la log that cua AIP922, da redact
id thiet bi va ad unit ID.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from usv.event_system_params import global_params, is_system, strip_system
from usv.fa_event_parse import Marker, ObservedEvent, parse_line, parse_log, parse_params

LOG = (Path(__file__).parent / "fixtures" / "fa-events-aip922.log").read_text(
    encoding="utf-8")
EVENTS, MARKERS = parse_log(LOG)

RATING_VIEWED = (
    "09-08 15:40:26.202 V/FA-SVC  ( 9320): Logging event: origin=app,"
    "name=rating_placement_viewed,params=Bundle[{placement_name=home, "
    "ga_event_origin(_o)=app, ga_screen_class(_sc)=AIP922Main, "
    "ga_screen_id(_si)=-671286583876492367}]"
)


def test_doc_du_67_event_tu_fixture():
    """Spike do 67 dong `Logging event`. Thieu dong nao la parse hong."""
    assert len(EVENTS) == 67


def test_phan_loai_theo_origin_dung_so_do_duoc():
    counts = {}
    for event in EVENTS:
        counts[event.origin] = counts.get(event.origin, 0) + 1
    assert counts == {"app": 42, "auto": 8, "am": 17}


def test_chi_origin_app_thuoc_pham_vi_spec():
    assert sum(1 for e in EVENTS if e.from_app) == 42


def test_hai_event_trong_spec_co_mat_va_dung_param():
    by_name = {e.name: e for e in EVENTS if e.from_app}
    assert by_name["rating_placement_viewed"].params == {"placement_name": "home"}
    assert by_name["rating_star_clicked"].params == {
        "placement_name": "home", "star_value": "3"}


def test_param_he_thong_bi_loc():
    event = parse_line(RATING_VIEWED)
    assert event.params == {"placement_name": "home"}
    assert "ga_event_origin" in event.raw_params, "raw_params phai giu de chan doan"


def test_hau_to_ngoac_bi_bo_o_ten_event():
    line = ("09-08 15:40:16.099 V/FA-SVC  ( 9320): Logging event: origin=auto,"
            "name=session_start(_s),params=Bundle[{ga_session_id(_sid)=1}]")
    assert parse_line(line).name == "session_start"


def test_gia_tri_dai_co_dau_cham_phay_va_backtick_khong_vo():
    """error_msg that dai 513 B, chua `:` `;` backtick, dau cham.

    Day la ly do KHONG dung split(", ").
    """
    hits = [e for e in EVENTS if e.name == "ump_request_failed"]
    assert hits, "fixture phai co ump_request_failed"
    params = hits[0].params
    assert "error_code" in params
    assert "Publisher misconfiguration" in params["error_msg"]


def test_split_khong_vo_khi_gia_tri_chua_dau_phay():
    body = "msg=a, b, c, code=3"
    assert parse_params(body) == {"msg": "a, b, c", "code": "3"}


def test_dong_bi_cat_tra_ve_truncated_thay_vi_bo_im_lang():
    """Bo im lang thi check bao 'thieu param' cho dong that ra co du param."""
    cut = ("09-08 15:40:26.202 V/FA-SVC  ( 9320): Logging event: origin=app,"
           "name=rating_star_clicked,params=Bundle[{placement_name=home, star_v")
    event = parse_line(cut)
    assert isinstance(event, ObservedEvent)
    assert event.truncated is True
    assert event.name == "rating_star_clicked"


def test_dong_khong_bi_cat_thi_truncated_false():
    assert parse_line(RATING_VIEWED).truncated is False
    assert all(not e.truncated for e in EVENTS), "fixture that khong co dong bi cat"


def test_nhan_dang_marker():
    line = "09-08 15:31:33.683 I/USV_MARK(11852): step=1 rating_placement_viewed"
    marker = parse_line(line)
    assert isinstance(marker, Marker)
    assert marker.label == "step=1 rating_placement_viewed"
    assert marker.timestamp == "09-08 15:31:33.683"


def test_dong_FA_logging_telemetry_khong_bi_coi_la_event():
    """Tag FA in dung 67 lan nhung KHONG kem params - khong duoc dem thanh event."""
    line = ("09-08 15:40:26.204 V/FA      (13959): "
            "Logging telemetry for logEvent from database")
    assert parse_line(line) is None


def test_dedupe_khong_de_mot_event_thanh_ban_2_lan():
    """Tag FA va FA-SVC cung in mot event o version SDK khac -> phai dedupe."""
    fe = ("09-08 15:40:26.202 V/FA      ( 100): Logging event (FE): "
          "rating_placement_viewed, Bundle[{placement_name=home}]")
    events, _ = parse_log(RATING_VIEWED + "\n" + fe)
    assert len(events) == 1


def test_dong_rac_tra_ve_None():
    assert parse_line("09-08 15:22:53.505 D/CHRE ( 1057): [ActivityPlatform]") is None
    assert parse_line("") is None


def test_screen_class_lay_duoc_cho_cot_screen_name():
    assert parse_line(RATING_VIEWED).screen_class == "AIP922Main"


def test_timestamp_doc_duoc():
    assert parse_line(RATING_VIEWED).timestamp == "09-08 15:40:26.202"


@pytest.mark.parametrize("name", [
    "ga_event_origin", "ga_screen_class", "_o", "_sc", "engagement_time_msec",
    "session_id", "firebase_screen_class", "",
])
def test_is_system_bat_dung(name):
    assert is_system(name) is True


@pytest.mark.parametrize("name", ["placement_name", "star_value", "error_code"])
def test_is_system_khong_bat_oan_param_that(name):
    assert is_system(name) is False


def test_strip_system_giu_thu_tu():
    got = strip_system({"placement_name": "home", "ga_event_origin": "app",
                        "star_value": "3"})
    assert list(got) == ["placement_name", "star_value"]


def test_global_params_can_it_nhat_2_event():
    """Mot event thi param nao cung 'co mat o 100% event' - vo nghia."""
    assert global_params([frozenset({"a", "b"})]) == frozenset()


def test_global_params_tim_ra_param_co_o_moi_event():
    sets = [frozenset({"a", "x"}), frozenset({"a", "y"}), frozenset({"a", "z"})]
    assert global_params(sets) == frozenset({"a"})


def test_fixture_that_khong_co_global_param_ngoai_he_thong():
    """Do tren AIP922: khong co global param tu khai nao.

    Neu test nay do tren mot fixture app khac thi la dau hieu phai bat
    global_param_heuristic trong YAML.
    """
    sets = [frozenset(e.params) for e in EVENTS if e.from_app]
    assert global_params(sets) == frozenset()
