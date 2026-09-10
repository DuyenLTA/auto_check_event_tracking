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
