"""Mot dong logcat -> ObservedEvent hoac Marker.

Dinh dang do duoc that tren AIP922 (SDK 181006):

    09-08 15:40:26.202 V/FA-SVC ( 9320): Logging event: origin=app,
        name=rating_placement_viewed,
        params=Bundle[{placement_name=home, ga_event_origin(_o)=app,
                       ga_screen_class(_sc)=AIP922...Activity}]

Ba diem da do, dung doan lai:

1. Event nam o tag `FA-SVC`, 67/67. Tag `FA` chi in `Logging telemetry for
   logEvent from database` - dung so lan nhung KHONG kem params. Van nhan dang
   `Logging event (FE):` cua tag FA de ben qua version SDK khac, roi dedupe.

2. `origin` la truong hang nhat: `app` 42 (app tu goi - pham vi spec),
   `auto` 8 (screen_view, session_start, user_engagement), `am` 17 (ad_query).
   Phan loai bang ORIGIN chu khong bang danh sach ten event -> ben hon nhieu.

3. Param KHONG duoc tach bang `split(", ")`. Gia tri chuoi chua dau phay se vo.
   Do that: `ump_request_failed.error_msg` dai 513 B chua `:`, `;`, backtick,
   dau cham. Dung lookahead: chi cat o `, ` nao DUNG TRUOC mot `key=`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .event_system_params import strip_system

# `Logging event: origin=app,name=X,params=Bundle[{...}]` (FA-SVC)
# hoac `Logging event (FE): X, Bundle[{...}]` (tag FA o mot so version SDK)
_SVC = re.compile(
    r"Logging event: origin=(?P<origin>\w+),name=(?P<name>[^,]+),"
    r"params=Bundle\[\{(?P<body>.*)\}\]\s*$")
_FE = re.compile(r"Logging event \(FE\): (?P<name>[^,]+), Bundle\[\{(?P<body>.*)\}\]\s*$")
# Dong bi logcat cat: mo Bundle ma khong dong.
_OPEN_BUNDLE = re.compile(r"params=Bundle\[\{|Bundle\[\{")
_MARKER = re.compile(r"/USV_MARK\s*\(\s*\d+\s*\):\s*(?P<label>.*?)\s*$")
_TIME = re.compile(r"^(?P<ts>\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})")
# Cat `, ` chi khi phia sau la mot `key=` -> gia tri chua dau phay khong bi vo.
_SPLIT = re.compile(r",\s+(?=[A-Za-z_][\w.]*(?:\([^)]*\))?=)")
# Bo hau to ngoac: `session_start(_s)` -> `session_start`, `ga_screen_class(_sc)`.
_SHORT = re.compile(r"\(.*\)$")

ORIGIN_APP = "app"


@dataclass(frozen=True, slots=True)
class ObservedEvent:
    """Mot event app that ban ra."""

    name: str
    origin: str
    params: dict[str, str]          # da bo param he thong
    raw_params: dict[str, str]      # con nguyen, de chan doan
    timestamp: str = ""
    truncated: bool = False

    @property
    def from_app(self) -> bool:
        """`origin=app` = app tu goi logEvent -> pham vi spec doi chieu."""
        return self.origin == ORIGIN_APP

    @property
    def screen_class(self) -> str:
        """Activity dang hien, Firebase gan san. Dung cho cot Screen Name."""
        for key in ("ga_screen_class", "firebase_screen_class"):
            if key in self.raw_params:
                return self.raw_params[key]
        return ""

    def payload(self) -> dict:
        return {"name": self.name, "origin": self.origin, "params": self.params,
                "timestamp": self.timestamp, "truncated": self.truncated,
                "screen_class": self.screen_class}


@dataclass(frozen=True, slots=True)
class Marker:
    """Moc tester/script chen vao logcat de cat cua so."""

    label: str
    timestamp: str = ""


def _timestamp(line: str) -> str:
    match = _TIME.match(line)
    return match.group("ts") if match else ""


def parse_params(body: str) -> dict[str, str]:
    out: dict[str, str] = {}
    if not body.strip():
        return out
    for part in _SPLIT.split(body):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        out[_SHORT.sub("", key.strip())] = value
    return out


def parse_line(line: str) -> ObservedEvent | Marker | None:
    marker = _MARKER.search(line)
    if marker:
        return Marker(label=marker.group("label"), timestamp=_timestamp(line))

    match = _SVC.search(line)
    origin = match.group("origin") if match else ORIGIN_APP
    if match is None:
        match = _FE.search(line)
    if match is None:
        # Mo Bundle ma khong dong -> logcat cat mat duoi (tran payload 4068 B).
        # Tra ve event co co `truncated` thay vi None: neu bo im lang thi check
        # se bao "thieu param" cho mot dong that ra co du param.
        if _OPEN_BUNDLE.search(line) and "Logging event" in line:
            name = _event_name_of_truncated(line)
            if name:
                return ObservedEvent(name=name, origin=origin, params={},
                                     raw_params={}, timestamp=_timestamp(line),
                                     truncated=True)
        return None

    raw = parse_params(match.group("body"))
    return ObservedEvent(
        name=_SHORT.sub("", match.group("name").strip()),
        origin=origin, params=strip_system(raw), raw_params=raw,
        timestamp=_timestamp(line),
    )


def _event_name_of_truncated(line: str) -> str:
    match = re.search(r"name=([^,]+)", line)
    return _SHORT.sub("", match.group(1).strip()) if match else ""


def parse_log(text: str) -> tuple[list[ObservedEvent], list[Marker]]:
    """Ca file log -> event + marker, da dedupe.

    Dedupe theo (timestamp, name): tag `FA` va `FA-SVC` co the cung in mot event
    o version SDK khac. Khong dedupe thi MOI event bao "ban 2 lan".
    """
    events: list[ObservedEvent] = []
    markers: list[Marker] = []
    seen: set[tuple[str, str]] = set()
    for line in text.splitlines():
        item = parse_line(line)
        if isinstance(item, Marker):
            markers.append(item)
        elif isinstance(item, ObservedEvent):
            key = (item.timestamp, item.name)
            if key in seen:
                continue
            seen.add(key)
            events.append(item)
    return events, markers
