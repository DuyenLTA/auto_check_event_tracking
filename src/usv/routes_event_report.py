"""Route xuat report: HTML de xem, xlsx de gui cho dev.

Tach khoi routes_event.py de moi file duoi 200 LOC, va vi hai viec nay doc
trang thai chu khong sua - de rieng thi doc code de thay cai gi sua state cai
gi khong.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, Response

from . import exporter, report_event_html
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
        fa_silent=run.fa_silent, near_edge=run.near_edge,
    )
    return HTMLResponse(html)


@router.get("/event/report.xlsx")
async def report_xlsx() -> Response:
    run = _run()
    data = exporter.build(
        run.results, run.summary, package=run.package,
        device=state.serial, generated_at=run.generated_at,
        warnings=_warnings(run),
    )
    name = f"event-tracking-{run.package or 'app'}.xlsx".replace("/", "-")
    return Response(
        content=data, media_type=XLSX_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


def _warnings(run) -> list[str]:
    """Hai canh bao KHONG duoc de mat khi xuat xlsx.

    Nguoi doc file xlsx thuong la dev, va ho khong thay callout trong ban HTML.
    Thieu hai dong nay thi ho doc mot bang toan 'Thieu' va tuong app hong.
    """
    out = []
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
