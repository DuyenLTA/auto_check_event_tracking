"""Doc flow YAML: dung thi ra Flow, sai thi noi ro sai o case/step nao.

Vi sao khong raise ngay o loi dau tien: sua mot loi roi chay lai de gap loi
tiep theo la vong lap vo nghia. Gom het loi vao `Flow.errors` nhu SpecSheet.
Chi `FlowError` khi ca file khong doc duoc (sai cu phap, khong phai mapping).
"""

from pathlib import Path

import pytest

from usv.flow_yaml import FlowError, load, parse

VALID = {
    "package": "com.example.app",
    "cases": [
        {"event": "widget_show",
         "label": "placement=result",
         "expect_params": {"placement_name": "result"},
         "reset": {"remote_config": {"widget_enabled": "true"},
                   "clear_prefs": ["apero_rate_prefs.xml"],
                   "relaunch": True},
         "steps": [
             {"kind": "launch"},
             {"kind": "tap", "resource_id": "btn_result"},
             {"kind": "wait", "seconds": 2},
             {"kind": "wait_text", "text": "Widget", "timeout": 10},
         ]},
    ],
}


def test_yaml_hop_le_ra_flow_dung():
    flow = parse(VALID)
    assert flow.ok, flow.errors
    assert flow.package == "com.example.app"
    case = flow.cases[0]
    assert case.event == "widget_show"
    assert case.name == "placement=result"
    assert case.expect_params == {"placement_name": "result"}
    assert case.reset.remote_config == {"widget_enabled": "true"}
    assert case.reset.clear_prefs == ("apero_rate_prefs.xml",)
    assert case.reset.relaunch is True
    assert [s.kind for s in case.steps] == ["launch", "tap", "wait", "wait_text"]
    assert case.steps[1].selector.resource_id == "btn_result"
    assert case.steps[2].seconds == 2.0
    assert case.steps[3].timeout == 10.0


def test_thieu_event_la_loi():
    """Khong co ten event thi `mark_label` khong chen moc duoc -> cua so vo danh."""
    flow = parse({"package": "com.x", "cases": [{"steps": [{"kind": "launch"}]}]})
    assert not flow.ok
    assert not flow.cases
    assert any("event" in e for e in flow.errors), flow.errors


def test_selector_hai_truong_la_loi():
    flow = parse({"package": "com.x", "cases": [
        {"event": "e1", "steps": [
            {"kind": "tap", "resource_id": "btn", "text": "OK"}]}]})
    assert not flow.ok
    assert any("case 1" in e and "step 1" in e for e in flow.errors), flow.errors


def test_kind_la_la_loi():
    flow = parse({"package": "com.x", "cases": [
        {"event": "e1", "steps": [{"kind": "shake"}]}]})
    assert not flow.ok
    assert any("shake" in e for e in flow.errors), flow.errors


def test_selector_text_canh_bao_fragile_nhung_van_chay():
    flow = parse({"package": "com.x", "cases": [
        {"event": "e1", "steps": [{"kind": "tap", "text": "Bắt đầu"}]}]})
    assert flow.ok, flow.errors
    assert flow.cases[0].fragile_steps, "selector theo chu phai bi danh dau fragile"


def test_file_rong_ra_flow_rong_khong_no():
    flow = parse({})
    assert flow.cases == ()
    assert not flow.ok          # rong thi khong co gi ma chay
    assert flow.package == ""


@pytest.mark.parametrize("raw, tu_khoa", [
    ({"package": "com.x", "cases": [{"event": "e", "steps": [{"kind": "tap"}]}]},
     "selector"),
    ({"package": "com.x", "cases": [{"event": "e", "steps": [{"kind": "wait"}]}]},
     "seconds"),
    ({"package": "com.x", "cases": [{"event": "e", "steps": [{"kind": "wait_text"}]}]},
     "text"),
])
def test_step_thieu_truong_bat_buoc(raw, tu_khoa):
    flow = parse(raw)
    assert not flow.ok
    assert any(tu_khoa in e for e in flow.errors), flow.errors


def test_thieu_package_la_loi():
    flow = parse({"cases": [{"event": "e1", "steps": [{"kind": "launch"}]}]})
    assert not flow.ok
    assert any("package" in e for e in flow.errors), flow.errors


def test_yaml_sai_cu_phap_thi_FlowError(tmp_path: Path):
    path = tmp_path / "bad.yaml"
    path.write_text("cases: [\n  - event: e1\n", encoding="utf-8")
    with pytest.raises(FlowError) as err:
        load(path)
    assert "bad.yaml" in str(err.value)


def test_khong_co_file_thi_FlowError(tmp_path: Path):
    with pytest.raises(FlowError):
        load(tmp_path / "khong-ton-tai.yaml")


def test_load_file_thuc_te(tmp_path: Path):
    path = tmp_path / "flow.yaml"
    path.write_text(
        "package: com.example.app\n"
        "cases:\n"
        "  - event: widget_show\n"
        "    steps:\n"
        "      - {kind: tap, resource_id: btn_result}\n",
        encoding="utf-8")
    flow = load(path)
    assert flow.ok, flow.errors
    assert flow.cases[0].steps[0].selector.resource_id == "btn_result"


def test_vi_du_trong_flows_hop_le():
    """`flows/example.yaml` la format chuan ma cli_record phai ghi theo - no
    hong thi phase sau ghi ra file khong ai doc duoc."""
    root = Path(__file__).resolve().parent.parent
    flow = load(root / "flows" / "example.yaml")
    assert flow.ok, flow.errors


def test_flow_chay_duoc_bang_run_flow():
    """Flow parse ra phai dut duoc vao `event_flow_run.run_step` - khong thi
    parser va runner dang noi hai thu tieng khac nhau."""
    from usv.event_flow_run import run_step
    import inspect
    flow = parse(VALID)
    kinds = {s.kind for c in flow.cases for s in c.steps}
    src = inspect.getsource(run_step)
    for kind in kinds:
        assert f'step.kind == "{kind}"' in src, f"run_step khong hieu {kind!r}"


def test_step_tuy_chon_doc_duoc_tu_yaml():
    """Quang cao xen ke luc co luc khong. Khong co `optional` thi happy case
    vo moi lan quang cao doi y."""
    flow = parse({"package": "com.x", "cases": [
        {"event": "e1", "steps": [
            {"kind": "tap", "resource_id": "dismiss-button", "optional": True},
            {"kind": "tap", "resource_id": "btnHome"}]}]})
    assert flow.ok, flow.errors
    assert [s.optional for s in flow.cases[0].steps] == [True, False]
    assert "tuỳ chọn" in flow.cases[0].steps[0].label()


def test_buoc_intent_doc_duoc_action_va_component(tmp_path):
    """Man Rating o app shortcut khong co nut nao trong app dan sang - intent la
    duong duy nhat toi no."""
    from usv import flow_yaml

    path = tmp_path / "f.yaml"
    path.write_text(
        "package: com.x\n"
        "cases:\n"
        "  - event: rating_placement_viewed\n"
        "    steps:\n"
        "      - kind: intent\n"
        "        action: com.apero.rating.action.RATING\n"
        "        component: com.x/com.apero.rating.RatingActivity\n",
        encoding="utf-8")
    flow = flow_yaml.load(path)
    assert flow.errors == ()
    step = flow.cases[0].steps[0]
    assert step.kind == "intent"
    assert step.text == "com.apero.rating.action.RATING"
    assert step.component == "com.x/com.apero.rating.RatingActivity"


def test_intent_thieu_action_thi_bao_ngay(tmp_path):
    """Thieu action thi `am start` mo mot man bat ky - case chay tren man khac
    ma van bao ket qua."""
    from usv import flow_yaml

    path = tmp_path / "f.yaml"
    path.write_text(
        "package: com.x\n"
        "cases:\n"
        "  - event: e\n"
        "    steps:\n"
        "      - kind: intent\n"
        "        component: com.x/A\n",
        encoding="utf-8")
    flow = flow_yaml.load(path)
    assert flow.errors and "action" in flow.errors[0]


# --- bien the ngon ngu: mot o nhan nhieu chuoi ---

def _mot_step(step: dict):
    """Flow toi thieu quanh MOT step, de test trung vao step do."""
    return parse({"package": "com.x", "cases": [
        {"event": "e", "label": "l", "steps": [step]}]})


def test_selector_nhan_nhieu_bien_the_ngon_ngu():
    """Chuoi tren man HE THONG doi theo locale cua may.

    Do duoc that: may de vi-VN, picker anh hien desc "Ảnh được chụp lúc..."
    trong khi flow cho "Photo taken on" - ngoi het 30 giay roi bao "Chua test"
    trong khi picker mo binh thuong.
    """
    flow = _mot_step({"kind": "tap",
                      "desc": ["Photo taken on*", "Ảnh được chụp lúc*"]})
    assert flow.ok, flow.errors
    sel = flow.cases[0].steps[0].selector
    assert sel.desc == "Photo taken on*"
    assert sel.alt == ("Ảnh được chụp lúc*",)
    assert sel.needles == ("Photo taken on*", "Ảnh được chụp lúc*")


def test_wait_text_nhan_nhieu_bien_the():
    flow = _mot_step({"kind": "wait_text", "text": ["Done", "Xong"]})
    assert flow.ok, flow.errors
    step = flow.cases[0].steps[0]
    assert (step.text, step.text_alt) == ("Done", ("Xong",))


def test_mot_chuoi_van_chay_nhu_cu():
    """Khai mot chuoi tron thi khong duoc doi hanh vi - ca tram step dang vay."""
    flow = _mot_step({"kind": "tap", "text": "PREMIUM"})
    assert flow.ok, flow.errors
    sel = flow.cases[0].steps[0].selector
    assert sel.alt == () and sel.needles == ("PREMIUM",)


def test_type_va_key_KHONG_nhan_danh_sach():
    """`type` go chu, `key` bam phim - chi co MOT gia tri dung.

    Nhan danh sach roi lay phan tu dau la am tham bo mat phan con lai.
    """
    flow = _mot_step({"kind": "type", "text": ["a", "b"]})
    assert not flow.ok
    assert any("chỉ nhận một" in e for e in flow.errors), flow.errors


def test_bao_loi_in_ca_hai_bien_the():
    """Bao loi chi ra mot chuoi trong khi flow tim hai thi nguoi doc di sua
    nham cai khong hong."""
    from usv.device_actions import Selector
    nhan = Selector(desc="Photo taken on*", alt=("Ảnh được chụp lúc*",)).label()
    assert "Photo taken on*" in nhan and "Ảnh được chụp lúc*" in nhan
