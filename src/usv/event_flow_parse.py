"""Doc flow YAML -> Flow. Di cau truc event/case; tu vung step o
`event_flow_step_parse`.

Vi sao tra errors thay vi raise: flow sai la loi DU LIEU cua tester, giong bang
spec dan vao. Tester can thay het cho sai mot luot de sua, chu khong phai sua
mot cai roi chay lai de lo ra cai tiep theo. Cung ly do `event_spec_parse`.

Chap hai dang document. Dang co `package` de flow tu mang ten app:

    package: com.x.y
    events:
      - event: rating_placement_viewed
        cases:
          - params: {placement_name: home}
            steps: [...]

Va dang danh sach tran (khong co `package`, goi ham thi truyen vao).
"""

from __future__ import annotations

import yaml

from .adb_parsers import AdbError, check_package
from .event_flow_models import Flow, FlowCase, Reset
from .event_flow_step_parse import parse_step
from .event_flow_validate import text_value, unknown_keys

CASE_KEYS = {"name", "params", "reset", "steps"}
RESET_KEYS = {"remote_config", "clear_prefs", "relaunch"}


class _NoDuplicateLoader(yaml.SafeLoader):
    """Khoa trung trong mot mapping -> bao loi.

    yaml mac dinh lay cai sau, im lang. Khai `steps` hai lan thi case chay
    thieu buoc, event khong ban ra, roi bao FAIL oan cho app - dung kieu loi
    ma `parse_step` da chan o cap step, nen chan luon o cap mapping.
    """

    def construct_mapping(self, node, deep=False):
        seen = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in seen:
                raise yaml.constructor.ConstructorError(
                    None, None, f"khóa {key!r} khai hai lần", key_node.start_mark)
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


def _string_list(raw, where: str, field: str, errors: list[str]) -> tuple[str, ...]:
    """Mot chuoi hoac danh sach chuoi. Kieu khac thi bao, khong `tuple()` bua."""
    if isinstance(raw, str):
        return (raw,)
    if not isinstance(raw, list):
        errors.append(f"{where}: {field} phải là một chuỗi hoặc danh sách chuỗi, "
                      f"nhận được {raw!r}.")
        return ()
    out = tuple(text_value(item, field, where, errors) or "" for item in raw)
    return tuple(item for item in out if item)


def _reset(raw, where: str, errors: list[str]) -> Reset:
    """`pm clear` khong co o day - no xoa sach login. Xem docstring Reset."""
    if raw is None:
        return Reset()
    if not isinstance(raw, dict):
        errors.append(f"{where}: reset phải có khóa {sorted(RESET_KEYS)}. "
                      f"Nhận được {raw!r}.")
        return Reset()
    unknown_keys(raw, RESET_KEYS, f"{where} reset", errors)
    config = raw.get("remote_config") or {}
    if not isinstance(config, dict):
        errors.append(f"{where}: remote_config phải là cặp khóa-giá trị.")
        config = {}
    values = {}
    for key, value in config.items():
        text = text_value(value, f"remote_config[{key}]", where, errors)
        if text is not None:
            values[str(key)] = text
    return Reset(remote_config=values,
                 clear_prefs=_string_list(raw.get("clear_prefs") or (), where,
                                          "clear_prefs", errors),
                 relaunch=bool(raw.get("relaunch", True)))


def _params(raw, where: str, errors: list[str]) -> dict[str, str]:
    if not isinstance(raw, dict):
        errors.append(f"{where}: params phải là cặp khóa-giá trị, nhận được {raw!r}.")
        return {}
    out = {}
    for key, value in raw.items():
        text = text_value(value, f"params[{key}]", where, errors)
        if text is not None:
            out[str(key)] = text
    return out


def _steps(raw, where: str, errors: list[str]) -> tuple:
    if raw is None:
        errors.append(f"{where}: thiếu `steps` - case này không lái app đi đâu.")
        return ()
    if not isinstance(raw, list):
        errors.append(f"{where}: steps phải là một danh sách, nhận được {raw!r}.")
        return ()
    if not raw:
        errors.append(f"{where}: steps rỗng - case này không lái app đi đâu.")
        return ()
    parsed = [parse_step(item, where, errors) for item in raw]
    if any(step is None for step in parsed):
        # Bo CA case: chay mot case thieu buoc con te hon khong chay - no ra
        # ket luan ve app dua tren duong di khong phai duong tester mo ta.
        errors.append(f"{where}: có step không đọc được - bỏ cả case này.")
        return ()
    return tuple(parsed)


def _case(raw, event: str, position: int, errors: list[str]) -> FlowCase | None:
    where = f"event {event!r} case {position}"
    if not isinstance(raw, dict):
        errors.append(f"{where}: case phải là một mapping.")
        return None
    unknown_keys(raw, CASE_KEYS, where, errors)
    # Doc reset TRUOC khi bo case vi thieu step: bo som thi loi reset bi mat,
    # tester sua step roi chay lai moi lo ra - dung vong lap can tranh.
    reset = _reset(raw.get("reset"), where, errors)
    params = _params(raw.get("params") or {}, where, errors)
    name = text_value(raw.get("name"), "name", where, errors) or ""
    steps = _steps(raw.get("steps"), where, errors)
    if not steps:
        return None
    return FlowCase(event=event, name=name, expect_params=params,
                    steps=steps, reset=reset)


def _groups(document, package: str) -> tuple[list, str]:
    if isinstance(document, dict):
        package = str(document.get("package") or package).strip()
        return document.get("events") or [], package
    return document, package


def parse_flow(text: str, package: str = "") -> Flow:
    """YAML -> Flow. Loi cu gom vao `Flow.errors`, khong raise."""
    errors: list[str] = []
    try:
        document = yaml.load(text or "", Loader=_NoDuplicateLoader) or []
    except yaml.YAMLError as exc:
        return Flow(package=package, errors=(f"YAML sai cú pháp: {exc}",))

    groups, package = _groups(document, package)
    if package:
        try:
            check_package(package)
        except AdbError as exc:
            errors.append(str(exc))
    if not isinstance(groups, list):
        return Flow(package=package,
                    errors=("Flow phải là danh sách các event, mỗi event có `cases`.",))

    cases: list[FlowCase] = []
    labels: set[str] = set()
    for index, group in enumerate(groups, start=1):
        if not isinstance(group, dict):
            errors.append(f"Event thứ {index}: phải là mapping có `event` và `cases`.")
            continue
        unknown_keys(group, {"event", "cases"}, f"Event thứ {index}", errors)
        event = text_value(group.get("event"), "event", f"Event thứ {index}", errors)
        if not event:
            errors.append(f"Event thứ {index}: thiếu tên event.")
            continue
        raw_cases = group.get("cases")
        if not isinstance(raw_cases, list) or not raw_cases:
            errors.append(f"Event {event!r}: không có case nào.")
            continue
        for position, raw_case in enumerate(raw_cases, start=1):
            case = _case(raw_case, event, position, errors)
            if case is None:
                continue
            # `event_flow_run.expectations` khoa theo nhan: hai case cung nhan
            # thi mot cai de mat expectations cua cai kia.
            if case.label in labels:
                errors.append(f"event {event!r} case {position}: nhãn "
                              f"{case.label!r} trùng với case trước - đặt `name` "
                              f"khác nhau để phân biệt cửa sổ.")
                continue
            labels.add(case.label)
            cases.append(case)

    if not cases and not errors:
        errors.append("Flow rỗng - chưa khai case nào.")
    return Flow(package=package, cases=tuple(cases), errors=tuple(errors))
