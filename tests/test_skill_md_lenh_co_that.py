"""Moi lenh viet trong SKILL.md / README.md phai CHAY DUOC that.

Tai lieu sai la bug: Claude doc SKILL.md roi go y nguyen, nen mot cai co doi ten
ma tai lieu con ghi ten cu thi lenh no ngay tren may user, giua luc dang cham.

Cach kiem: dua nguyen dong lenh qua DUNG parser cua lenh do. Go sai ten co, sai
ten lenh con, thieu tham so bat buoc - deu lo ra o day chu khong lo tren may
user.
"""

from __future__ import annotations

import contextlib
import io
import re
import shlex
from pathlib import Path

import pytest

from usv import cli_main, cli_record

ROOT = Path(__file__).resolve().parent.parent
TAI_LIEU = {"SKILL.md": (ROOT / "SKILL.md").read_text(encoding="utf-8"),
            "README.md": (ROOT / "README.md").read_text(encoding="utf-8")}

# Lenh cua tool o dau dong trong khoi code (bo tien to shell `$` neu co).
_LENH = re.compile(r"^\s*(?:\$\s*)?((?:usv-check|usv-record|usv-artifact)\b.*)$", re.M)
# Cho trong tai lieu de nguoi dien: <link Confluence>, <package>...
_CHO_TRONG = re.compile(r"<[^>]+>")

PARSER = {"usv-check": cli_main.build_parser, "usv-record": cli_record.build_parser}


def _lenh_trong_tai_lieu():
    for ten_file, noi_dung in TAI_LIEU.items():
        for dong in _LENH.findall(noi_dung):
            yield ten_file, dong.strip()


DONG_LENH = list(_lenh_trong_tai_lieu())


@pytest.mark.parametrize("ten_file, dong", DONG_LENH)
def test_lenh_trong_tai_lieu_parse_duoc(ten_file, dong):
    phan = shlex.split(_CHO_TRONG.sub("cho-trong", dong))
    ten = phan[0]
    if ten not in PARSER:          # usv-artifact dung parser cuc bo, xem test duoi
        return
    with contextlib.redirect_stderr(io.StringIO()) as loi:
        try:
            PARSER[ten]().parse_args(phan[1:])
        except SystemExit:
            pytest.fail(f"{ten_file}: `{dong}` không chạy được — {loi.getvalue()}")


def test_co_lenh_de_kiem():
    """Regex hong ma test van xanh thi khong giu duoc gi."""
    assert len(DONG_LENH) >= 10, DONG_LENH


def test_usv_artifact_trong_tai_lieu_parse_duoc():
    from usv import cli_artifact

    for ten_file, dong in DONG_LENH:
        if not dong.startswith("usv-artifact"):
            continue
        phan = shlex.split(_CHO_TRONG.sub("cho-trong", dong))
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()) as loi:
            try:
                cli_artifact.main([*phan[1:], "--out", str(ROOT / "out")])
            except SystemExit:
                pytest.fail(f"{ten_file}: `{dong}` — {loi.getvalue()}")


def test_tai_lieu_khong_con_noi_ve_web_ui():
    """Web UI da bo. Con huong dan mo http://127.0.0.1:8000 la chi nguoi ta vao
    mot cai khong con ton tai."""
    for ten_file, noi_dung in TAI_LIEU.items():
        assert "127.0.0.1:8000" not in noi_dung, ten_file
        assert "start.sh" not in noi_dung, ten_file


def test_tai_lieu_neu_du_hai_lenh_chinh():
    for ten_file, noi_dung in TAI_LIEU.items():
        assert "usv-check" in noi_dung, ten_file
        assert "usv-record" in noi_dung, ten_file


def test_entry_point_khai_trong_pyproject_tro_dung_ham():
    raw = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'usv-check = "usv.cli_main:main"' in raw
    assert 'usv-record = "usv.cli_record:main"' in raw
    assert 'usv-artifact = "usv.cli_artifact:main"' in raw
