"""Route tang event: nap spec, ghi logcat, danh dau tung buoc, cham check.

MOT NUT MOT BUOC: moc cua buoc sau chinh la diem ket cua buoc truoc. Spec 40-60
event thi cach nay tiet kiem mot nua so lan bam ma khong mat thong tin gi.

KHONG cho Ghi khi spec con loi: spec sai thi bao cao sai, va sai am tham. Xem
event_spec_parse ve chuyen gop dong lam mat o rong.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from . import logcat_stream
from .adb_parsers import AdbError
from .check_config import ConfigError, load as load_config
from .confluence_client import (ConfluenceError, ConfluenceLinkError,
                                fetch_page)
from .event_spec_confluence import parse_page
from .event_session import bo_phien_cu, co_the_tu_mo, lay_mau_app
from .event_spec_parse import parse_paste
from .event_state import state
from .event_window import mark_label, windows_for
from .fa_event_parse import parse_log
from .routes_device import client

router = APIRouter()


class SpecRequest(BaseModel):
    text: str = Field(default="", max_length=2_000_000)


class ConfluenceRequest(BaseModel):
    url: str = Field(default="", max_length=2000)


class RecordRequest(BaseModel):
    serial: str
    package: str
    # KHONG co `from_launch`. Luon ghi tu dau; tool tu mo app khi tim thay
    # package, khong thay thi de tester tu mo - xem co_the_tu_mo().
    # KHONG co tham so `quick`. Cham ca phien hay cat theo moc duoc SUY RA luc
    # Dung ghi, tu viec co moc hay khong - xem stop_record.


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
    await bo_phien_cu()
    state.spec = sheet
    return {"stage": state.stage, **sheet.payload()}


@router.post("/event/spec/confluence")
async def load_spec_confluence(request: ConfluenceRequest) -> dict:
    """Nap spec THANG tu link Confluence.

    Hon han duong dan TSV o mot cho khong the vuot qua bang cach dan: bang
    that dung `rowspan`, hang thu hai cua mot event chi co 2 o trong khi bang
    rong 8 cot. Ranh gioi o lay tu luoi HTML thi chuyen do bien mat; dem o
    theo dau tab thi khong.

    Loi mang/token tra 502 (loi HE THONG, khong phai loi cua tester), con bang
    doc duoc ma sai thi tra 200 kem `errors` - giong duong dan dan tay.
    """
    try:
        title, html = fetch_page(request.url)
    except ConfluenceLinkError as exc:
        # Link go sai la loi cua nguoi dung -> 400, dung bao nhu su co mang.
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ConfluenceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    sheet = parse_page(html)
    await bo_phien_cu()
    state.spec = sheet
    return {"stage": state.stage, "source": title, **sheet.payload()}


@router.post("/event/record")
async def start_record(request: RecordRequest) -> dict:
    if state.spec is None or not state.spec.ok:
        raise HTTPException(
            status_code=409,
            detail="Spec chưa hợp lệ — sửa hết lỗi ở bảng preview rồi mới Ghi được.")
    old = state.recording
    if old is not None and old.live:
        raise HTTPException(status_code=409, detail="Đang ghi rồi.")
    if old is not None and not old.stopped:
        # Stream da chet (may rot khoi USB) ma chua ai bam Dung. Don xac cho
        # tu te - task doc va process con treo o day - roi cho ghi phien moi.
        await logcat_stream.stop(old)

    adb = client()
    tu_mo, nhac = await co_the_tu_mo(adb, request.serial, request.package)
    try:
        recording = await logcat_stream.start(
            adb, request.serial, request.package, from_launch=tu_mo)
    except AdbError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    # Lay mau ngay sau khi mo app. Tu mo tay thi luc nay chua chay - con mau
    # o /event/stop.
    recording.package_found = tu_mo
    await lay_mau_app(adb, recording, ten_co_tren_may=tu_mo)
    state.recording = recording
    state.serial, state.package = request.serial, request.package
    state.quick = False
    state.run, state.windows = None, ()
    return {"stage": state.stage, "quick": state.quick,
            "launched": tu_mo, "hint": nhac,
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

    await lay_mau_app(client(), recording,
                      ten_co_tren_may=recording.package_found)

    events, markers = parse_log(recording.text())
    state.windows, state.quick = windows_for(
        tuple(e.name for e in (state.spec.events if state.spec else ())),
        events, markers)
    return {
        "stage": state.stage,
        "quick": state.quick,
        "recording": recording.payload(),
        "window_count": len(state.windows),
        "event_count": len(events),
        "marker_count": len(markers),
    }
