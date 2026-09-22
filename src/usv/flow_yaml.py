"""Doc `flows/<package>.yaml` -> Flow. Sai o dau noi dung cho do.

Gom loi thay vi raise o loi dau tien: sua mot dong roi chay lai de gap dong
sai tiep theo la vong lap vo nghia - giong cach SpecSheet tra ca events lan
errors. `FlowError` chi danh cho truong hop CA FILE khong doc duoc (sai cu
phap YAML, khong co file, tang goc khong phai mapping): luc do khong con gi
ma gom.

Selector khoa bang `text` KHONG bi chan, chi bi `FlowCase.fragile_steps` danh
dau: no vo khi app doi ngon ngu, nhung nhieu man khong co resource_id nao dung
duoc, chan thi tester het duong.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from .event_flow_models import Flow, FlowCase, Reset, Step
from .flow_yaml_selector import SELECTOR_FIELDS, bien_the, doc_selector

KINDS = frozenset({"launch", "tap", "swipe", "type", "key", "wait", "wait_text",
                   "intent", "close_popup",
                   "close_ad", "allow"})
# Chi tap/swipe moi lam viec tren mot node. `wait_text` va `type` cung co
# truong `text` nhung do la chu de TIM / de GO, doc no thanh selector thi
# `wait_text` bi danh dau fragile oan va Step.label() in ra sai viec.
NEEDS_SELECTOR = frozenset({"tap", "swipe"})
DEFAULT_TIMEOUT = 10.0


class FlowError(Exception):
    """Ca file khong doc duoc - khong phai mot dong sai."""


def _step(raw: object, where: str) -> tuple[Step | None, list[str]]:
    if not isinstance(raw, dict):
        return None, [f"{where}: step phải là mapping, đang là {type(raw).__name__}."]
    kind = str(raw.get("kind") or "").strip()
    if kind not in KINDS:
        shown = repr(kind) if kind else "(trống)"
        return None, [f"{where}: không hiểu kind {shown} — chọn một trong "
                      f"{', '.join(sorted(KINDS))}."]

    selector = None
    if kind in NEEDS_SELECTOR:
        selector, errors = doc_selector(raw, where)
        if errors:
            return None, errors
        if selector is None:
            return None, [f"{where}: `{kind}` cần selector "
                          f"(resource_id | text | desc)."]

    # Voi tap/swipe thi `text` la SELECTOR, khong phai chu de go. Chi nhung
    # kind that su can chu moi doc `text` lam du lieu.
    text = ""
    text_alt: tuple[str, ...] = ()
    component = ""
    if kind == "swipe":
        text = str(raw.get("direction") or "up").strip()
    elif kind == "intent":
        # `action` chu khong phai `text`: doc lai flow mot thang sau, "action"
        # noi ngay day la intent cua he thong, con "text" thi doc nhu chu de go.
        text = str(raw.get("action") or "").strip()
        if not text:
            return None, [f"{where}: `intent` cần `action` (vd "
                          f"com.apero.rating.action.RATING)."]
        component = str(raw.get("component") or "").strip()
    elif kind in {"type", "key", "wait_text", "close_popup"}:
        cac_chuoi = bien_the(raw.get("text"))
        if not cac_chuoi:
            return None, [f"{where}: `{kind}` cần `text`."]
        # `type` go chu va `key` bam phim - hai viec nay chi co MOT gia tri
        # dung. Nhan mot danh sach roi tu lay phan tu dau la am tham bo mat
        # phan con lai.
        if len(cac_chuoi) > 1 and kind in {"type", "key"}:
            return None, [f"{where}: `{kind}` chỉ nhận một `text`, "
                          f"đang khai {len(cac_chuoi)} giá trị."]
        text, *phu = cac_chuoi
        text_alt = tuple(phu)

    seconds = 0.0
    if kind == "wait":
        if raw.get("seconds") is None:
            return None, [f"{where}: `wait` cần `seconds`."]
        try:
            seconds = float(raw["seconds"])
        except (TypeError, ValueError):
            return None, [f"{where}: `seconds` phải là số, đang là {raw['seconds']!r}."]

    # `close_ad` mac dinh KIEM MOT LAN (timeout 0): man khong co quang cao la
    # truong hop thuong gap nhat, cho 10s o moi buoc do la moi case dai them
    # vai chuc giay khong de lam gi. Flow nao can cho (splash ad) thi khai
    # `timeout` ro rang.
    mac_dinh = 0.0 if kind in {"close_ad", "allow"} else DEFAULT_TIMEOUT
    try:
        timeout = float(raw.get("timeout") or mac_dinh)
    except (TypeError, ValueError):
        return None, [f"{where}: `timeout` phải là số, đang là {raw.get('timeout')!r}."]

    return Step(kind=kind, selector=selector, text=text, text_alt=text_alt,
                component=component, seconds=seconds, timeout=timeout,
                optional=bool(raw.get("optional", False))), []


def _reset(raw: object, where: str) -> tuple[Reset, list[str]]:
    if raw is None:
        return Reset(), []
    if not isinstance(raw, dict):
        return Reset(), [f"{where}: `reset` phải là mapping."]
    remote = raw.get("remote_config") or {}
    if not isinstance(remote, dict):
        return Reset(), [f"{where}: `reset.remote_config` phải là mapping key: value."]
    prefs = raw.get("clear_prefs") or []
    if isinstance(prefs, str):
        prefs = [prefs]
    if not isinstance(prefs, list):
        return Reset(), [f"{where}: `reset.clear_prefs` phải là danh sách tên file."]
    return Reset(remote_config={str(k): str(v) for k, v in remote.items()},
                 clear_prefs=tuple(str(p).strip() for p in prefs if str(p).strip()),
                 relaunch=bool(raw.get("relaunch", True))), []


def _case(raw: object, order: int) -> tuple[FlowCase | None, list[str]]:
    where = f"case {order}"
    if not isinstance(raw, dict):
        return None, [f"{where}: phải là một mapping."]
    event = str(raw.get("event") or "").strip()
    if not event:
        return None, [f"{where}: thiếu `event`. Không có tên event thì không chèn "
                      f"được mốc vào logcat, cửa sổ thành vô danh."]
    where = f"case {order} ({event})"

    errors: list[str] = []
    reset, reset_errors = _reset(raw.get("reset"), where)
    errors += reset_errors

    steps: list[Step] = []
    for index, raw_step in enumerate(raw.get("steps") or [], start=1):
        step, step_errors = _step(raw_step, f"{where}, step {index}")
        errors += step_errors
        if step is not None:
            steps.append(step)

    expect = raw.get("expect_params") or {}
    if not isinstance(expect, dict):
        errors.append(f"{where}: `expect_params` phải là mapping param: giá trị.")
        expect = {}

    if errors:
        # Case hong thi BO han: chay mot case parse dang do thi verdict cham ra
        # khong con nghia gi.
        return None, errors
    return FlowCase(event=event, name=str(raw.get("label") or "").strip(),
                    expect_params={str(k): str(v) for k, v in expect.items()},
                    steps=tuple(steps), reset=reset), []


def parse(raw: dict) -> Flow:
    """Mapping -> Flow. Loi tung dong nam trong `Flow.errors`, khong raise."""
    if not isinstance(raw, dict):
        raise FlowError("Flow phải là mapping `package:` + `cases:`.")
    if not raw:
        return Flow()

    errors: list[str] = []
    package = str(raw.get("package") or "").strip()
    if not package:
        errors.append("Thiếu `package` — không biết lái app nào.")

    raw_cases = raw.get("cases") or []
    if not isinstance(raw_cases, list):
        raise FlowError("`cases` phải là một danh sách.")

    cases: list[FlowCase] = []
    for order, raw_case in enumerate(raw_cases, start=1):
        case, case_errors = _case(raw_case, order)
        errors += case_errors
        if case is not None:
            cases.append(case)

    if not cases and not errors:
        errors.append("Không có case nào để chạy.")
    return Flow(package=package, cases=tuple(cases), errors=tuple(errors))


def load(path: Path | str) -> Flow:
    """Doc file flow. Khong co file / sai cu phap -> FlowError."""
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise FlowError(f"Không đọc được {path}: {exc}") from exc
    try:
        raw = yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        raise FlowError(f"{path.name} sai cú pháp YAML:\n{exc}") from exc
    return parse(raw)
