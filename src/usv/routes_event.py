"""Route tang event: nap spec, ghi logcat, danh dau tung buoc, cham check.

MOT NUT MOT BUOC: moc cua buoc sau chinh la diem ket cua buoc truoc. Spec 40-60
event thi cach nay tiet kiem mot nua so lan bam ma khong mat thong tin gi.

KHONG cho Ghi khi spec con loi: spec sai thi bao cao sai, va sai am tham. Xem
event_spec_parse ve chuyen gop dong lam mat o rong.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from . import event_check_runner, logcat_stream
from .adb_parsers import AdbError
from .check_config import ConfigError, load as load_config
from .event_spec_parse import parse_paste
from .event_state import EventRun, now_vn, state
from .event_window import cut, mark_label, whole_session
from .fa_event_parse import parse_log
from .routes_device import client

log = logging.getLogger(__name__)
router = APIRouter()


class SpecRequest(BaseModel):
    text: str = Field(default="", max_length=2_000_000)


class RecordRequest(BaseModel):
    serial: str
    package: str
    from_launch: bool = True
    # Che do NHANH: khong danh dau tung buoc, tester bam Ghi roi thao tac tu do.
    # Danh doi: khong biet event ban dung luc hay khong. Xem event_window.whole_session.
    quick: bool = False


class MarkRequest(BaseModel):
    spec_event: str
    note: str = ""


@router.get("/event/state")
async def read_state() -> dict:
    """Trang thai hien tai. Tra rong thay vi loi khi chua nap gi - goi de hoi
    trang thai la binh thuong."""
    return state.payload()


@router.get("/event/config")
async def read_config() -> dict:
    """Doc lai file config MOI LAN goi -> tester sua YAML la co hieu luc ngay."""
    try:
        return load_config().payload()
    except ConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/event/spec")
async def load_spec(request: SpecRequest) -> dict:
    """Dan bang spec -> parse -> tra ca events LAN errors cho bang preview.

    Tra 200 ke ca khi co loi: spec sai la loi DU LIEU cua tester, khong phai
    loi server. Tester can thay dong nao sai de sua, chu khong phai mot cai 400
    khong noi gi.
    """
    sheet = parse_paste(request.text)
    state.spec = sheet
    state.run = None
    state.windows = ()
    return {"stage": state.stage, **sheet.payload()}


@router.post("/event/record")
async def start_record(request: RecordRequest) -> dict:
    if state.spec is None or not state.spec.ok:
        raise HTTPException(
            status_code=409,
            detail="Spec chua hop le - sua het loi o bang preview roi mới Ghi được.")
    if state.recording is not None and not state.recording.stopped:
        raise HTTPException(status_code=409, detail="Đang ghi rồi.")

    adb = client()
    try:
        recording = await logcat_stream.start(
            adb, request.serial, request.package, from_launch=request.from_launch)
    except AdbError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    state.recording = recording
    state.serial, state.package = request.serial, request.package
    state.quick = request.quick
    state.run, state.windows = None, ()
    return {"stage": state.stage, "quick": state.quick,
            "recording": recording.payload()}


@router.post("/event/mark")
async def add_mark(request: MarkRequest) -> dict:
    recording = state.recording
    if recording is None or recording.stopped:
        raise HTTPException(status_code=409, detail="Chưa bắt đầu ghi.")
    if state.spec is None or state.spec.event(request.spec_event) is None:
        raise HTTPException(
            status_code=400,
            detail=f"Spec không có event {request.spec_event!r}.")

    adb = client()
    try:
        await logcat_stream.mark(
            adb, recording, mark_label(request.spec_event, request.note))
    except AdbError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"stage": state.stage, "marks": list(recording.marks)}


@router.post("/event/stop")
async def stop_record() -> dict:
    recording = state.recording
    if recording is None:
        raise HTTPException(status_code=409, detail="Chưa bắt đầu ghi.")
    if not recording.stopped:
        await logcat_stream.stop(recording)

    events, markers = parse_log(recording.text())
    if state.quick:
        # Khong co moc -> cat theo moc se ra 0 cua so va MOI dong thanh
        # "chua test". Che do nhanh gom ca phien thanh mot cua so cho tung event.
        app_events = [e for e in events if e.from_app]
        state.windows = whole_session(
            tuple(e.name for e in (state.spec.events if state.spec else ())),
            app_events)
    else:
        state.windows = cut(events, markers)
    return {
        "stage": state.stage,
        "quick": state.quick,
        "recording": recording.payload(),
        "window_count": len(state.windows),
        "event_count": len(events),
        "marker_count": len(markers),
    }


@router.post("/event/check")
async def run_check() -> dict:
    if state.spec is None or not state.spec.ok:
        raise HTTPException(status_code=409, detail="Chưa nạp spec hợp lệ.")
    recording = state.recording
    if recording is None or not recording.stopped:
        raise HTTPException(status_code=409, detail="Chưa Dừng ghi.")

    try:
        config = load_config()
    except ConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if state.quick:
        # Mot phien dai vao ra cung mot man thi event do ban lai - dung, khong
        # phai loi. Bat `duplicate` o che do nay la bao oan hang loat.
        config = config.with_option("event_presence", "duplicate", False)

    fa_silent = recording.fa_silent
    stream_died = recording.stream_died
    results, summary = event_check_runner.run(
        state.spec, state.windows, config, fa_silent=fa_silent,
        stream_died=stream_died)
    events, _ = parse_log(recording.text())

    state.run = EventRun(
        results=results, summary=summary, spec=state.spec, package=state.package,
        generated_at=now_vn(), fa_silent=fa_silent, stream_died=stream_died,
        near_edge=tuple(dict.fromkeys(n for w in state.windows for n in w.near_edge)),
        event_count=len(events), quick=state.quick,
    )
    return {
        "stage": state.stage,
        "quick": state.quick,
        "summary": summary.payload(),
        "fa_silent": fa_silent,
        "stream_died": stream_died,
        "near_edge": list(state.run.near_edge),
        "config": config.payload(),
        "results": [r.payload() for r in results],
    }


@router.post("/event/reset")
async def reset() -> dict:
    """Bo het de lam lai. Kill process logcat neu con dang chay."""
    recording = state.recording
    if recording is not None and not recording.stopped:
        await logcat_stream.stop(recording)
    state.reset()
    return state.payload()
