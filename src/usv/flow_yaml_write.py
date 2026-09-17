"""Ghi `Flow` ra YAML - dang ma chinh `flow_yaml.load` doc lai duoc.

Round-trip la rang buoc cung: `record` ghi ra ma `check` khong doc duoc thi
nguoi dung phai sua tay moi lan, va cai sai chi lo ra luc dang cham dang do.
Test `test_ghi_ra_roi_doc_lai_duoc_y_nguyen` giu viec do.

File flow la file NGUOI doc va sua tay, nen: giu thu tu khoa nhu luc viet tay
(`sort_keys=False`), va khong escape tieng Viet (`allow_unicode=True`).
"""

from __future__ import annotations

from pathlib import Path

import yaml

from .event_flow_models import Flow, FlowCase, Step
from .flow_yaml import load

# Kind nao doc `text` lam DU LIEU (chu de go / de cho / ten phim).
TEXT_KINDS = frozenset({"type", "key", "wait_text"})


def step_to_dict(step: Step) -> dict:
    ra: dict = {"kind": step.kind}
    if step.selector is not None:
        ra[step.selector.kind] = step.selector.needle
        # Luon ghi `index`, ke ca 0: resource_id trung nhau la chuyen that, va
        # mot id tran trong file lam nguoi doc tuong no duy nhat.
        ra["index"] = step.selector.index
    if step.kind == "swipe":
        ra["direction"] = step.text or "up"
    elif step.kind in TEXT_KINDS:
        ra["text"] = step.text
    if step.kind == "wait":
        ra["seconds"] = step.seconds
    if step.kind == "wait_text":
        ra["timeout"] = step.timeout
    return ra


def case_to_dict(case: FlowCase) -> dict:
    ra: dict = {"event": case.event}
    if case.name:
        ra["label"] = case.name
    if case.expect_params:
        ra["expect_params"] = dict(case.expect_params)
    reset = case.reset
    if not reset.empty or not reset.relaunch:
        khoi: dict = {}
        if reset.remote_config:
            khoi["remote_config"] = dict(reset.remote_config)
        if reset.clear_prefs:
            khoi["clear_prefs"] = list(reset.clear_prefs)
        khoi["relaunch"] = reset.relaunch
        ra["reset"] = khoi
    ra["steps"] = [step_to_dict(s) for s in case.steps]
    return ra


def flow_to_yaml(flow: Flow) -> str:
    raw = {"package": flow.package,
           "cases": [case_to_dict(c) for c in flow.cases]}
    return yaml.safe_dump(raw, sort_keys=False, allow_unicode=True,
                          default_flow_style=False)


def append_case(path: Path | str, package: str, case: FlowCase) -> Path:
    """Noi mot case vao file flow. File cu hong -> FlowError, KHONG de len.

    Giu ban sao `.bak` truoc khi ghi: file nay co the chua case go tay hang gio,
    va mot lan ghi hong la mat trang.
    """
    path = Path(path)
    cu = load(path) if path.exists() else Flow(package=package)
    moi = Flow(package=package or cu.package, cases=(*cu.cases, case))

    if path.exists():
        path.with_suffix(path.suffix + ".bak").write_text(
            path.read_text(encoding="utf-8"), encoding="utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(flow_to_yaml(moi), encoding="utf-8")
    return path
