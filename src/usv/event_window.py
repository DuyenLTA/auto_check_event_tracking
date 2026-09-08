"""Cat timeline log thanh cac CUA SO theo moc USV_MARK.

MOT nut mot buoc: moc cua buoc sau chinh la diem ket cua buoc truoc. Spec 40-60
event thi cach nay tiet kiem mot nua so lan bam ma khong mat thong tin gi.

Vi sao cat theo moc trong LOG chu khong theo gio host: dong USV_MARK nam chung
timeline voi event nen khong phai dong bo clock host/device. Da verify tren may.

R4 - event ban sat luc bam moc: KHONG tu doi cua so cho no (doan la sai), ma gan
co `near_edge` de report noi ra, tester tu phan.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .fa_event_parse import Marker, ObservedEvent, parse_log

# Nhan moc: "<ten event spec> | <van xuoi cot Triggered>".
_SEP = " | "
# Event cach bien duoi nguong nay -> ghi chu "sat bien". 250ms la SO DOAN, chua
# do tren phien that; giu nho de it gan co oan, va bao ra chu khong tu xu ly.
EDGE_MS = 250.0
_TS = re.compile(r"^(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})\.(\d{3})$")


def mark_label(spec_event: str, note: str = "") -> str:
    """Nhan de chen vao logcat. Ghep de mot dong log noi du ca hai."""
    return f"{spec_event}{_SEP}{note}" if note else spec_event


def split_label(label: str) -> tuple[str, str]:
    spec_event, _, note = (label or "").partition(_SEP)
    return spec_event.strip(), note.strip()


def to_ms(timestamp: str) -> float | None:
    """'09-08 15:40:26.202' -> mili-giay trong nam. So sanh va tru duoc.

    Khong dung datetime: log khong co nam, va ta chi can HIEU giua hai moc trong
    cung mot phien ghi (vai phut).
    """
    match = _TS.match((timestamp or "").strip())
    if not match:
        return None
    month, day, hour, minute, second, milli = (int(g) for g in match.groups())
    return ((((month * 31 + day) * 24 + hour) * 60 + minute) * 60 + second) * 1000.0 + milli


@dataclass(frozen=True, slots=True)
class Window:
    """Mot buoc: tu luc bam moc den luc bam moc sau (hoac Dung ghi)."""

    spec_event: str
    note: str = ""
    events: tuple[ObservedEvent, ...] = ()
    start_ms: float | None = None
    end_ms: float | None = None
    near_edge: tuple[str, ...] = ()   # ten event nam sat bien cua so

    def named(self, name: str) -> tuple[ObservedEvent, ...]:
        return tuple(e for e in self.events if e.name == name and e.from_app)

    @property
    def app_events(self) -> tuple[ObservedEvent, ...]:
        return tuple(e for e in self.events if e.from_app)

    def payload(self) -> dict:
        return {"spec_event": self.spec_event, "note": self.note,
                "event_count": len(self.events),
                "events": [e.payload() for e in self.events],
                "near_edge": list(self.near_edge)}


def _edge_names(events: list[ObservedEvent], start: float | None,
                end: float | None) -> tuple[str, ...]:
    out = []
    for event in events:
        stamp = to_ms(event.timestamp)
        if stamp is None:
            continue
        if start is not None and abs(stamp - start) <= EDGE_MS:
            out.append(event.name)
        elif end is not None and abs(end - stamp) <= EDGE_MS:
            out.append(event.name)
    return tuple(dict.fromkeys(out))


def cut(events: list[ObservedEvent], markers: list[Marker]) -> tuple[Window, ...]:
    """Cat theo moc. Event truoc moc dau tien bi bo - chua bat dau buoc nao."""
    if not markers:
        return ()

    bounds: list[tuple[Marker, float | None, float | None]] = []
    stamps = [to_ms(m.timestamp) for m in markers]
    for i, marker in enumerate(markers):
        start = stamps[i]
        end = stamps[i + 1] if i + 1 < len(stamps) else None
        bounds.append((marker, start, end))

    windows: list[Window] = []
    for marker, start, end in bounds:
        inside = []
        for event in events:
            stamp = to_ms(event.timestamp)
            if stamp is None or start is None:
                continue
            if stamp < start:
                continue
            if end is not None and stamp >= end:
                continue
            inside.append(event)
        spec_event, note = split_label(marker.label)
        windows.append(Window(
            spec_event=spec_event, note=note, events=tuple(inside),
            start_ms=start, end_ms=end, near_edge=_edge_names(inside, start, end),
        ))
    return tuple(windows)


def cut_log(text: str) -> tuple[Window, ...]:
    events, markers = parse_log(text)
    return cut(events, markers)
