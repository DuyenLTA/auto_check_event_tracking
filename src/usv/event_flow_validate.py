"""Kiem du lieu YAML tho: khoa la, chuoi, thoi gian, index.

Tach rieng vi hai file kia deu dung: `event_flow_parse` kiem cap case/reset,
`event_flow_step_parse` kiem cap step. De o mot cho thi them mot kieu kiem la
ap dung duoc cho ca hai, khong phai sua hai noi.
"""

from __future__ import annotations

import re

_DURATION = re.compile(r"^\s*([0-9]*\.?[0-9]+)\s*(ms|s)?\s*$", re.IGNORECASE)


def unknown_keys(raw: dict, allowed: set[str], where: str, errors: list[str]) -> None:
    """Khoa la -> bao. Im lang bo qua thi tester khong biet minh go sai."""
    extra = sorted(set(raw) - allowed)
    if extra:
        errors.append(f"{where}: khóa lạ {extra}. Chỉ có: {', '.join(sorted(allowed))}.")


def text_value(raw, field: str, where: str, errors: list[str]) -> str | None:
    """YAML -> chuoi. bool thi BAO LOI chu khong tu doi.

    `true` khong nhay ra Python True, `str(True)` = 'True' - lech voi 'true' ma
    may giu. Doi ngam thanh 'true' la phai DOAN app luu bool kieu gi: Firebase
    Remote Config luu chuoi, con logcat in bool param thanh so. Chua do nen
    khong doan - bat go nhay de tester noi ro y minh.
    """
    if isinstance(raw, bool):
        errors.append(f"{where}: {field} nhận bool {raw!r}. Bỏ trong nháy để nói rõ "
                      f"là chuỗi: \"{str(raw).lower()}\".")
        return None
    return str(raw if raw is not None else "").strip()


def duration(raw, where: str, errors: list[str], default: float = 0.0) -> float:
    """'2s' · '500ms' · 2 · 2.5 -> giay. Khong hieu thi bao, khong im lang lay mac dinh."""
    if isinstance(raw, bool):
        errors.append(f"{where}: thời gian không nhận bool.")
        return default
    if isinstance(raw, (int, float)):
        value = float(raw)
    else:
        match = _DURATION.match(str(raw or ""))
        if not match:
            errors.append(f"{where}: không đọc được thời gian {raw!r}. Vd: 2s, 500ms, 1.5")
            return default
        value = float(match.group(1))
        if (match.group(2) or "s").lower() == "ms":
            value /= 1000.0
    if value < 0:
        errors.append(f"{where}: thời gian âm ({value:g}s). Chờ âm là không chờ gì cả.")
        return default
    return value


def index_value(arg: dict, where: str, errors: list[str]) -> int:
    raw = arg.get("index", 0)
    # bool la int trong Python: `index: true` se lot neu chi kiem isinstance int.
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0:
        errors.append(f"{where}: index phải là số nguyên >= 0, nhận được {raw!r}.")
        return 0
    return raw
