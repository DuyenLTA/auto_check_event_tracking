"""Chot chan cho khung case agent sinh ra tu spec.

Agent doc van xuoi thi phai suy luan, va suy luan thi sai duoc. Cac test duoi
day kiem dung phan DOI CHIEU - phan khong can suy luan gi, chi can so voi bang
spec. Khong test chat luong suy luan cua agent o day: cai do khong lap lai duoc.
"""

from __future__ import annotations

from pathlib import Path

from usv import spec_case_rules as rules
from usv import spec_case_skeleton as skeleton
from usv.event_spec_parse import parse_paste
from usv.spec_prose_sections import sections

SPEC = parse_paste(
    (Path(__file__).parent / "fixtures" / "event-spec-rating.tsv")
    .read_text(encoding="utf-8"))


def _case(**over) -> dict:
    base = {"id": "c1", "event": "rating_placement_viewed",
            "expect_params": {"placement_name": "home"}, "reset": "relaunch"}
    base.update(over)
    return base


def test_event_khong_co_trong_spec_bi_tu_choi():
    cases, errors = skeleton.parse([_case(event="rating_popup_closed",
                                          expect_params={})])
    assert not errors
    found = rules.validate(cases, SPEC)
    assert found and "rating_popup_closed" in found[0]


def test_gia_tri_ngoai_danh_sach_spec_bi_tu_choi():
    cases, _ = skeleton.parse([_case(expect_params={"placement_name": "splash"})])
    found = rules.validate(cases, SPEC)
    assert found and "splash" in found[0]


def test_param_event_khong_khai_bi_tu_choi():
    cases, _ = skeleton.parse([_case(expect_params={"star_value": "5"})])
    found = rules.validate(cases, SPEC)
    assert found and "star_value" in found[0]


def test_case_dot_popup_ma_chi_relaunch_thi_bi_tu_choi():
    """Spec: 'Khong hien pop-up rating khi user da bam rate'. Relaunch khong go
    duoc trang thai do, nen case sau se khong do duoc gi ma van im lang."""
    cases, _ = skeleton.parse([
        _case(event="rating_star_clicked",
              expect_params={"star_value": "5", "placement_name": "home"},
              burns_popup=True, reset="relaunch")])
    found = rules.validate(cases, SPEC)
    assert found and "pm_clear" in found[0]


def test_case_dot_popup_ma_pm_clear_thi_qua():
    cases, _ = skeleton.parse([
        _case(event="rating_star_clicked",
              expect_params={"star_value": "5", "placement_name": "home"},
              burns_popup=True, reset="pm_clear")])
    assert rules.validate(cases, SPEC) == ()


def test_reset_la_khong_bi_tu_choi_kem_danh_sach_hop_le():
    _, errors = skeleton.parse([_case(reset="wipe")])
    assert errors and "pm_clear" in errors[0]


def test_id_trung_bi_bao():
    _, errors = skeleton.parse([_case(), _case()])
    assert errors and "trùng" in errors[0]


def test_bo_sot_liet_ke_gia_tri_chua_case_nao_phu():
    """Event DA co case thi liet ke tung gia tri con thieu; event chua co case
    nao thi bao MOT dong - liet ke ca 9 gia tri cua no chi lam nhoe cai chinh."""
    cases, _ = skeleton.parse([_case()])
    gaps = rules.missed(cases, SPEC)
    assert "rating_placement_viewed.placement_name=result" in gaps
    assert "rating_placement_viewed.placement_name=home" not in gaps
    assert "rating_star_clicked (chưa có case nào)" in gaps
    assert not any(g.startswith("rating_star_clicked.") for g in gaps)


def test_phu_het_thi_bo_sot_rong():
    raw = [_case(id=f"v-{v}", expect_params={"placement_name": v})
           for v in ("result", "exit_click", "app_shortcut", "home")]
    raw += [_case(id=f"s-{n}", event="rating_star_clicked",
                  expect_params={"star_value": str(n), "placement_name": p})
            for n, p in zip(range(1, 6),
                            ("result", "exit_click", "app_shortcut", "home",
                             "home"))]
    cases, _ = skeleton.parse(raw)
    assert rules.missed(cases, SPEC) == ()


def test_sections_cat_trang_theo_heading():
    html = ("<p>mo dau</p><h1>I. Scope</h1><p>pham vi</p>"
            "<h1>III. Requirements</h1><ul><li>dieu kien A</li></ul>")
    got = dict(sections(html))
    assert got["I. Scope"] == "pham vi"
    assert "dieu kien A" in got["III. Requirements"]


# --- remote config la TIEN DE cua case, khong phai thu de kiem ---------------
# Man rating o luong exit chi hien khi vi tri `home` da bi go khoi
# `show_rating_placement`: con `home` thi popup tieu het luot cua session ngay
# o man home, bam back khong ra gi.

KEYS = ("show_rating_placement", "show_rating_button_x", "rating_threshold",
        "feedback_email")


def test_remote_key_khong_co_trong_trang_bi_tu_choi():
    cases, _ = skeleton.parse([_case(remote_config={"show_rating_home": "off"})])
    found = rules.validate(cases, SPEC, KEYS)
    assert found and "show_rating_home" in found[0]


def test_doi_remote_config_ma_khong_mo_lai_app_bi_tu_choi():
    cases, _ = skeleton.parse([
        _case(expect_params={"placement_name": "exit_click"},
              remote_config={"show_rating_placement": "result,exit_click,app_shortcut"},
              reset="none")])
    found = rules.validate(cases, SPEC, KEYS)
    assert found and "khởi động" in found[0]


def test_doi_remote_config_kem_relaunch_thi_qua():
    cases, _ = skeleton.parse([
        _case(expect_params={"placement_name": "exit_click"},
              remote_config={"show_rating_placement": "result,exit_click,app_shortcut"},
              reset="relaunch")])
    assert rules.validate(cases, SPEC, KEYS) == ()


def test_khong_khai_remote_keys_thi_bo_qua_khau_kiem_ten():
    """Trang khong co bang Remote Key thi khong co gi de so - bat bua se bao
    loi tren moi case."""
    cases, _ = skeleton.parse([_case(remote_config={"key_la": "1"})])
    assert rules.validate(cases, SPEC) == ()


def test_remote_keys_doc_bang_theo_ten_cot():
    html = ("<table><tr><th>Requirement</th><th>Mô tả</th></tr>"
            "<tr><td>abc</td><td>xyz</td></tr></table>"
            "<table><tr><th>Remote Key</th><th>Data Type</th></tr>"
            "<tr><td>Remote Key Bật/Tắt Ads</td><td></td></tr>"
            "<tr><td>show_rating_placement</td><td>String</td></tr></table>")
    from usv.spec_prose_sections import remote_keys
    assert remote_keys(html) == ("show_rating_placement",)


# --- chuoi case noi tiep nhau -----------------------------------------------
# `reset: none` nghia la chay tiep trang thai case truoc de lai. Neu thu tu do
# nam o thu tu dong trong file thi doi cho hai dong la hong im lang: case chay
# tren mot man hinh khac roi bao "Chua test" chu khong bao loi.

def test_reset_none_ma_khong_khai_sau_thi_bi_bao():
    cases, _ = skeleton.parse([_case(reset="none")])
    found = rules.chain(cases)
    assert found and "`sau`" in found[0]


def test_sau_tro_toi_id_khong_co_thi_bi_bao():
    cases, _ = skeleton.parse([_case(reset="none", sau="khong-ton-tai")])
    found = rules.chain(cases)
    assert found and "khong-ton-tai" in found[0]


def test_sau_tro_vao_chinh_no_thi_bi_bao():
    cases, _ = skeleton.parse([_case(id="a", reset="none", sau="a")])
    found = rules.chain(cases)
    assert found and "chính nó" in found[0]


def test_vong_tron_bi_bao():
    cases, _ = skeleton.parse([_case(id="a", reset="none", sau="b"),
                               _case(id="b", reset="none", sau="a")])
    found = rules.chain(cases)
    assert any("vòng tròn" in line for line in found)


def test_chuoi_hop_le_thi_khong_bao_gi():
    cases, _ = skeleton.parse([_case(id="a"),
                               _case(id="b", reset="none", sau="a")])
    assert rules.chain(cases) == ()


def test_thu_tu_chay_suy_ra_tu_sau_chu_khong_tu_thu_tu_dong():
    """Dong con dat truoc dong cha van phai chay sau."""
    cases, _ = skeleton.parse([_case(id="b", reset="none", sau="a"),
                               _case(id="a")])
    assert [c.id for c in rules.order(cases)] == ["a", "b"]


def test_case_doc_lap_giu_nguyen_thu_tu_xuat_hien():
    cases, _ = skeleton.parse([_case(id="x"), _case(id="y"), _case(id="z")])
    assert [c.id for c in rules.order(cases)] == ["x", "y", "z"]


def test_case_doc_lap_khong_bi_nhac_len_chen_giua_day():
    """Xep theo tang thi moi case goc bi don len dau, chen vao giua mot day
    dang do - day van chay duoc nhung doc khong ra trinh tu nao."""
    cases, _ = skeleton.parse([
        _case(id="a"),
        _case(id="a2", reset="none", sau="a"),
        _case(id="b"),                       # doc lap, dung o cuoi file
    ])
    assert [c.id for c in rules.order(cases)] == ["a", "a2", "b"]


def test_event_khong_co_param_van_phai_co_case():
    """Bang spec ma moi event deu khong co param (daily checkin, widget): khong
    co bo ba (event, param, gia tri) nao de thieu, nen dem bo ba khong thi mot
    danh sach case RONG cung bao 'khong bo sot' - pass gia."""
    sheet = parse_paste(
        "Screen Name\tEvent_Name\tTriggered\tParams\tParam Description\t"
        "Value Type\tValue\tValue Description\n"
        "\tdaily_checkin_screen_view\tKhi màn daily checkin hiển thị\t\t\t\t\t\n")
    assert [e.name for e in sheet.events] == ["daily_checkin_screen_view"]
    assert rules.missed((), sheet) == ("daily_checkin_screen_view (chưa có case nào)",)
    cases, _ = skeleton.parse([_case(event="daily_checkin_screen_view",
                                     expect_params={})])
    assert rules.missed(cases, sheet) == ()


def test_khai_lai_gia_tri_mac_dinh_bi_tu_choi():
    """Trang khai Default Value, nen day la thu do duoc chu khong phai suy doan:
    khai lai mac dinh khong doi gi, chi bien case chay duoc thanh case doi sua
    Remote Config - tren build khong debuggable la thanh BLOCKED oan."""
    cases, _ = skeleton.parse([_case(remote_config={"show_checkin_screen": "ON"})])
    found = rules.validate(cases, SPEC, ("show_checkin_screen",),
                           {"show_checkin_screen": "ON"})
    assert found and "mặc định" in found[0]


def test_khai_khac_mac_dinh_thi_qua():
    cases, _ = skeleton.parse([_case(remote_config={"show_checkin_screen": "OFF"})])
    assert rules.validate(cases, SPEC, ("show_checkin_screen",),
                          {"show_checkin_screen": "ON"}) == ()
