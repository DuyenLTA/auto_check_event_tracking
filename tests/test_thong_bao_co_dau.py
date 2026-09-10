"""Moi thong bao cho NGUOI DUNG phai la tieng Viet co dau.

Chu thich trong code thi khong dau (thong nhat voi ca repo, va tranh loi font
o terminal cu). Nhung thong bao thi nguoi dung doc, va "Trang tra ve rong -
co the ban khong co quyen xem" doc len rat kho hieu.

Cach kiem: gom cac chuoi cua tung cho sinh thong bao (raise XxxError(...),
detail=..., message=..., errors.append(...)), roi doi hoi cum do co it nhat
MOT ky tu co dau. Kiem theo cum chu khong theo tung chuoi: mot thong bao dai
co the co dong ky thuat thuan ASCII (vd "export CONFLUENCE_TOKEN=..."), va
dong do khong sai gi.
"""

from __future__ import annotations

import ast
import pathlib
import re

import pytest

SRC = pathlib.Path(__file__).parent.parent / "src" / "usv"
# Tu tieng Viet KHONG DAU hay gap trong thong bao. Doi hoi "co it nhat mot
# dau" thi qua long: mot cau nua dau nua khong van lot - da lot that voi
# "2 cot, can 3. Hang nay co the bi gay...".
# CHI cac tu ma tieng Viet KHONG BAO GIO viet khong dau. Bo "ghi", "hai",
# "thay", "tri", "lan"... - chung von khong dau nen bao oan.
KHONG_DAU = re.compile(
    r"\b(khong|duoc|nguoi|chua|phai|nhung|hang|cot|bang|thieu|loi|hoac"
    r"|may|tren|mot|dan|cham|buoc|nay|voi|xoa|sua|lien|tiep|gay|tat"
    r"|dung|gio|man|hinh|dong|phia|nao|nua|moc|hop le|gio)\b")
# Chuoi qua ngan thi khong phai cau tieng Viet (vd ": ", " - ").
NGAN = 12


def _cum_thong_bao(tree: ast.AST) -> list[tuple[int, str]]:
    """Cac cho sinh thong bao, moi cho gom het chuoi cua no thanh mot cum."""
    ra = []
    for node in ast.walk(tree):
        goc = None
        if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call):
            ten = getattr(node.exc.func, "id", "") or getattr(node.exc.func, "attr", "")
            if ten.endswith("Error") or ten == "HTTPException":
                goc = node.exc
        elif isinstance(node, ast.keyword) and node.arg in ("detail", "message"):
            goc = node.value
        elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
              and node.func.attr == "append"
              and getattr(node.func.value, "id", "") in ("errors", "out")):
            goc = node
        if goc is None:
            continue
        chuoi = [n.value for n in ast.walk(goc)
                 if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        cum = " ".join(chuoi).strip()
        if len(cum) >= NGAN:
            ra.append((getattr(goc, "lineno", 0), cum))
    return ra


FILES = sorted(SRC.rglob("*.py"))


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_thong_bao_co_dau(path: pathlib.Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    thieu = []
    for ln, cum in _cum_thong_bao(tree):
        con = KHONG_DAU.findall(cum.lower())
        if con:
            thieu.append(f"dong {ln}: con {sorted(set(con))} -> {cum[:60]}")
    assert not thieu, path.name + "\n" + "\n".join(thieu)
