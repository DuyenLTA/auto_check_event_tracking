"""Parse bang spec event dan tu Excel.

Test quan trong nhat: test_ban_bi_gay_dong_bi_TU_CHOI. Spike da chung minh gop
dong theo so cot lam MAT o rong o diem gay -> spec sai ma khong bao gi. Neu test
do xanh bang cach parser "doan lai duoc" thi cung la SAI: yeu cau la TU CHOI.
"""

from __future__ import annotations

from pathlib import Path

from usv.event_spec_parse import parse_paste

FIXTURES = Path(__file__).parent / "fixtures"
GOOD = (FIXTURES / "event-spec-rating.tsv").read_text(encoding="utf-8")
BROKEN = (FIXTURES / "event-spec-broken.tsv").read_text(encoding="utf-8")


def test_spec_that_parse_dung():
    sheet = parse_paste(GOOD)
    assert sheet.errors == ()
    assert sheet.ok is True
    assert [e.name for e in sheet.events] == [
        "rating_placement_viewed", "rating_star_clicked"]


def test_hang_param_tiep_gan_vao_event_phia_tren():
    """Cot Event_Name de trong = param tiep cua event tren no."""
    sheet = parse_paste(GOOD)
    star = sheet.event("rating_star_clicked")
    assert star is not None
    assert star.param_names == {"star_value", "placement_name"}


def test_gia_tri_cho_phep_tach_dung():
    sheet = parse_paste(GOOD)
    viewed = sheet.event("rating_placement_viewed")
    assert viewed.param("placement_name").allowed == (
        "result", "exit_click", "app_shortcut", "home")
    star = sheet.event("rating_star_clicked")
    assert star.param("star_value").allowed == ("1", "2", "3", "4", "5")


def test_kieu_va_screen_va_triggered_doc_duoc():
    sheet = parse_paste(GOOD)
    viewed = sheet.event("rating_placement_viewed")
    assert viewed.screen == "Home"
    assert "rating" in viewed.triggered.lower()
    assert viewed.param("placement_name").wants_string is True
    assert sheet.event("rating_star_clicked").param("star_value").wants_number is True


def test_ban_bi_gay_dong_bi_TU_CHOI():
    """KHONG duoc tu gop. Phai bao loi kem so dong."""
    sheet = parse_paste(BROKEN)
    assert sheet.errors, "ban bi gay dong phai sinh loi"
    assert sheet.ok is False
    joined = " ".join(sheet.errors)
    assert "Dòng 2" in joined, "loi phai chi ro SO DONG de tester sua duoc"


def test_ban_bi_gay_khong_sinh_ra_spec_sai():
    """Do la thiet hai thuc su: parse ra mot spec TRONG NHU DUNG.

    Spike: noi tho lam 'Vi tri man rating xuat hien' + 'rating_star_clicked'
    dinh vao nhau va thanh gia tri cho phep cua placement_name.
    """
    sheet = parse_paste(BROKEN)
    for event in sheet.events:
        for param in event.params:
            for value in param.allowed:
                assert "rating_star_clicked" not in value
                assert "Vị trí" not in value


def test_thieu_cot_bat_buoc_bao_ro():
    text = "Event_Name\tTriggered\n rating_x\tkhi nao\n"
    sheet = parse_paste(text)
    assert sheet.events == ()
    joined = " ".join(sheet.errors)
    assert "Params" in joined and "Value Type" in joined


def test_o_text_trong():
    sheet = parse_paste("")
    assert sheet.ok is False
    assert sheet.errors


def test_chi_co_dong_tieu_de():
    sheet = parse_paste("Event_Name\tParams\tValue Type\n")
    assert sheet.events == ()
    assert sheet.errors


def test_param_mo_coi_khong_co_event_phia_tren():
    text = ("Event_Name\tParams\tValue Type\tValue\n"
            "\tplacement_name\tString\thome\n")
    sheet = parse_paste(text)
    assert any("chưa có event nào" in e for e in sheet.errors)


def test_value_rong_la_free_form():
    text = ("Event_Name\tParams\tValue Type\tValue\n"
            "ump_request_failed\terror_code\tString\t\n")
    sheet = parse_paste(text)
    param = sheet.event("ump_request_failed").param("error_code")
    assert param.allowed == ()
    assert param.free_form is True


def test_ten_cot_bien_the_va_thu_tu_bat_ky():
    """'Event Name' co khoang trang, thu tu cot dao lon."""
    text = ("Value\tvalue type\tPARAMS\tEvent Name\n"
            "home, result\tString\tplacement_name\trating_placement_viewed\n")
    sheet = parse_paste(text)
    assert sheet.errors == ()
    assert sheet.event("rating_placement_viewed").param("placement_name").allowed \
        == ("home", "result")


def test_cot_la_khong_lam_vo_parse():
    text = ("Event_Name\tParams\tValue Type\tValue\tGhi chu cua QA\n"
            "rating_star_clicked\tstar_value\tNumber\t1,2,3\txem lai sau\n")
    sheet = parse_paste(text)
    assert sheet.errors == ()
    assert sheet.event("rating_star_clicked").param("star_value").allowed == ("1", "2", "3")


def test_param_khai_hai_lan_bao_loi():
    text = ("Event_Name\tParams\tValue Type\tValue\n"
            "rating_star_clicked\tstar_value\tNumber\t1,2\n"
            "\tstar_value\tNumber\t3,4\n")
    sheet = parse_paste(text)
    assert any("hai lần" in e for e in sheet.errors)


def test_o_nhieu_dong_boc_nguoc_kep_van_la_MOT_hang():
    """Excel boc nguoc kep quanh o co xuong dong - do la o hop le."""
    text = ('Event_Name\tParams\tValue Type\tValue Description\n'
            'rating_star_clicked\tstar_value\tNumber\t"So sao\nuser da rate"\n')
    sheet = parse_paste(text)
    assert sheet.errors == (), f"khong duoc coi o nhieu dong la hang gay: {sheet.errors}"
    assert sheet.event("rating_star_clicked") is not None


def test_payload_dem_dung():
    sheet = parse_paste(GOOD)
    payload = sheet.payload()
    assert payload["event_count"] == 2
    assert payload["param_count"] == 3
    assert payload["ok"] is True
