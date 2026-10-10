"""Cham event ban DUNG LUC cu bam kich hoat (moc `@bấm`)."""

from __future__ import annotations

from usv.check_config import parse
from usv.check_models import Verdict
from usv.checks import event_timing
from usv.event_flow_models import FlowCase, Step
from usv.event_spec_parse import parse_paste
from usv.event_window import TAP_PREFIX, cut_log, mark_label, with_delays

SPEC = parse_paste("Event_Name\tParams\tValue Type\nsetting_click\t\t\nsetting_view\t\t\n")
CONFIG = parse({})


def _log(*dong):
    return "\n".join(dong)


def _mark(sec_ms, label):
    return f"09-08 15:00:{sec_ms} I/USV_MARK( 9): {label}"


def _event(sec_ms, name):
    return (f"09-08 15:00:{sec_ms} V/FA-SVC  ( 9): Logging event: origin=app,"
            f"name={name},params=Bundle[{{a=1}}]")


def _cham(text, delays=None):
    windows = cut_log(text)
    if delays:
        windows = with_delays(windows, delays)
    return event_timing.run(SPEC, windows, CONFIG)


CASE = mark_label("setting_click", "icon Setting")
TAP = TAP_PREFIX + "tap desc='Setting'"


def test_ban_ngay_sau_cu_bam_la_pass_va_ghi_do_tre():
    [r] = _cham(_log(_mark("01.000", CASE), _mark("40.000", TAP),
                     _event("40.300", "setting_click")))
    assert r.verdict == Verdict.PASS
    assert "300 ms" in r.actual


def test_ban_truoc_cu_bam_la_sai_thoi_diem_du_van_trong_cua_so():
    """Presence se PASS (event nam trong cua so case) - timing phai bat duoc."""
    [r] = _cham(_log(_mark("01.000", CASE), _event("05.000", "setting_click"),
                     _mark("40.000", TAP)))
    assert r.verdict == Verdict.FAIL_TIMING
    assert "TRƯỚC" in r.actual


def test_ban_tre_qua_nguong_la_sai_thoi_diem():
    [r] = _cham(_log(_mark("01.000", CASE), _mark("10.000", TAP),
                     _event("13.000", "setting_click")))
    assert r.verdict == Verdict.FAIL_TIMING


def test_view_co_nguong_rong_hon_click():
    view = mark_label("setting_view", "man Setting")
    [r] = _cham(_log(_mark("01.000", view), _mark("10.000", TAP),
                     _event("13.000", "setting_view")))
    assert r.verdict == Verdict.PASS


def test_case_khai_max_delay_ms_thi_dung_nguong_cua_case():
    [r] = _cham(_log(_mark("01.000", CASE), _mark("10.000", TAP),
                     _event("13.000", "setting_click")),
                delays={"icon Setting": 5000})
    assert r.verdict == Verdict.PASS


def test_khong_co_moc_cu_bam_thi_khong_ra_dong_nao():
    assert _cham(_log(_mark("01.000", CASE), _event("02.000", "setting_click"))) == []


def test_moc_cu_bam_khong_cat_cua_so():
    windows = cut_log(_log(_mark("01.000", CASE), _mark("02.000", TAP),
                           _event("02.200", "setting_click")))
    assert len(windows) == 1 and windows[0].tap_ms is not None


def test_buoc_kich_hoat_mac_dinh_la_thao_tac_bat_buoc_cuoi():
    case = FlowCase(event="x", steps=(
        Step(kind="tap", text="", optional=False),
        Step(kind="wait", seconds=1),
        Step(kind="tap", optional=True),
    ))
    assert case.trigger_index == 0
    chi_dinh = FlowCase(event="x", steps=(Step(kind="tap"), Step(kind="tap", trigger=True),
                                          Step(kind="key")))
    assert chi_dinh.trigger_index == 1


def test_moc_thay_man_cho_phep_event_truoc_moc_vai_giay():
    view = mark_label("setting_view", "man Setting")
    [r] = _cham(_log(_mark("01.000", view), _event("08.000", "setting_view"),
                     _mark("10.000", TAP_PREFIX + "wait_text 'Setting'")))
    assert r.verdict == Verdict.PASS


def test_moc_thay_man_event_som_qua_thi_sai():
    view = mark_label("setting_view", "man Setting")
    [r] = _cham(_log(_mark("01.000", view), _event("02.000", "setting_view"),
                     _mark("10.000", TAP_PREFIX + "wait_text 'Setting'")))
    assert r.verdict == Verdict.FAIL_TIMING


def test_after_event_lay_event_khac_lam_moc():
    from usv.event_window import with_after_events
    view = mark_label("setting_view", "man Setting")
    windows = with_after_events(cut_log(_log(
        _mark("01.000", view), _event("09.000", "setting_click"),
        _event("09.400", "setting_view"))), {"man Setting": "setting_click"})
    [r] = event_timing.run(SPEC, windows, CONFIG)
    assert r.verdict == Verdict.PASS and "400" in r.actual
