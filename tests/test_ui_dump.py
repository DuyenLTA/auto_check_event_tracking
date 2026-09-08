"""Parse cay UI. Assert theo dump THAT da do tay luc spike (tests/fixtures).

Cac con so trong file nay chinh la ket qua spike GO/NO-GO. Neu chung doi nghia
la parser sai, hoac fixture bi thay - khong duoc sua assert cho khop, phai tim
hieu vi sao truoc.
"""

from __future__ import annotations

import pytest

from usv.models import Bounds
from usv.ui_dump import (
    app_nodes, dump_stats, is_system_node, parse_bounds, parse_dump, strip_package,
)


def test_parse_bounds():
    assert parse_bounds("[0,72][1080,283]") == Bounds(0, 72, 1080, 283)
    assert parse_bounds(" [57,315][504,762] ") == Bounds(57, 315, 504, 762)


def test_parse_bounds_toa_do_am():
    """Node scroll ra ngoai man hinh co bounds am - phai doc duoc, khong crash."""
    assert parse_bounds("[-263,-141][763,653]") == Bounds(-263, -141, 763, 653)


@pytest.mark.parametrize("bad", ["", "0,72,1080,283", "[0,72]", "rac"])
def test_parse_bounds_tu_choi_rac(bad):
    with pytest.raises(ValueError):
        parse_bounds(bad)


def test_strip_package():
    assert strip_package("com.x.app:id/tvTitle") == "tvTitle"
    assert strip_package("tvTitle") == "tvTitle"
    assert strip_package("") == ""


def test_dump_that_ra_dung_so_luong_node(spike_xml, metrics):
    nodes = parse_dump(spike_xml, metrics)
    assert len(nodes) == 25  # so do tay luc spike


def test_dump_that_giu_dung_chi_so_spike(spike_xml, metrics):
    """Day la ket qua GO/NO-GO: 100% leaf node match duoc, 0 node Compose."""
    stats = dump_stats(parse_dump(spike_xml, metrics))
    assert stats["total"] == 25
    assert stats["with_resource_id"] == 17
    assert stats["leaves"] == 10
    assert stats["leaves_with_resource_id"] == 10
    assert stats["leaves_matchable"] == 10
    assert stats["compose_nodes"] == 0


def test_resource_id_KHONG_unique_trong_dump_that(spike_xml, metrics):
    """Chuyen quan trong nhat cua ca tool.

    1 GridView chua 4 card, ca 4 dung chung resource-id 'borderContainer'. Neu
    matcher khoa bang resource_id mot minh thi 4 card se dồn vào 1 design node
    -> sai toan bo ket qua. Vi vay khoa la (resource_id, index_in_parent).
    """
    nodes = parse_dump(spike_xml, metrics)
    borders = [n for n in nodes if n.resource_id == "borderContainer"]
    assert len(borders) == 4, "fixture phai co 4 card dung chung resource-id"

    # resource_id mot minh: trung nhau -> KHONG dung lam khoa duoc
    assert len({n.resource_id for n in borders}) == 1
    # khoa that su: match_key phan biet duoc, va node_id thi luon unique
    assert len({n.node_id for n in borders}) == 4


def test_match_key_phan_biet_card_cung_hang(spike_xml, metrics):
    """2 card cung 1 hang GridView co index_in_parent khac nhau."""
    nodes = parse_dump(spike_xml, metrics)
    titles = [n for n in nodes if n.resource_id == "tvQuestionTitle"]
    assert len(titles) == 4
    # moi title nam trong 1 ViewGroup card rieng -> parent khac nhau
    assert len({n.parent_id for n in titles}) == 4


def test_cay_giu_quan_he_cha_con(spike_xml, metrics):
    nodes = parse_dump(spike_xml, metrics)
    by_id = {n.node_id: n for n in nodes}
    for node in nodes:
        if node.parent_id is not None:
            assert node.parent_id in by_id, f"{node.node_id} tro tro toi cha khong ton tai"
            assert by_id[node.parent_id].depth == node.depth - 1


def test_bounds_dp_khop_so_do_tay(spike_xml, metrics):
    nodes = parse_dump(spike_xml, metrics)
    border = next(n for n in nodes if n.resource_id == "borderContainer")
    assert border.bounds_px.as_tuple() == (57, 315, 504, 762)
    assert border.bounds_dp.size_tuple() == (162.5, 162.5)

    header = next(n for n in nodes if n.resource_id == "tvQuestionHeader")
    assert header.bounds_dp.as_tuple()[:2] == (0.0, 26.2)


def test_loc_node_he_thong(spike_xml, metrics):
    """android:id/content, action_bar_root... co trong MOI Activity - phai bo
    khoi bucket EXTRA, khong thi report day ra hang chuc dong vo nghia."""
    nodes = parse_dump(spike_xml, metrics)
    assert any(is_system_node(n) for n in nodes)
    kept = app_nodes(nodes)
    assert all(n.resource_id not in {"content", "action_bar_root"} for n in kept)
    assert len(kept) < len(nodes)


def test_node_thieu_bounds_khong_lam_crash(metrics):
    """XML den tu device - khong tin duoc dinh dang. Node loi phai bi danh dau
    invisible chu khong duoc lam vo ca lan capture."""
    xml = (
        '<?xml version="1.0"?><hierarchy rotation="0">'
        '<node class="android.widget.FrameLayout" bounds="RAC" resource-id="x:id/a"/>'
        '<node class="android.widget.TextView" bounds="[0,0][10,10]" text="ok"/>'
        "</hierarchy>"
    )
    nodes = parse_dump(xml, metrics)
    assert len(nodes) == 2
    assert nodes[0].visible is False
    assert nodes[1].visible is True


def test_node_bounds_rong_la_invisible(metrics):
    xml = (
        '<?xml version="1.0"?><hierarchy rotation="0">'
        '<node class="android.view.View" bounds="[10,10][10,10]"/>'
        "</hierarchy>"
    )
    assert parse_dump(xml, metrics)[0].visible is False


def test_thu_tu_la_pre_order(metrics):
    """`order` cua check order phase sau dua vao thu tu nay."""
    xml = (
        '<?xml version="1.0"?><hierarchy rotation="0">'
        '<node class="A" bounds="[0,0][1,1]">'
        '<node class="B" bounds="[0,0][1,1]"/><node class="C" bounds="[0,0][1,1]"/>'
        "</node><node class=\"D\" bounds=\"[0,0][1,1]\"/>"
        "</hierarchy>"
    )
    assert [n.cls for n in parse_dump(xml, metrics)] == ["A", "B", "C", "D"]
