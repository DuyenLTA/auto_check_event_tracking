"""Xuat ket qua ra XLSX de nop bao cao. Dung openpyxl.

Hai sheet:
  "Kết quả"  - moi dong mot ket luan, loc/sort duoc bang Excel
  "Tổng quan" - so lieu + thong tin phien, de nguoi doc biet report nay cua
                man nao, may nao, luc nao

Cot `Lệch` giu nguyen dang chu ("lech +4dp (design 60, app 64)") thay vi tach so:
nguoi nhan report thuong copy nguyen dong vao ticket, doc duoc quan trong hon
tinh toan duoc.
"""

from __future__ import annotations

import io

from .check_models import CheckResult, Summary, Verdict

SHEET_RESULTS = "Kết quả"
SHEET_SUMMARY = "Tổng quan"

_HEADERS = (
    ("Trang thai", 16),
    ("Kiểm tra", 12),
    ("Element", 34),
    ("Thiết kế", 22),
    ("App", 22),
    ("Lệch", 34),
    ("Giải thích", 62),
    ("Node trên app", 24),
    ("Độ tin cậy khớp", 15),
)

# Mau nen theo trang thai. Dung ARGB, khong co dau '#'.
_FILL = {
    "fail": "FBEEEC",
    "warn": "FBF6E9",
    "pass": "FFFFFF",
    "mute": "F4F5F7",
}


def _tone(verdict: Verdict) -> str:
    if verdict is Verdict.PASS:
        return "pass"
    if verdict is Verdict.NOT_VERIFIABLE:
        return "warn"
    # NOT_TESTED di cung nhom nay: chua do gi ca thi khong duoc to do nhu
    # loi that. Xem check_models.Summary.add.
    if verdict in (Verdict.EXTRA, Verdict.NOT_TESTED):
        return "mute"
    return "fail"


def build(
    results: list[CheckResult],
    summary: Summary,
    *,
    screen: str = "",
    package: str = "",
    metrics_label: str = "",
    design_title: str = "",
    generated_at: str = "",
    warnings: list[str] | None = None,
) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    book = Workbook()
    sheet = book.active
    sheet.title = SHEET_RESULTS

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="151A21")
    for index, (label, width) in enumerate(_HEADERS, start=1):
        cell = sheet.cell(row=1, column=index, value=label)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(vertical="center")
        sheet.column_dimensions[get_column_letter(index)].width = width
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = f"A1:{get_column_letter(len(_HEADERS))}{len(results) + 1}"

    wrap = Alignment(vertical="top", wrap_text=True)
    for row_index, item in enumerate(results, start=2):
        values = (
            str(item.verdict), item.check, item.element, item.expected, item.actual,
            item.delta, item.message, item.device_label,
            f"t{item.tier}/{item.confidence:.2f}" if item.tier >= 0 else "",
        )
        fill = PatternFill("solid", fgColor=_FILL[_tone(item.verdict)])
        for col_index, value in enumerate(values, start=1):
            cell = sheet.cell(row=row_index, column=col_index, value=value)
            cell.alignment = wrap
            cell.fill = fill

    _write_summary(book, summary, screen=screen, package=package,
                   metrics_label=metrics_label, design_title=design_title,
                   generated_at=generated_at, warnings=warnings or [])

    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()


def _write_summary(book, summary: Summary, **info) -> None:
    from openpyxl.styles import Alignment, Font

    sheet = book.create_sheet(SHEET_SUMMARY)
    sheet.column_dimensions["A"].width = 26
    sheet.column_dimensions["B"].width = 74
    bold = Font(bold=True)

    rows: list[tuple[str, object]] = [
        ("Màn hình", info.get("screen", "")),
        ("Thiết kế", info.get("design_title", "")),
        ("App", info.get("package", "")),
        ("May", info.get("metrics_label", "")),
        ("Tạo lúc", info.get("generated_at", "")),
        ("", ""),
        ("Lệch thiết kế", summary.failed),
        ("Khớp", summary.passed),
        ("Chưa kết luận được", summary.not_verifiable),
        ("Không khớp được", summary.unmatched),
        ("App có thêm", summary.extra),
        ("Tỉ lệ khớp", f"{summary.pass_ratio:.0%}"),
        ("", ""),
        ("LƯU Ý", "'Không khớp được' KHONG phai loi cua app - do la gioi han cua "
                  "công cụ khi app không gắn resource-id/chữ. Không tính vào số lệch."),
    ]
    for label, value in rows:
        if not label and not value:
            sheet.append([])
            continue
        sheet.append([label, value])
        sheet.cell(row=sheet.max_row, column=1).font = bold
        sheet.cell(row=sheet.max_row, column=2).alignment = Alignment(
            wrap_text=True, vertical="top")

    warnings = info.get("warnings") or []
    if warnings:
        sheet.append([])
        sheet.append(["CẢNH BÁO", ""])
        sheet.cell(row=sheet.max_row, column=1).font = bold
        for warning in warnings:
            sheet.append(["", warning])
            sheet.cell(row=sheet.max_row, column=2).alignment = Alignment(
                wrap_text=True, vertical="top")
