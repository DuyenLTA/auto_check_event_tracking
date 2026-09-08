"""Doc flow YAML. Khong can may.

Hai bat buoc:
  - STEP LA -> loi noi ro, KHONG bo qua im lang. Bo qua thi case chay thieu
    buoc, event khong ban ra, roi bao FAIL oan cho app.
  - Loi gom het mot luot, khong raise o cai dau tien - tester sua mot lan.
"""

from __future__ import annotations

import asyncio
import pathlib

import pytest

from usv.device_actions import find
from usv.event_flow_parse import parse_flow
from usv.event_flow_step_parse import allowed_steps
from usv.ui_dump import parse_dump

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def _flow():
    return parse_flow((FIXTURES / "flow-rating.yaml").read_text(encoding="utf-8"))


# --- Fixture that doc duoc ----------------------------------------------------

def test_fixture_doc_duoc_khong_loi():
    flow = _flow()
    assert flow.errors == ()
    assert flow.ok
    assert flow.package == "com.aihomedesign.aihomedecor.designidea.aiinterior"
    assert len(flow.cases) == 3


def test_package_o_document_thang_vao_flow():
    assert parse_flow("package: com.x\nevents: []\n").package == "com.x"


def test_danh_sach_tran_van_doc_duoc_va_nhan_package_tu_tham_so():
    text = "- event: e\n  cases:\n    - steps: [launch]\n"
    flow = parse_flow(text, package="com.y")
    assert flow.ok and flow.package == "com.y"


def test_mot_case_mot_event():
    events = [c.event for c in _flow().cases]
    assert events == ["rating_placement_viewed", "rating_placement_viewed",
                      "rating_star_clicked"]


def test_expect_params_la_gia_tri_case_nay_phai_ra():
    first = _flow().cases[0]
    assert first.expect_params == {"placement_name": "home"}


def test_name_khai_tay_thi_lam_nhan_con_khong_thi_sinh_tu_params():
    cases = _flow().cases
    assert cases[1].label == "rating tu man Result"
    assert cases[0].label == "rating_placement_viewed (placement_name=home)"


# --- Step dich ra dung kind runner hieu ---------------------------------------

def test_step_dich_ra_dung_kind():
    kinds = [s.kind for s in _flow().cases[0].steps]
    assert kinds == ["launch", "wait_text", "tap", "wait"]


def test_back_tran_thanh_keyevent_BACK():
    step = _flow().cases[1].steps[-1]
    assert (step.kind, step.text) == ("key", "BACK")


def test_index_doc_duoc__resource_id_mot_minh_khong_khoa_duoc_node():
    tap = _flow().cases[1].steps[2]
    assert tap.selector.index == 2
    assert tap.selector.resource_id == "borderContainer"


def test_swipe_giu_huong():
    swipe = _flow().cases[1].steps[3]
    assert (swipe.kind, swipe.text) == ("swipe", "up")


def test_don_vi_thoi_gian():
    assert parse_flow("- event: e\n  cases:\n    - steps:\n        - wait: 500ms\n"
                      ).cases[0].steps[0].seconds == 0.5
    assert parse_flow("- event: e\n  cases:\n    - steps:\n        - wait: 2s\n"
                      ).cases[0].steps[0].seconds == 2.0
    assert parse_flow("- event: e\n  cases:\n    - steps:\n        - wait: 1.5\n"
                      ).cases[0].steps[0].seconds == 1.5


def test_wait_text_timeout_mac_dinh_10s_va_khai_lai_duoc():
    bare = parse_flow('- event: e\n  cases:\n    - steps:\n        - wait_text: Home\n')
    assert bare.cases[0].steps[0].timeout == 10.0
    assert _flow().cases[1].steps[1].timeout == 15.0


# --- Tu choi cai khong hieu ---------------------------------------------------

def test_step_la_bi_tu_choi_kem_danh_sach_cho_phep():
    flow = parse_flow("- event: e\n  cases:\n    - steps:\n        - tap_di: btnHome\n")
    assert not flow.ok
    assert any("tap_di" in e and "Chi co:" in e for e in flow.errors)


def test_message_loi_liet_ke_du_ten_step_de_tester_tu_sua():
    """Chi kiem NOI DUNG MESSAGE. Hop dong that voi runner nam o
    test_event_flow_parse_regressions.py."""
    listed = allowed_steps()
    for name in ("tap_id", "tap_text", "tap_desc", "swipe", "wait", "wait_text",
                 "key", "type", "launch", "back"):
        assert name in listed


def test_huong_swipe_la_bi_tu_choi():
    flow = parse_flow("- event: e\n  cases:\n    - steps:\n"
                      "        - swipe: {id: x, dir: nghieng}\n")
    assert not flow.ok
    assert any("nghieng" in e for e in flow.errors)


def test_selector_rong_bi_bao():
    flow = parse_flow("- event: e\n  cases:\n    - steps:\n        - tap_id: ''\n")
    assert not flow.ok
    assert any("thieu gia tri de tim node" in e for e in flow.errors)


def test_index_am_bi_bao():
    flow = parse_flow("- event: e\n  cases:\n    - steps:\n"
                      "        - tap_id: {id: x, index: -1}\n")
    assert any("index" in e for e in flow.errors)


def test_reset_khoa_la_bi_bao__pm_clear_khong_ton_tai_o_day():
    flow = parse_flow("- event: e\n  cases:\n    - reset: {pm_clear: true}\n"
                      "      steps: [launch]\n")
    assert any("pm_clear" in e for e in flow.errors)


def test_thieu_ten_event_bi_bao():
    assert not parse_flow("- cases:\n    - steps: [launch]\n").ok


def test_event_khong_co_case_bi_bao():
    flow = parse_flow("- event: rating_star_clicked\n")
    assert any("khong co case nao" in e for e in flow.errors)


def test_case_khong_co_step_bi_bao__khong_lai_app_di_dau():
    flow = parse_flow("- event: e\n  cases:\n    - params: {a: b}\n")
    assert any("khong lai app di dau" in e for e in flow.errors)


def test_yaml_sai_cu_phap_bao_loi_chu_khong_raise():
    flow = parse_flow("- event: e\n   cases: [\n")
    assert not flow.ok
    assert any("YAML sai cu phap" in e for e in flow.errors)


def test_flow_rong_bao_loi_chu_khong_tra_ok():
    assert not parse_flow("").ok
    assert not parse_flow("[]").ok


def test_gom_HET_loi_mot_luot_chu_khong_dung_o_cai_dau():
    flow = parse_flow("- event: e\n  cases:\n    - steps:\n"
                      "        - tap_di: a\n        - vuot: b\n        - wait: lau\n")
    assert len(flow.errors) >= 3


def test_mot_case_loi_khong_lam_mat_case_dung():
    flow = parse_flow("- event: e\n  cases:\n    - steps: [launch]\n"
                      "    - steps:\n        - tap_di: a\n")
    assert len(flow.cases) == 1 and flow.errors


# --- Canh bao selector theo chu ----------------------------------------------

def test_tap_text_bi_gan_co_fragile__canh_bao_chu_khong_chan():
    star = _flow().cases[2]
    assert star.fragile_steps
    assert "tap_text" not in str(star.fragile_steps)   # nhan la kind cua Selector
    assert any("Japandi" in f for f in star.fragile_steps)


def test_tap_id_khong_bi_gan_co_fragile():
    assert _flow().cases[0].fragile_steps == ()


# --- Selector parser sinh ra phai tim duoc node tren dump THAT ----------------

@pytest.fixture
def nodes(spike_xml, metrics):
    return parse_dump(spike_xml, metrics)


def test_selector_tu_flow_tim_duoc_node_tren_dump_that(nodes):
    tap = _flow().cases[0].steps[2]
    node = find(nodes, tap.selector)
    assert node.resource_id == "tvQuestionTitle"
    assert not node.bounds_px.empty


def test_index_tu_flow_chon_dung_card_thu_3_trong_grid(nodes):
    tap = _flow().cases[1].steps[2]
    shared = [n for n in nodes if n.resource_id == tap.selector.resource_id
              and not n.bounds_px.empty]
    assert len(shared) > 2, "dump nay phai co nhieu node dung chung borderContainer"
    assert find(nodes, tap.selector) is shared[2]


# --- Hop dong parser <-> runner ----------------------------------------------
# Test o tren chi doc CHU trong allowed_steps(). Test duoi chay THAT qua
# run_step: parser sinh ra `kind` ma runner khong xu ly thi vo o day, chu khong
# doi den luc cam may moi biet.

def test_moi_step_cua_fixture_chay_duoc_qua_run_step(recorder, metrics, no_sleep):
    """Parser sinh ra `kind` ma runner khong xu ly thi vo o day, chu khong doi
    den luc cam may moi biet."""
    from usv import event_flow_run

    flow = _flow()

    async def drive():
        for case in flow.cases:
            for step in case.steps:
                await event_flow_run.run_step(recorder, "S1", metrics,
                                              flow.package, step)

    asyncio.run(drive())
    assert recorder.done.count("launch") == 3
    assert any(d.startswith("tap:") for d in recorder.done)
    assert "swipe" in recorder.done
    assert "key:BACK" in recorder.done and "key:ENTER" in recorder.done
