"""Sua noi dung file Remote Config - THUAN VAN BAN, khong I/O.

Tach ra de test duoc ma khong can may. Phan chay adb nam o remote_config.py.

Hai file, PHAI SUA CA HAI:
  files/frc_<appId>_firebase_activate.json    gia tri
  shared_prefs/frc_<appId>_firebase_settings.xml   moc throttle

Chi sua file gia tri thi lan mo app sau app fetch that va DE MAT SACH. Da do:
196 key bi ghi de thanh 200 key. Don bay dung la throttle 12h cua SDK - dat
`fetch_time_key` va `last_fetch_time_in_millis` = bay gio thi SDK coi nhu vua
fetch xong nen khong fetch nua, va patch song qua lan mo app.

KHONG cat mang de chan fetch: app can mang cho ads/API/analytics, cat la fail oan.

Gia tri trong `configs_key` LUON la string, ke ca voi key kieu boolean/so.
"""

from __future__ import annotations

import json
import re

CONFIGS_KEY = "configs_key"
FETCH_TIME_KEY = "fetch_time_key"
THROTTLE_KEY = "last_fetch_time_in_millis"


def patch_activate_json(text: str, values: dict[str, str], now_ms: int) -> str:
    """Dat gia tri moi + day moc fetch len bay gio.

    File chua co (chuoi rong) van dung duoc: tao moi voi dung nhung key can.
    """
    try:
        data = json.loads(text) if text.strip() else {}
    except json.JSONDecodeError as exc:
        raise ValueError(f"frc activate json không đọc được: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("frc activate json phải là một object.")

    configs = data.get(CONFIGS_KEY)
    if not isinstance(configs, dict):
        configs = {}
    for key, value in values.items():
        configs[key] = str(value)      # SDK luu moi gia tri duoi dang string
    data[CONFIGS_KEY] = configs
    data[FETCH_TIME_KEY] = int(now_ms)
    return json.dumps(data, ensure_ascii=False)


def patch_throttle_xml(text: str, now_ms: int) -> str:
    """Dat `last_fetch_time_in_millis` = bay gio de SDK khong fetch lai."""
    return _set_long(text, THROTTLE_KEY, int(now_ms))


# <boolean name="k" value="true" />  |  <long name="k" value="1" />
_ATTR = r'<(?P<tag>boolean|long|int|float)\s+name="{key}"\s+value="(?P<val>[^"]*)"\s*/>'
# <string name="k">val</string>
_TEXT = r'<(?P<tag>string)\s+name="{key}"\s*>(?P<val>.*?)</string>'


def _set_long(text: str, key: str, value: int) -> str:
    pattern = re.compile(_ATTR.format(key=re.escape(key)))
    replacement = f'<long name="{key}" value="{value}" />'
    if pattern.search(text):
        return pattern.sub(replacement, text, count=1)
    return _append_entry(text, replacement)


def _append_entry(text: str, entry: str) -> str:
    """Chen mot dong vao truoc </map>. File chua co thi tao khung moi."""
    if "</map>" in text:
        return text.replace("</map>", f"    {entry}\n</map>", 1)
    return ("<?xml version='1.0' encoding='utf-8' standalone='yes' ?>\n"
            f"<map>\n    {entry}\n</map>\n")


def _as_bool(value: str) -> str:
    return "true" if str(value).strip().lower() in {"true", "1", "yes"} else "false"


def patch_prefs_xml(text: str, values: dict[str, str]) -> tuple[str, set[str]]:
    """Sua cac key CO SAN trong file prefs, GIU NGUYEN kieu XML.

    Tra (noi dung moi, cac key that su doi). Chi sua key da co: SDK Apero mirror
    RC sang prefs rieng voi TEN KEY Y HET, nhung moi app mirror mot tap khac
    nhau. Them key moi vao la doan - app khong doc key no khong biet, va con lam
    file khac han ban goc.
    """
    changed: set[str] = set()
    out = text
    for key, raw in values.items():
        escaped = re.escape(key)

        attr = re.compile(_ATTR.format(key=escaped))
        match = attr.search(out)
        if match:
            tag = match.group("tag")
            value = _as_bool(raw) if tag == "boolean" else str(raw)
            out = attr.sub(f'<{tag} name="{key}" value="{value}" />', out, count=1)
            changed.add(key)
            continue

        text_tag = re.compile(_TEXT.format(key=escaped), re.S)
        if text_tag.search(out):
            out = text_tag.sub(f'<string name="{key}">{raw}</string>', out, count=1)
            changed.add(key)
    return out, changed


def read_configs(text: str) -> dict[str, str]:
    """Doc lai gia tri tu activate json - dung de verify sau khi mo lai app."""
    try:
        data = json.loads(text) if text.strip() else {}
    except json.JSONDecodeError:
        return {}
    configs = data.get(CONFIGS_KEY)
    return {str(k): str(v) for k, v in configs.items()} if isinstance(configs, dict) else {}


def prefs_value(text: str, key: str) -> str | None:
    """Gia tri mot key trong prefs XML, None neu khong co."""
    escaped = re.escape(key)
    match = re.search(_ATTR.format(key=escaped), text)
    if match:
        return match.group("val")
    match = re.search(_TEXT.format(key=escaped), text, re.S)
    return match.group("val") if match else None
