"""Gop cac dong giong het nhau trong bang report.

Mot case = mot event, nen cham du nam gia tri `star_value` phai viet nam case.
Moi case lai kiem LAI toan bo param spec khai cho event do (xem vong lap
`for param in event.params` trong checks/event_params.py), nen cot
`placement_name` in lai y het `exit_click` nam lan - lan mat cot `star_value`
la thu that su khac nhau giua nam case do. Do tren app Nexus AI 3.2.0: bang
`rating_star_clicked` co 6 dong `placement_name` deu la `exit_click`.

Gop theo DUNG nhung gi hien ra man: cung event.param, cung "Spec can", cung
"App gui", cung ket luan, cung ghi chu thi moi la mot dong. Lech mot ky tu la
tach dong, nen khong the giau mat mot sai lech dang le phai thay.

Chi gop de HIEN. So "n/m khop" o dau moi muc van dem tung ket qua mot, vi moi
case that su co kiem - gop o day ma tru luon vao tong thi bao cao noi doi ve
khoi luong da chay.
"""

from __future__ import annotations

from .check_models import CheckResult


def gop_dong_trung(rows: list[CheckResult]) -> list[tuple[CheckResult, int]]:
    """[(dong dai dien, so case cho ra dong do)], giu thu tu gap dau tien."""
    thu_tu: list[tuple] = []
    gom: dict[tuple, list[CheckResult]] = {}
    for item in rows:
        # `check` nam trong khoa: dong presence va dong param cua cung mot
        # element khong duoc lan vao nhau.
        khoa = (item.element, item.check, item.verdict,
                item.expected, item.actual, item.delta, item.message)
        if khoa not in gom:
            gom[khoa] = []
            thu_tu.append(khoa)
        gom[khoa].append(item)
    return [(gom[k][0], len(gom[k])) for k in thu_tu]
