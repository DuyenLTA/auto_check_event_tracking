"""Moi id JS lay bang $() phai co that trong index.html.

Vi sao can: document.getElementById tra ve `null` khi khong tim thay - khong
nem loi. Go sai mot id thi ca mot nut chet lang, va chi phat hien khi co nguoi
ngoi bam thu. Da mat mot luot test vi mot nut khong phan ung.

Test doc tinh (khong chay browser) nen re, va bat dung loai loi do.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

WEB = Path(__file__).parent.parent / "src" / "usv" / "web"
HTML = (WEB / "index.html").read_text(encoding="utf-8")
JS_FILES = sorted(WEB.glob("*.js"))

_DOLLAR = re.compile(r"\$\(\s*'([^']+)'\s*\)")
_GET_BY_ID = re.compile(r"getElementById\(\s*'([^']+)'\s*\)")


def _ids_in(text: str) -> set[str]:
    return set(_DOLLAR.findall(text)) | set(_GET_BY_ID.findall(text))


@pytest.mark.parametrize("path", JS_FILES, ids=lambda p: p.name)
def test_id_js_dung_deu_co_trong_html(path: Path):
    missing = sorted(i for i in _ids_in(path.read_text(encoding="utf-8"))
                     if f'id="{i}"' not in HTML)
    assert not missing, f"{path.name} goi id khong co trong index.html: {missing}"


def test_test_nay_bat_duoc_id_go_sai():
    """Tu chung minh: id bia ra phai bi bao thieu."""
    assert 'id="khong-ton-tai"' not in HTML


def test_khong_con_dem_buoc_khi_chua_danh_dau_gi():
    """Danh dau la tuy chon. In "0/2 buoc — con 2" ngay tu dau lam nguoi dung
    tuong con viec phai lam, va bam het kich ban roi van thay 0/2 thi tuong
    tool khong ghi nhan gi."""
    js = (WEB / "event-marks.js").read_text(encoding="utf-8")
    assert "if (!total || !hit) return '';" in js, (
        "chua bam moc nao thi markProgress phai tra chuoi rong")
    assert "bước — còn" not in js, "nhan cu ('N/M bước') gay hieu nham"



def test_loi_khi_bam_ghi_hien_o_buoc_ghi():
    """Loi cua /event/record (vd app khong co tren may) phai hien canh nut Ghi.

    Truoc day no bi day vao o loi cua buoc 1: nguoi dung dang o buoc 2, bam
    Ghi khong thay gi phan hoi, con thong bao thi nam tren cao co khi ngoai
    man hinh.
    """
    js = (WEB / "event.js").read_text(encoding="utf-8")
    khoi = js[js.index("ui.btnRecord.addEventListener"):]
    khoi = khoi[:khoi.index("\n});")]
    assert "fail(ui.recordAlert" in khoi
    assert "fail(ui.spec.errors" not in khoi, "loi buoc ghi khong duoc day ve buoc 1"


def test_khong_con_o_tick_chon_cach_mo_app():
    """Bo o tick roi thi khong duoc con dau vet: id mo, tham so gui di, hay
    nhan tren trang. De lai mot nua thi client va server hieu khac nhau."""
    html = (WEB / "index.html").read_text(encoding="utf-8")
    js = (WEB / "event.js").read_text(encoding="utf-8")
    assert 'id="from-launch"' not in html
    assert "fromLaunch" not in js
    assert "from_launch" not in js, "khong duoc gui tham so ma server khong con doc"
