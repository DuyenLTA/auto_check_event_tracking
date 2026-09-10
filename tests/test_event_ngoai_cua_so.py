"""Event ban NGOAI buoc da danh dau -> chua ket luan, KHONG phai fail.

Da gap that tren may: spec 2 event (`daily_checkin_screen_view`,
`daily_checkin_button_clicked`). App bat man daily checkin ngay khi mo, nen
screen_view ban TRUOC khi tester kip bam moc dau tien; `cut()` bo moi event
truoc moc dau -> bao "Thieu event" cho mot event app ban dung. Cung app do,
cham o che do khong danh dau thi ra 2 PASS.

Mot verdict doi theo THU TU BAM NUT thi khong dung duoc. Moc do TESTER bam,
event do APP ban - tool khong biet ai truoc ai sau, nen phai tra "chua ket
luan" chu khong tra fail.
"""

from __future__ import annotations

from usv import event_check_runner
from usv.check_config import load as load_config
from usv.check_models import Verdict
from usv.event_spec_parse import parse_paste
from usv.event_window import cut, mark_label
from usv.fa_event_parse import parse_log

CONFIG = load_config()

SPEC = "\t".join(["Screen Name", "Event_Name", "Triggered", "Params",
                  "Param Description", "Value Type", "Value",
                  "Value Description"]) + "\n" + "\n".join([
    "\t".join(["Daily", "daily_checkin_screen_view", "Khi màn checkin hiển thị",
               "", "", "", "", ""]),
    "\t".join(["Daily", "daily_checkin_button_clicked", "Khi user bấm checkin",
               "", "", "", "", ""]),
])


def _dong(stamp: str, name: str) -> str:
    return (f"09-10 {stamp} V/FA-SVC  ( 9320): Logging event: origin=app,"
            f"name={name},params=Bundle[{{ga_event_origin(_o)=app}}]")


def _moc(stamp: str, spec_event: str, note: str) -> str:
    return (f"09-10 {stamp} I/USV_MARK( 999): "
            f"{mark_label(spec_event, note)}")


# App mo -> screen_view ban NGAY (16:54:10), tester bam moc sau (16:54:15),
# bam moc thu hai (16:54:20) roi click -> button_clicked ban (16:54:21).
LOG_BAN_TRUOC_MOC = "\n".join([
    _dong("16:54:10.100", "daily_checkin_screen_view"),
    _dong("16:54:11.000", "splash_view"),
    _moc("16:54:15.000", "daily_checkin_screen_view", "Khi màn checkin hiển thị"),
    _dong("16:54:16.000", "some_other_event"),
    _moc("16:54:20.000", "daily_checkin_button_clicked", "Khi user bấm checkin"),
    _dong("16:54:21.312", "daily_checkin_button_clicked"),
])

# Cung kich ban nhung app KHONG he ban screen_view lan nao.
LOG_KHONG_BAN = "\n".join([
    _dong("16:54:11.000", "splash_view"),
    _moc("16:54:15.000", "daily_checkin_screen_view", "Khi màn checkin hiển thị"),
    _dong("16:54:16.000", "some_other_event"),
    _moc("16:54:20.000", "daily_checkin_button_clicked", "Khi user bấm checkin"),
    _dong("16:54:21.312", "daily_checkin_button_clicked"),
])


def _cham(log_text: str):
    """Cham y nhu route /event/check lam: truyen event CA PHIEN vao check."""
    spec = parse_paste(SPEC)
    assert spec.errors == (), spec.errors
    events, markers = parse_log(log_text)
    windows = cut(events, markers)
    return event_check_runner.run(
        spec, windows, CONFIG,
        session_events=tuple(e for e in events if e.from_app))


def _tim(results, name: str, check: str = "event_presence"):
    for item in results:
        if item.check == check and item.element.startswith(name):
            return item
    raise AssertionError(f"khong co dong {check} cho {name}")


def test_ban_truoc_moc_dau_tien_khong_bi_bao_thieu():
    results, _ = _cham(LOG_BAN_TRUOC_MOC)
    muc = _tim(results, "daily_checkin_screen_view")
    assert muc.verdict is Verdict.NOT_VERIFIABLE, muc.message
    assert muc.verdict is not Verdict.FAIL_MISSING


def test_ban_truoc_moc_van_khong_lam_tang_so_fail():
    """Cai nguoi dung nhin thay dau tien la con so o dong tong ket."""
    _, summary = _cham(LOG_BAN_TRUOC_MOC)
    assert summary.failed == 0, summary.payload()


def test_bao_ra_gio_event_thuc_su_ban_de_tester_tu_doi_chieu():
    results, _ = _cham(LOG_BAN_TRUOC_MOC)
    muc = _tim(results, "daily_checkin_screen_view")
    assert "16:54:10.100" in muc.actual, muc.actual


def test_event_dung_buoc_van_pass_binh_thuong():
    results, _ = _cham(LOG_BAN_TRUOC_MOC)
    assert _tim(results, "daily_checkin_button_clicked").verdict is Verdict.PASS


def test_app_khong_ban_lan_nao_thi_VAN_la_fail():
    """Noi long o tren khong duoc lam mat kha nang bat thieu event that."""
    results, summary = _cham(LOG_KHONG_BAN)
    muc = _tim(results, "daily_checkin_screen_view")
    assert muc.verdict is Verdict.FAIL_MISSING, muc.message
    assert summary.failed == 1, summary.payload()


def test_khong_truyen_event_ca_phien_thi_van_la_fail_nhu_truoc():
    """Chan hoi quy nguoc: neu route quen truyen `session_events` thi tool tro
    ve dung hanh vi cu (bao thieu oan). Test nay giu cho loi do khong am tham -
    no ghi lai rang chinh THAM SO DO la thu quyet dinh verdict."""
    spec = parse_paste(SPEC)
    events, markers = parse_log(LOG_BAN_TRUOC_MOC)
    results, _ = event_check_runner.run(spec, cut(events, markers), CONFIG)
    assert _tim(results, "daily_checkin_screen_view").verdict is Verdict.FAIL_MISSING
