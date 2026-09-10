"""Route xuat report HTML.

Tach khoi routes_event.py de moi file duoi 200 LOC, va vi hai viec nay doc
trang thai chu khong sua - de rieng thi doc code de thay cai gi sua state cai
gi khong.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, Response

from . import report_event_html
from .event_state import state

log = logging.getLogger(__name__)
router = APIRouter()

XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _run():
    run = state.run
    if run is None:
        raise HTTPException(status_code=409,
                            detail="Chưa chấm lần nào - bấm Chấm trước đã.")
    return run


@router.get("/event/report", response_class=HTMLResponse)
async def report_html() -> HTMLResponse:
    run = _run()
    html = report_event_html.build(
        run.spec, run.results, run.summary, package=run.package,
        generated_at=run.generated_at, event_count=run.event_count,
        fa_silent=run.fa_silent, stream_died=run.stream_died,
        app_seen=run.app_seen, foreground=run.foreground,
        near_edge=run.near_edge, quick=run.quick,
    )
    return HTMLResponse(html)


def _warnings(run) -> list[str]:
    """Canh bao dua vao dau bao cao HTML."""
    out = []
    if not run.app_seen:
        out.append(
            "APP DUOI TEST KHONG CHAY LAN NAO trong phien ghi. Log Firebase do "
            "Google Play Services in ra nen khong cho biet event thuoc app nao "
            "- event bat duoc la cua APP KHAC. Kiem lai ten package."
            + (f" Luc dung ghi may dang mo {run.foreground} - rat co the day "
               "moi la ten can dan." if run.foreground else ""))
    if run.stream_died:
        # Dat dau tien: doc bang ma khong biet phien ghi da chet thi moi dong
        # "khong bat duoc" deu bi hieu sai thanh loi app.
        out.append(
            "PHIÊN GHI BỊ ĐỨT GIỮA ĐƯỜNG: stream logcat dừng trước khi bấm Dừng "
            "ghi (thường là máy rớt khỏi USB). Phần sau của phiên không được "
            "ghi, nên các mục 'không bắn' chỉ là KHÔNG KIỂM ĐƯỢC, không phải "
            "lỗi app. Cắm lại máy và ghi lại.")
    if run.quick:
        out.append(
            "Chạy ở chế độ nhanh (không đánh dấu từng bước): file này chỉ kết "
            "luận event có bắn ra trong cả phiên và param có đúng hay không, "
            "KHÔNG kết luận event bắn đúng lúc. Kiểm bắn trùng đã tắt.")
    if run.fa_silent:
        out.append(
            "Cả phiên ghi không có dòng log FA-SVC nào. Rất có thể bản build này "
            "không in log Firebase, KHÔNG phải app thiếu event - đừng kết luận "
            "app sai từ file này.")
    if run.near_edge:
        out.append(
            "Event bắn sát mốc đánh dấu nên có thể thuộc bước liền kề, công cụ "
            "không tự đổi bước cho chúng: " + ", ".join(run.near_edge))
    return out
