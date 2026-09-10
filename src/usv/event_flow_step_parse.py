"""Tu vung step: mot phan tu trong `steps` -> Step.

Tach khoi `event_flow_parse` vi hai viec khac nhau: file kia di cau truc
event/case, file nay dich MOT thao tac. Danh sach step con dai ra khi them thao
tac moi, con cau truc flow thi khong.

Nhan dien step la mot mapping MOT KHOA: `{tap_id: btnHome}`. Khoa la ten step,
gia tri la doi so - dang ngan nhat cho thu tester phai go tay nhieu nhat.

Tu choi cai khong hieu thay vi bo qua - ke ca MOT khoa la trong mot dict. Go
`indx` thay `index` ma im lang thi selector ve index 0, bam sang card khac, lai
sang man khac, event khong ban ra, roi bao FAIL oan cho app. Go sai mot chu ma
doc ra ket luan sai ve app la kieu that bai te nhat o day. Cung nguyen tac
`check_config`.
"""

from __future__ import annotations

from .adb_input import KEYEVENTS
from .device_actions import DIRECTIONS, Selector
from .event_flow_models import Step
from .event_flow_validate import duration, index_value, text_value, unknown_keys

# Step khong can doi so: viet `- back` tran, khong phai `- back: true`.
BARE = {"back": ("key", "BACK"), "home": ("key", "HOME"), "launch": ("launch", "")}
# Ten step -> truong cua Selector no dien vao.
TAPS = {"tap_id": "resource_id", "tap_text": "text", "tap_desc": "desc"}
# Truong cua Selector -> khoa YAML dat gia tri cho no.
NEEDLE_KEY = {"resource_id": "id", "text": "text", "desc": "desc"}


def allowed_steps() -> str:
    names = sorted(set(TAPS) | set(BARE) | {"swipe", "wait", "wait_text", "key", "type"})
    return "Chỉ có: " + ", ".join(names) + "."


def selector(arg, field: str, where: str, errors: list[str],
             extra_keys: set[str] = frozenset()) -> Selector | None:
    """Chap `tap_id: btnHome` va dang co index `{id: x, index: 2}`.

    Can index vi resource_id mot minh khong khoa duoc node: da gap GridView 4
    card dung chung mot resource_id. Xem docstring Selector.

    Khai hai khoa tim kiem cung luc thi BAO LOI chu khong chon ngam mot cai -
    chon ngam la bam vao node tester khong he y.
    """
    if not isinstance(arg, dict):
        needle = text_value(arg, "selector", where, errors)
        return Selector(**{field: needle}) if needle else _missing(where, errors)

    key = NEEDLE_KEY[field]
    unknown_keys(arg, {key, "index"} | extra_keys, where, errors)
    clash = sorted(set(NEEDLE_KEY.values()) & set(arg) - {key})
    if clash:
        errors.append(f"{where}: khai cả {key!r} lẫn {clash} - chọn một cái.")
        return None
    needle = text_value(arg.get(key), key, where, errors)
    if not needle:
        return _missing(where, errors)
    return Selector(**{field: needle}, index=index_value(arg, where, errors))


def _missing(where: str, errors: list[str]) -> None:
    errors.append(f"{where}: thiếu giá trị để tìm node.")
    return None


def _swipe(arg, where: str, errors: list[str]) -> Step | None:
    if not isinstance(arg, dict):
        arg = {"id": arg}
    given = sorted(set(NEEDLE_KEY.values()) & set(arg))
    if len(given) > 1:
        errors.append(f"{where}: khai nhiều khóa tìm kiếm {given} - chọn một cái.")
        return None
    field = next((f for f, k in NEEDLE_KEY.items() if k in arg), "resource_id")
    direction = text_value(arg.get("dir") or arg.get("direction") or "up",
                           "dir", where, errors)
    if direction is None:
        return None
    if direction.lower() not in DIRECTIONS:
        errors.append(f"{where}: hướng {direction!r} không hiểu. "
                      f"Chỉ có: {', '.join(DIRECTIONS)}.")
        return None
    found = selector(arg, field, where, errors, extra_keys={"dir", "direction"})
    return Step(kind="swipe", selector=found, text=direction.lower()) if found else None


def _wait_text(arg, where: str, errors: list[str]) -> Step | None:
    if not isinstance(arg, dict):
        arg = {"text": arg}
    unknown_keys(arg, {"text", "timeout"}, where, errors)
    text = text_value(arg.get("text"), "text", where, errors)
    if not text:
        errors.append(f"{where}: thiếu chữ cần chờ.")
        return None
    return Step(kind="wait_text", text=text,
                timeout=duration(arg.get("timeout", 10.0), where, errors, default=10.0))


def _key(arg, where: str, errors: list[str]) -> Step | None:
    """Kiem whitelist NGAY LUC PARSE, khong doi den luc chay.

    Doi den luc chay thi case da reset Remote Config, xoa prefs, force-stop va
    mo lai app, chen moc - roi moi bao `not_tested` vi mot chu go sai. Mat ca
    mot chu ky chay may cho thu bat duoc luc doc file.
    """
    name = text_value(arg, "key", where, errors)
    if not name:
        errors.append(f"{where}: thiếu tên phím.")
        return None
    if name.upper() not in KEYEVENTS:
        errors.append(f"{where}: phím {name!r} không được phép. "
                      f"Chỉ có: {', '.join(sorted(KEYEVENTS))}.")
        return None
    return Step(kind="key", text=name.upper())


def parse_step(raw, where: str, errors: list[str]) -> Step | None:
    """Khong hieu -> bao kem danh sach cho phep, khong doan y."""
    if isinstance(raw, str):
        name = raw.strip()
        if name in BARE:
            kind, text = BARE[name]
            return Step(kind=kind, text=text)
        errors.append(f"{where}: step {raw!r} không hiểu. {allowed_steps()}")
        return None
    if not isinstance(raw, dict) or len(raw) != 1:
        errors.append(f"{where}: một step phải là một khóa duy nhất, vd `- tap_id: btnHome`. "
                      f"Nhận được {raw!r}.")
        return None

    (name, arg), = raw.items()
    name = str(name).strip()
    spot = f"{where} step {name!r}"

    if name in TAPS:
        found = selector(arg, TAPS[name], spot, errors)
        return Step(kind="tap", selector=found) if found else None
    if name == "swipe":
        return _swipe(arg, spot, errors)
    if name == "wait":
        return Step(kind="wait", seconds=duration(arg, spot, errors))
    if name == "wait_text":
        return _wait_text(arg, spot, errors)
    if name == "key":
        return _key(arg, spot, errors)
    if name == "type":
        text = text_value(arg, "type", spot, errors)
        if not text:
            errors.append(f"{spot}: thiếu chữ cần gõ.")
            return None
        if "'" in text or '"' in text:
            # adb_input.input_text tu choi dau nhay - bat o day cho som.
            errors.append(f"{spot}: chuỗi gõ vào không được chứa dấu nháy.")
            return None
        return Step(kind="type", text=text)
    if name in BARE:
        # `launch: {package: x}` - package khai o cap flow, step khong nhan doi so.
        if arg not in (None, True):
            errors.append(f"{spot}: step này không nhận đối số ({arg!r}). "
                          f"Package khai ở cấp flow, không ở từng step.")
            return None
        kind, text = BARE[name]
        return Step(kind=kind, text=text)

    errors.append(f"{spot}: step không hiểu. {allowed_steps()}")
    return None
