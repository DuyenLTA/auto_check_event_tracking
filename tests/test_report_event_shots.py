"""Nhung anh vao report: mo bang browser la thay, khong can file kem."""

from __future__ import annotations

from usv.flow_screenshots import Shot
from usv.report_event_shots import build_shots

PNG = b"\x89PNG\r\n\x1a\n" + b"gia-lap"


def test_anh_nhung_thang_vao_HTML_khong_can_file_kem():
    html = build_shots({"case A": [Shot(moment="sau bước cuối", png=PNG)]})
    assert "data:image/png;base64," in html
    assert "case A" in html
    assert "sau bước cuối" in html


def test_khong_co_anh_thi_khong_de_lai_khoi_rong():
    assert build_shots({}) == ""


def test_case_khong_co_anh_bi_bo_qua_khong_vo_layout():
    html = build_shots({"case A": [], "case B": [Shot(moment="sau", png=PNG)]})
    assert "case A" not in html
    assert "case B" in html


def test_noi_ro_anh_la_bang_chung_NGU_CANH_khong_phai_thoi_diem():
    """Event ban bat dong bo: anh chup sau step cuoi co the som hon luc event
    that su ban. De nguoi doc tuong anh la bang chung thoi diem la sai."""
    html = build_shots({"case A": [Shot(moment="sau", png=PNG)]})
    assert "ngữ cảnh" in html


def test_anh_hong_khong_lam_vo_report():
    html = build_shots({"case A": [Shot(moment="sau", png=b"")]})
    assert "case A" not in html
