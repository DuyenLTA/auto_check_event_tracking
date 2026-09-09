"""Trang thai mot phien lam viec: spec da nap, phien ghi, ket qua da cham.

Mot phien mot luc - tool chay localhost cho MOT tester, khong phai server nhieu
nguoi. Giu don gian: mot bien module, co reset() cho test.

Vi sao co `stage`: UI can biet dang o buoc nao de bat/tat nut. Suy tu cac field
khac cung duoc nhung se rai rac o ca client lan server, roi hai ben lech nhau.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from .check_models import CheckResult, Summary
from .event_spec_models import SpecSheet
from .event_window import Window
from .logcat_stream import Recording


def now_vn() -> str:
    """Gio Viet Nam - tester doc report la biet ngay chay luc nao."""
    return datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M")


@dataclass(slots=True)
class EventRun:
    """Ket qua mot lan cham."""

    results: list[CheckResult]
    summary: Summary
    spec: SpecSheet
    package: str = ""
    generated_at: str = ""
    fa_silent: bool = False
    # Phien ghi bi dut giua duong -> bao cao phai noi ra, xem report_event_html.
    stream_died: bool = False
    near_edge: tuple[str, ...] = ()
    event_count: int = 0
    quick: bool = False


@dataclass(slots=True)
class State:
    spec: SpecSheet | None = None
    recording: Recording | None = None
    windows: tuple[Window, ...] = ()
    run: EventRun | None = None
    serial: str = ""
    package: str = ""
    quick: bool = False

    @property
    def stage(self) -> str:
        """Buoc hien tai, cho UI bat/tat nut."""
        if self.spec is None or not self.spec.ok:
            return "need_spec"
        if self.recording is None:
            return "ready_to_record"
        if not self.recording.stopped:
            return "recording"
        if self.run is None:
            return "ready_to_check"
        return "done"

    def reset(self) -> None:
        self.spec = None
        self.recording = None
        self.windows = ()
        self.run = None
        self.serial = ""
        self.package = ""
        self.quick = False

    def payload(self) -> dict:
        return {
            "stage": self.stage,
            "quick": self.quick,
            "serial": self.serial,
            "package": self.package,
            "spec": self.spec.payload() if self.spec else None,
            "recording": self.recording.payload() if self.recording else None,
            "window_count": len(self.windows),
            "summary": self.run.summary.payload() if self.run else None,
        }


state = State()
