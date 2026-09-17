"""Ghi flow ra YAML. Thu do PHAI doc lai duoc bang chinh `flow_yaml.load`.

Ghi ra mot dang ma parser cua minh khong doc duoc thi `record` sinh ra file
chet: nguoi dung phai sua tay, va `check` thi bao "flow hong" ma khong ai hieu
tai sao.
"""

from __future__ import annotations

from pathlib import Path

from usv.device_actions import Selector
from usv.event_flow_models import Flow, FlowCase, Reset, Step
from usv.flow_yaml import load
from usv.flow_yaml_write import append_case, flow_to_yaml

CASE = FlowCase(
    event="rating_placement_viewed", name="tại home",
    expect_params={"placement_name": "home"},
    reset=Reset(remote_config={"rating_enabled": "true"},
                clear_prefs=("apero_rate_prefs.xml",), relaunch=True),
    steps=(Step(kind="launch"),
           Step(kind="tap", selector=Selector(resource_id="btnHome", index=2)),
           Step(kind="wait", seconds=2),
           Step(kind="wait_text", text="Đánh giá", timeout=8),
           Step(kind="swipe", selector=Selector(desc="danh sách"), text="up"),
           Step(kind="type", text="hello"),
           Step(kind="key", text="KEYCODE_BACK")))


def test_ghi_ra_roi_doc_lai_duoc_y_nguyen(tmp_path: Path):
    path = tmp_path / "com.x.yaml"
    path.write_text(flow_to_yaml(Flow(package="com.x", cases=(CASE,))),
                    encoding="utf-8")
    lai = load(path)

    assert lai.ok, lai.errors
    case = lai.cases[0]
    assert case.event == CASE.event
    assert case.name == CASE.name
    assert case.expect_params == CASE.expect_params
    assert case.reset == CASE.reset
    assert [s.kind for s in case.steps] == [s.kind for s in CASE.steps]
    assert case.steps[1].selector == Selector(resource_id="btnHome", index=2)
    assert case.steps[2].seconds == 2
    assert case.steps[3].timeout == 8
    assert case.steps[4].text == "up"
    assert case.steps[5].text == "hello"


def test_noi_case_moi_khong_lam_mat_case_cu(tmp_path: Path):
    path = tmp_path / "com.x.yaml"
    append_case(path, "com.x", CASE)
    hai = FlowCase(event="rating_star_clicked", name="5 sao",
                   steps=(Step(kind="tap",
                               selector=Selector(resource_id="star5", index=0)),))
    append_case(path, "com.x", hai)

    lai = load(path)
    assert [c.event for c in lai.cases] == ["rating_placement_viewed",
                                            "rating_star_clicked"]


def test_ghi_de_thi_giu_mot_ban_sao_de_khoi_mat_trang(tmp_path: Path):
    path = tmp_path / "com.x.yaml"
    append_case(path, "com.x", CASE)
    append_case(path, "com.x", CASE)
    assert (tmp_path / "com.x.yaml.bak").exists()


def test_file_cu_hong_thi_khong_de_len_ma_bao_loi(tmp_path: Path):
    """De len mot file hong la mat luon nhung case nguoi ta go tay trong do."""
    from usv.flow_yaml import FlowError

    path = tmp_path / "com.x.yaml"
    path.write_text("cases: [\n  - event: x\n", encoding="utf-8")
    try:
        append_case(path, "com.x", CASE)
    except FlowError:
        return
    raise AssertionError("file hong ma van ghi de")


def test_selector_luon_kem_index(tmp_path: Path):
    """resource_id trung nhau la chuyen that (4 card cung mot id). Ghi id tran
    la lan replay sau bam vao card khac."""
    path = tmp_path / "com.x.yaml"
    append_case(path, "com.x", CASE)
    raw = path.read_text(encoding="utf-8")
    assert "index" in raw


def test_chu_tieng_viet_khong_bi_bien_thanh_ma_unicode(tmp_path: Path):
    path = tmp_path / "com.x.yaml"
    append_case(path, "com.x", CASE)
    raw = path.read_text(encoding="utf-8")
    assert "Đánh giá" in raw, "file de nguoi doc va sua tay - khong duoc \\u..."
