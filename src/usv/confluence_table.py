"""Doc bang HTML cua Confluence thanh LUOI chu nhat.

Vi sao phai co module nay thay vi tach chuoi: bang that dung `rowspan`, nen
hang thu hai cua mot event chi co 2 the <td> trong khi bang rong 8 cot - sau o
kia bi o rowspan phia tren chiem cho. Dem o theo tung dong se ra "2 cot, can 8"
va bao loi oan tren mot bang hoan toan hop le.

Do tren trang that (SDK Widget V 1.0.0):
  - header nam trong <td><strong>, KHONG phai <th> - dung doi hoi <th>
  - o chua <p><span>..</span></p> long nhau, co ca &nbsp; va &quot;
  - bang long trong bang (muc Requirements) -> phai theo doi do sau
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

_CELL = {"td", "th"}
_SPACES = re.compile(r"\s+")

# Cot toi thieu de nhan ra "day la bang spec event", khong phai bang khac tren
# cung trang (Requirements, List Remote Key...).
# Da chuan hoa: bo gach duoi/khoang trang, ha hoa-thuong.
_MARKERS = ("eventname", "params")


def _clean(text: str) -> str:
    """Gom khoang trang, bo &nbsp; thua. Giu nguyen dau phay - danh sach gia
    tri cho phep duoc tach bang dau phay o tang tren."""
    return _SPACES.sub(" ", text.replace("\xa0", " ")).strip()


def _span(value: str | None) -> int:
    try:
        number = int((value or "1").strip())
    except ValueError:
        return 1
    return number if number > 0 else 1


class _Tables(HTMLParser):
    """Gom tung bang thanh danh sach o kem rowspan/colspan.

    Bang long nhau: moi khi gap <table> thi day mot bang moi vao ngan xep, o
    van duoc gan cho bang tren cung. Nho vay bang ngoai khong nuot o cua bang
    trong.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.done: list[list[list[tuple[str, int, int]]]] = []
        self._stack: list[list[list[tuple[str, int, int]]]] = []
        self._cell: list[str] | None = None
        self._span: tuple[int, int] = (1, 1)

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._stack.append([])
            return
        if not self._stack:
            return
        if tag == "tr":
            self._stack[-1].append([])
        elif tag in _CELL:
            self._flush()
            attr = dict(attrs)
            self._span = (_span(attr.get("rowspan")), _span(attr.get("colspan")))
            self._cell = []
        elif tag == "br" and self._cell is not None:
            self._cell.append(" ")

    def handle_endtag(self, tag):
        if tag in _CELL:
            self._flush()
        elif tag == "table" and self._stack:
            self._flush()
            self.done.append(self._stack.pop())

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)

    def _flush(self) -> None:
        if self._cell is None or not self._stack:
            return
        rows = self._stack[-1]
        if not rows:                     # <td> ngoai <tr> - markup hong
            rows.append([])
        rows[-1].append((_clean("".join(self._cell)), *self._span))
        self._cell = None
        self._span = (1, 1)


def _grid(rows: list[list[tuple[str, int, int]]]) -> list[list[str]]:
    """Trai rowspan/colspan ra thanh luoi chu nhat.

    O NOI TIEP CUA rowspan DE RONG, khong lap lai chu. Trong bang spec, o gop
    doc mang nghia "van la event nay" - dung y het o Event_Name de trong o ban
    TSV. Lap lai chu thi mot event bi dem thanh hai event trung ten.

    `carry[cot] = con lai bao nhieu hang` - o rowspan phu xuong cac hang duoi,
    va cac hang do khong khai lai o nao cho nhung cot ay.
    """
    carry: dict[int, int] = {}
    out: list[list[str]] = []
    for row in rows:
        line: list[str] = []
        pos = 0
        queue = list(row)
        while queue or any(left > 0 for left in carry.values()):
            left = carry.get(pos, 0)
            if left > 0:
                line.append("")            # o noi tiep - xem docstring
                carry[pos] = left - 1
                pos += 1
                continue
            if not queue:
                break
            text, rowspan, colspan = queue.pop(0)
            for _ in range(colspan):
                line.append(text)
                if rowspan > 1:
                    carry[pos] = rowspan - 1
                pos += 1
        out.append(line)
    width = max((len(r) for r in out), default=0)
    return [r + [""] * (width - len(r)) for r in out]


def tables_of(page_html: str) -> list[list[list[str]]]:
    """Moi bang tren trang, da trai thanh luoi chu nhat."""
    parser = _Tables()
    parser.feed(page_html)
    parser.close()
    return [_grid(rows) for rows in parser.done if rows]


def find_spec_table(page_html: str) -> list[list[str]] | None:
    """Bang spec event tren trang, hoac None neu trang khong co bang nao khop.

    Nhan dien bang CHU O HEADER chu khong theo thu tu: mot trang that con co
    bang Requirements va List Remote Key, lay nham bang la cham sai toan bo.
    """
    for grid in tables_of(page_html):
        for row in grid[:2]:      # header co the o hang 1 hoac hang 2
            keys = {"".join(ch for ch in cell.casefold() if ch.isalnum())
                    for cell in row}
            if all(marker in keys for marker in _MARKERS):
                return grid
    return None
