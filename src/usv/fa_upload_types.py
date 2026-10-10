"""Kieu THAT cua tung param, doc tu payload upload cua Firebase trong logcat.

Dong `Logging event` in Long 3 va String "3" y het nhau (`style_id=100111`), nen
chi nhin dong do thi spec String ma app gui so la khong ket luan duoc. Nhung khi
bat log.tag.FA-SVC=VERBOSE, luc gui batch len server Firebase in ca proto:

    10-02 10:07:19.251  5727 13976 V FA-SVC  :     event {
    10-02 10:07:19.251  5727 13976 V FA-SVC  :       name: style_click
    10-02 10:07:19.251  5727 13976 V FA-SVC  :       param {
    10-02 10:07:19.251  5727 13976 V FA-SVC  :         name: style_id
    10-02 10:07:19.251  5727 13976 V FA-SVC  :         int_value: 100111
    10-02 10:07:19.251  5727 13976 V FA-SVC  :       }

`string_value` / `int_value` / `double_value` chinh la kieu ma server nhan. Do
that tren AIP922 3.5.0 (SDK 181006), 01/10/2026.

Batch gui TRE (vai phut sau luc ban), co the khong kip vao phien ghi: khi do
event khong co kieu -> van NOT_VERIFIABLE nhu cu, khong doan.
"""

from __future__ import annotations

import re
from dataclasses import replace

# Noi dung sau tag FA-SVC, ca dinh dang `-v threadtime` lan `-v time`.
_SVC_BODY = re.compile(r"FA-SVC\s*(?:\(\s*\d+\s*\))?\s*:\s?(?P<body>.*)$")
_SHORT = re.compile(r"\(.*\)$")
_VALUE = re.compile(r"^(?P<kind>string|int|double)_value:\s?(?P<value>.*)$")

KIND_STRING = "string"


def parse_upload_events(text: str) -> list[tuple[str, dict[str, tuple[str, str]]]]:
    """Moi `event {...}` trong batch upload -> (ten, {param: (kieu, gia tri)}).

    Doc theo DO SAU ngoac: batch con `user_property {}`, `bundle {}` long nhau,
    chi `name:` ngay trong `event {` moi la ten event.
    """
    out: list[tuple[str, dict[str, tuple[str, str]]]] = []
    stack: list[str] = []               # loai khoi dang mo, trong cung la cuoi
    name = ""
    params: dict[str, tuple[str, str]] = {}
    param_name = ""
    for line in text.splitlines():
        match = _SVC_BODY.search(line)
        if match is None:
            continue
        body = match.group("body").strip()
        if body.endswith("{"):
            kind = body[:-1].strip()
            stack.append(kind)
            if kind == "event":
                name, params = "", {}
            elif kind == "param":
                param_name = ""
            continue
        if body == "}":
            if not stack:
                continue
            closed = stack.pop()
            if closed == "event" and name:
                out.append((name, params))
            continue
        if not stack:
            continue
        if stack[-1] == "event" and body.startswith("name:"):
            name = _SHORT.sub("", body[5:].strip())
        elif stack[-1] == "param" and "event" in stack:
            if body.startswith("name:"):
                param_name = _SHORT.sub("", body[5:].strip())
            else:
                value = _VALUE.match(body)
                if value and param_name:
                    params[param_name] = (value.group("kind"), value.group("value").strip())
    return out


def annotate(events: list, text: str) -> list:
    """Gan `param_types` cho event app ban, ghep voi khoi upload CUNG TEN va
    CUNG GIA TRI moi param. Moi khoi upload chi ghep mot lan, theo thu tu.

    Ghep theo gia tri chu khong theo gio: proto upload chi co
    `timestamp_millis` theo epoch, con dong log co gio may khong nam - doi qua
    lai de sai lech mui gio ma khong them gi chac hon.
    """
    uploads = parse_upload_events(text)
    if not uploads:
        return events
    used: set[int] = set()
    out = []
    for event in events:
        types = _match(event, uploads, used) if event.from_app and not event.truncated else None
        out.append(replace(event, param_types=types) if types else event)
    return out


def _match(event, uploads, used: set[int]) -> dict[str, str] | None:
    for index, (name, params) in enumerate(uploads):
        if index in used or name != event.name:
            continue
        if all(key in params and params[key][1] == value
               for key, value in event.params.items()):
            used.add(index)
            return {key: kind for key, (kind, _) in params.items()}
    return None
