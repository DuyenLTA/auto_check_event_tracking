"""Phan giai selector tren cay UI THAT (tests/fixtures/spike-dump.xml).

Dump nay co mot GridView chua 4 card dung chung resource_id `borderContainer` -
day la ly do khoa selector la (resource_id, index) chu khong bao gio la
resource_id mot minh.
"""

from __future__ import annotations

import asyncio

import pytest

from usv.adb_parsers import AdbError
from usv.device_actions import Selector, find, swipe, tap
from usv.ui_dump import parse_dump


class FakeClient:
    def __init__(self) -> None:
        self.taps: list[tuple[float, float]] = []
        self.swipes: list[tuple[float, float, float, float]] = []

    async def input_tap(self, serial, x, y):
        self.taps.append((x, y))

    async def input_swipe(self, serial, x1, y1, x2, y2, duration_ms=300):
        self.swipes.append((x1, y1, x2, y2))


@pytest.fixture
def nodes(spike_xml, metrics):
    return parse_dump(spike_xml, metrics)


def test_resource_id_trung_nhau_that_tren_dump_nay(nodes):
    """Neu dump doi va khong con trung nua thi test duoi mat y nghia."""
    hits = [n for n in nodes if n.resource_id == "borderContainer"]
    assert len(hits) == 4, "dump phai co 4 node dung chung resource_id"


def test_index_chon_dung_node_thu_may(nodes):
    first = find(nodes, Selector(resource_id="borderContainer", index=0))
    third = find(nodes, Selector(resource_id="borderContainer", index=2))
    assert first.bounds_px.top < third.bounds_px.top, "index phai chon node khac nhau"


def test_index_vuot_so_node_khop_bao_loi_ro(nodes):
    with pytest.raises(AdbError) as info:
        find(nodes, Selector(resource_id="borderContainer", index=9))
    assert "chi co 4 node" in str(info.value)


def test_tim_theo_text(nodes):
    node = find(nodes, Selector(text="Japandi Style"))
    assert node.resource_id == "tvQuestionTitle"


def test_tim_theo_text_khong_phan_biet_hoa_thuong(nodes):
    assert find(nodes, Selector(text="japandi style")).resource_id == "tvQuestionTitle"


def test_khong_thay_thi_goi_y_node_gan_giong(nodes):
    """Bao 'not found' mot minh thi tester phai tu doc dump hang tram node."""
    with pytest.raises(AdbError) as info:
        find(nodes, Selector(text="Japandi Styl"))
    message = str(info.value)
    assert "Gan giong" in message
    assert "Japandi Style" in message


def test_khong_co_gi_gan_giong_thi_noi_thang(nodes):
    with pytest.raises(AdbError) as info:
        find(nodes, Selector(resource_id="zzzzzzzzz"))
    assert "Khong co gi gan giong" in str(info.value)


def test_bam_vao_TAM_node_khong_phai_goc(nodes):
    """Goc tren-trai co the nam ngoai vung bam duoc."""
    client = FakeClient()
    node = asyncio.run(tap(client, "S1", nodes, Selector(text="Japandi Style")))
    box = node.bounds_px
    assert client.taps == [((box.left + box.right) / 2, (box.top + box.bottom) / 2)]


def test_quet_nam_TRONG_node(nodes):
    """Quet ca man de trung thanh dieu huong hoac notification shade."""
    client = FakeClient()
    node = asyncio.run(swipe(client, "S1", nodes,
                             Selector(resource_id="rvQuestion"), "up"))
    x1, y1, x2, y2 = client.swipes[0]
    box = node.bounds_px
    assert box.top <= y2 < y1 <= box.bottom
    assert x1 == x2 == (box.left + box.right) / 2


def test_huong_quet_la_bao_loi(nodes):
    with pytest.raises(AdbError):
        asyncio.run(swipe(FakeClient(), "S1", nodes,
                          Selector(resource_id="rvQuestion"), "cheo"))


def test_selector_theo_chu_bi_danh_dau_de_vo():
    assert Selector(text="Home").fragile is True
    assert Selector(desc="Back").fragile is True
    assert Selector(resource_id="btnHome").fragile is False


def test_selector_nhan_ro_kieu_va_gia_tri():
    assert Selector(resource_id="btnA").label() == "resource_id='btnA'"
    assert Selector(text="Xin chao", index=2).label() == "text='Xin chao'[2]"
