"""Boc phan VAN XUOI cua trang spec ra cho agent doc.

`event_spec_confluence.parse_page` chi lay BANG event tracking - dung cho viec
cham. Nhung dieu kien de mot event ban ra ("tu session 2 tro di", "1 lan/1
session", "khong hien lai khi user da bam rate") nam o muc Requirements duoi
dang van xuoi, va o bang Remote Key. Bo qua chung thi case sinh ra thieu tien
de, va luot chay bao `not_tested` hang loat ma khong ai biet vi sao.

Tang nay KHONG suy luan gi - chi cat trang thanh tung muc va do ra text. Viec
doc van xuoi thanh dieu kien la viec cua agent; viec lay ve va cat muc la do
duoc nen de Python lam, dung de agent tu goi HTTP.
"""

from __future__ import annotations

import html as html_lib
import re

from . import confluence_client, confluence_table

# Heading nao cung duoc, khong rieng h1: trang khac nhau danh so muc khac nhau.
_HEADING = re.compile(r"<h([1-6])[^>]*>(.*?)</h\1>", re.S)
_BREAKS = re.compile(r"</(p|li|tr|div)>|<br\s*/?>", re.I)
_TAGS = re.compile(r"<[^>]+>")
_BLANKS = re.compile(r"\n{3,}")


def _text(fragment: str) -> str:
    """HTML -> text giu xuong dong. Giu dong vi moi gach dau dong la mot y."""
    out = _BREAKS.sub("\n", fragment)
    out = _TAGS.sub("", out)
    out = html_lib.unescape(out)
    out = "\n".join(line.strip() for line in out.splitlines())
    return _BLANKS.sub("\n\n", out).strip()


def sections(page_html: str) -> list[tuple[str, str]]:
    """Cat trang thanh [(tieu de muc, noi dung)] theo thu tu xuat hien.

    Phan dung truoc heading dau tien di vao muc rong "" - thuong la muc luc,
    bo cung duoc nhung khong vut di: co trang de Scope ngay tren cung.
    """
    parts: list[tuple[str, str]] = []
    last_end = 0
    title = ""
    for found in _HEADING.finditer(page_html):
        body = _text(page_html[last_end:found.start()])
        if body or title:
            parts.append((title, body))
        title = _text(found.group(2))
        last_end = found.end()
    parts.append((title, _text(page_html[last_end:])))
    return [(t, b) for t, b in parts if t or b]


def tables_as_tsv(page_html: str) -> list[str]:
    """Moi bang -> mot khoi TSV. Dung luoi cua confluence_table nen o gop
    (rowspan) khong lam lech cot - bay da do duoc, xem docstring module do."""
    blocks = []
    for grid in confluence_table.tables_of(page_html):
        blocks.append("\n".join("\t".join(cell for cell in row) for row in grid))
    return blocks


def remote_keys(page_html: str) -> tuple[str, ...]:
    """Ten cac remote key trang khai, lay tu bang co cot dau la "Remote Key".

    Tim theo TEN COT chu khong theo thu tu bang: mot trang thuong co them bang
    Requirements va bang phan cong nguoi lam, lay nham bang la kiem sai toan bo.
    Cung ly do `confluence_table.find_spec_table` tim bang event theo ten cot.
    """
    for grid in confluence_table.tables_of(page_html):
        if not grid:
            continue
        header = [cell.strip().casefold() for cell in grid[0]]
        if "remote key" not in header:
            continue
        column = header.index("remote key")
        names = []
        for row in grid[1:]:
            if column >= len(row):
                continue
            name = row[column].strip()
            # Bang hay co dong tieu de phu ("Remote Key Bat/Tat Ads") trai dai
            # het hang; dong do khong phai mot key.
            if name and not name.casefold().startswith("remote key"):
                names.append(name)
        return tuple(names)
    return ()


def remote_defaults(page_html: str) -> dict[str, str]:
    """Ten key -> gia tri o cot "Default Value".

    Dung de bat case khai lai chinh gia tri mac dinh: khai nhu vay khong doi gi
    ca, nhung lai bien mot case chay duoc thanh case doi sua Remote Config -
    tren build khong debuggable la thanh BLOCKED ma dang le khong phai.
    """
    for grid in confluence_table.tables_of(page_html):
        if not grid:
            continue
        header = [cell.strip().casefold() for cell in grid[0]]
        if "remote key" not in header or "default value" not in header:
            continue
        name_at, default_at = header.index("remote key"), header.index("default value")
        out: dict[str, str] = {}
        for row in grid[1:]:
            if max(name_at, default_at) >= len(row):
                continue
            name = row[name_at].strip()
            if name and not name.casefold().startswith("remote key"):
                out[name] = row[default_at].strip()
        return out
    return {}


def dump(url: str) -> str:
    """Tai trang roi do ra text: muc van xuoi + bang duoi dang TSV.

    Mot chuoi duy nhat vi ben nhan la prompt cua agent - tra ve cau truc long
    nhau chi de roi noi lai thanh chuoi o dau kia.
    """
    title, page_html = confluence_client.fetch_page(url)
    lines = [f"# {title}", f"# nguon: {url}", ""]
    for heading, body in sections(page_html):
        lines.append(f"## {heading}" if heading else "## (dau trang)")
        if body:
            lines.append(body)
        lines.append("")
    for index, block in enumerate(tables_as_tsv(page_html), start=1):
        lines.append(f"## BANG {index} (TSV)")
        lines.append(block)
        lines.append("")
    return "\n".join(lines)
