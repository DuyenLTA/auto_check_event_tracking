"""Ghi chu triage: chi gan duoc vao dong dang FAIL, va khong duoc cat im lang.

Ghi chu nay do AGENT sinh ra, tuc la do suy luan chu khong phai do do duoc.
Nen tang nhan phai kho tinh: mot ghi chu gan nham cho hoac gan vao luot khac
la mot nguon sai lech MOI, te hon la khong co ghi chu nao.
"""

from __future__ import annotations

import pytest

from usv.check_models import CheckResult, Verdict
from usv.event_triage import KET_LUAN, TriageError, doc

FAILS = {"daily_checkin_screen_view", "rating_star_clicked.star_value"}


def _note(**doi):
    goc = {"element": "daily_checkin_screen_view", "ket_luan": "app_doi_ten",
           "ly_do": "App có bắn daily_checkin_shown cùng thời điểm."}
    return {**goc, **doi}


def _doc(notes, **doi):
    payload = {"notes": notes, **doi}
    return doc(payload, fail_elements=FAILS, generated_at="2026-09-11 09:00")


# --- rang buoc 1: chi gan vao dong dang FAIL ---

def test_gan_vao_dong_dang_fail_thi_duoc():
    batch = _doc([_note()])
    assert batch.cho("daily_checkin_screen_view").ket_luan == "app_doi_ten"


def test_gan_vao_dong_KHONG_fail_thi_tu_choi():
    """Gan ket luan vao dong dang PASS lam nguoi doc tuong dong do cung loi."""
    with pytest.raises(TriageError, match="không nằm trong danh sách FAIL"):
        _doc([_note(element="daily_checkin_button_clicked")])


def test_gan_hai_ghi_chu_cho_cung_mot_dong_thi_tu_choi():
    """Hai ket luan trai nguoc cho mot dong thi in ra cai nao cung sai."""
    with pytest.raises(TriageError, match="hai ghi chú"):
        _doc([_note(), _note(ket_luan="spec_cu")])


# --- rang buoc: ket luan trong bo dong ---

def test_ket_luan_ngoai_bon_gia_tri_thi_tu_choi():
    with pytest.raises(TriageError, match="không hợp lệ"):
        _doc([_note(ket_luan="chac_la_app_sai")])


@pytest.mark.parametrize("ma", sorted(KET_LUAN))
def test_bon_ket_luan_deu_co_nhan_tieng_viet(ma: str):
    assert KET_LUAN[ma] and KET_LUAN[ma] != ma


def test_thieu_ly_do_thi_tu_choi():
    """Khong co ly do thi nguoi doc khong kiem lai duoc, chi con biet tin."""
    with pytest.raises(TriageError, match="thiếu ly_do"):
        _doc([_note(ly_do="   ")])


# --- rang buoc 3: bo sot phai hien ra ---

def test_triage_thieu_mot_dong_thi_tu_dem_la_bo_sot():
    """Khong khai bo_sot thi phai TU TINH, khong duoc mac dinh 0.

    Mac dinh 0 se bao 'da soi het' cho mot lan triage lam do dang.
    """
    batch = _doc([_note()])
    assert batch.bo_sot == 1, "còn 1 dòng FAIL chưa có ghi chú"


def test_triage_du_ca_hai_dong_thi_khong_bo_sot():
    batch = _doc([_note(),
                  _note(element="rating_star_clicked.star_value",
                        ket_luan="spec_cu", ly_do="Spec còn khai giá trị cũ.")])
    assert batch.bo_sot == 0


def test_khai_bo_sot_tay_thi_ton_trong():
    """Agent cat bot vi qua nhieu loi -> tu khai so that."""
    assert _doc([_note()], bo_sot=12).bo_sot == 12


def test_bo_sot_am_thi_tu_choi():
    with pytest.raises(TriageError, match="không âm"):
        _doc([_note()], bo_sot=-1)


# --- phieu phan bien ---

def test_phieu_in_ra_de_biet_muc_chac_chan():
    batch = _doc([_note(dong_y=2, tong=3)])
    assert batch.cho("daily_checkin_screen_view").phieu == "2/3 agent đồng ý"


def test_khong_co_phieu_thi_khong_in_gi():
    assert _doc([_note()]).cho("daily_checkin_screen_view").phieu == ""


def test_dong_y_nhieu_hon_tong_thi_tu_choi():
    with pytest.raises(TriageError, match="lớn hơn"):
        _doc([_note(dong_y=5, tong=3)])


# --- hien trong report ---

def _run_gia(triage):
    """Mot luot cham nho: 1 FAIL + 1 PASS, de xem ghi chu rot dung cho."""
    from usv.check_models import Summary
    from usv.event_spec_parse import parse_paste
    from usv.report_event_html import build

    tsv = "\t".join(["Event_Name", "Params", "Value Type"]) + "\n" \
        + "daily_checkin_screen_view\t\t\n" \
        + "daily_checkin_button_clicked\t\t\n"
    spec = parse_paste(tsv)
    assert spec.errors == (), spec.errors
    results = [
        CheckResult(element="daily_checkin_screen_view", check="event_presence",
                    verdict=Verdict.FAIL_MISSING, actual="không bắn"),
        CheckResult(element="daily_checkin_button_clicked", check="event_presence",
                    verdict=Verdict.PASS, actual="bắn 1 lần: 09-11 09:00:00.000"),
    ]
    summary = Summary()
    for r in results:
        summary.add(r)
    return build(spec, results, summary, package="com.x", triage=triage)


def test_ghi_chu_hien_duoi_dong_fail():
    batch = doc({"notes": [_note()], "bo_sot": 0},
                fail_elements={"daily_checkin_screen_view"},
                generated_at="2026-09-11 09:00")
    html = _run_gia(batch)
    assert "Nhiều khả năng: App đổi tên event" in html
    assert "daily_checkin_shown" in html, "bằng chứng/lý do phải in ra"


def test_khong_co_triage_thi_report_y_nhu_cu():
    assert "Nhiều khả năng" not in _run_gia(None)


def test_bo_sot_phai_hien_thanh_canh_bao_tren_dau_report():
    batch = doc({"notes": [], "bo_sot": 4},
                fail_elements={"daily_checkin_screen_view"},
                generated_at="2026-09-11 09:00")
    html = _run_gia(batch)
    assert "4 lỗi chưa được soi" in html, (
        "cắt bớt im lặng thì báo cáo trông như đã soi hết")


def test_khong_bo_sot_thi_khong_in_canh_bao():
    batch = doc({"notes": [_note()], "bo_sot": 0},
                fail_elements={"daily_checkin_screen_view"},
                generated_at="2026-09-11 09:00")
    assert "chưa được soi" not in _run_gia(batch)


def test_tang_RENDER_cung_chan_ghi_chu_tren_dong_khong_fail():
    """Hai lop chan doc lap, khong phai mot.

    Lop mot la `doc()` - no tu choi ghi chu tro vao dong khong FAIL. Lop hai
    nam o cho ve bang. Test nay dung thang TriageBatch, KHONG di qua `doc()`,
    de lop hai bi kiem that su: mot batch dung sai (do sua tay, do doc tu file
    cu, do goi truc tiep tu code khac) van khong duoc phep dan ket luan vao
    mot dong dang PASS.
    """
    from usv.event_triage import TriageBatch, TriageNote

    xau = TriageNote(element="daily_checkin_button_clicked",
                     ket_luan="app_thieu", ly_do="Ghi chú đặt nhầm chỗ.")
    html = _run_gia(TriageBatch(notes={xau.element: xau}))
    assert "Nhiều khả năng" not in html, (
        "dòng đang PASS mà hiện ghi chú thì người đọc tưởng nó cũng có vấn đề")
