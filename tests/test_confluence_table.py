"""Doc bang tu HTML Confluence (storage format).

Vi sao khong dung lai duong TSV: bang that dung `rowspan`, nen hang thu hai cua
mot event CHI CO 2 o - sau o kia bi o rowspan phia tren chiem. Dem o theo dong
se ra "2 cot, can 8" va bao loi oan. Ranh gioi o phai lay tu LUOI HTML, khong
tu dau tab.

Do tren trang that (SDK Widget V 1.0.0, page 306053648):
  - header nam trong <td><strong>, KHONG phai <th>
  - o chua <p><span>...</span></p> long nhau, co ca &nbsp; va &quot;
"""

from __future__ import annotations

from pathlib import Path

from usv.confluence_table import find_spec_table, tables_of
from usv.event_spec_confluence import parse_page

FIXTURE = (Path(__file__).parent / "fixtures"
           / "confluence-event-table.html").read_text(encoding="utf-8")


def test_rowspan_duoc_trai_ra_du_cot():
    """Hang 2 chi co 2 <td> nhung phai thanh 8 cot."""
    grid = tables_of(FIXTURE)[0]
    assert all(len(row) == 8 for row in grid), \
        f"moi hang phai du 8 cot, dang la {[len(r) for r in grid]}"
    assert len(grid) == 3, "1 header + 2 hang"


def test_o_rowspan_de_hang_duoi_RONG_chu_khong_lap_lai():
    """O gop doc = "van la event nay", dung y het o Event_Name de trong o TSV.

    Lap lai chu thi mot event bi dem thanh hai event trung ten - da gap khi
    viet module nay.
    """
    grid = tables_of(FIXTURE)[0]
    assert grid[1][1] == "event_mot"
    assert grid[2][1] == "", "hang noi tiep khong duoc lap lai ten event"


def test_go_the_va_giai_ma_ky_tu():
    grid = tables_of(FIXTURE)[0]
    assert grid[0][0] == "Screen Name", "the <p><span><strong> phai bi go het"
    assert grid[1][7] == 'Vi tri man"A"', "&quot; phai duoc giai ma"
    assert grid[1][0] == "Man A", "&nbsp; thua phai bi gom lai"


def test_chon_dung_bang_spec_giua_nhieu_bang():
    """Trang that co ca bang Requirements va List Remote Key - khong duoc lay nham."""
    noise = ("<table><tbody><tr><th>Remote Key</th><th>Data Type</th></tr>"
             "<tr><td>show_x</td><td>Boolean</td></tr></tbody></table>")
    grid = find_spec_table(noise + FIXTURE)
    assert grid is not None
    assert grid[0][1] == "Event_Name"


def test_khong_co_bang_spec_thi_tra_None():
    assert find_spec_table("<p>trang khong co bang event nao</p>") is None


def test_parse_page_ra_dung_spec():
    sheet = parse_page(FIXTURE)
    assert sheet.errors == (), sheet.errors
    assert [e.name for e in sheet.events] == ["event_mot"]
    event = sheet.events[0]
    assert event.screen == "Man A"
    assert event.triggered == "Khi hien thi man A"
    assert [p.name for p in event.params] == ["ten_cho"]
    assert event.params[0].allowed == ("home", "result")
    assert event.params[0].value_type == "String"


def test_trang_khong_co_bang_thi_bao_loi_ro_rang():
    sheet = parse_page("<p>khong co gi</p>")
    assert sheet.errors and "Event_Name" in sheet.errors[0]
