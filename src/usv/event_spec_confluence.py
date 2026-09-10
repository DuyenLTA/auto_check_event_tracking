"""Trang Confluence -> SpecSheet.

Chi lam mot viec: tim bang spec tren trang roi giao cho event_spec_parse. Y
nghia cac cot dung chung voi duong dan TSV (parse_rows) - hai ban rieng la mot
ngay hai duong hieu bang khac nhau.
"""

from __future__ import annotations

from .confluence_table import find_spec_table
from .event_spec_models import SpecSheet
from .event_spec_parse import parse_rows


def parse_page(page_html: str) -> SpecSheet:
    grid = find_spec_table(page_html or "")
    if grid is None:
        return SpecSheet(errors=(
            "Trang nay khong co bang nao co ca cot 'Event_Name' va 'Params'. "
            "Kiem lai link co dung trang chua bang event tracking khong - "
            "nhieu trang chi tro sang Google Sheet, cong cu khong doc duoc "
            "Sheet.",))
    # Hang rong hoan toan la o ke bang de trong, khong phai hang du lieu.
    rows = [row for row in grid if any(cell.strip() for cell in row)]
    return parse_rows(rows)
