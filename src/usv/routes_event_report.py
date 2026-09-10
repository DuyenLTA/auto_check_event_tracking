"""Route xuat report HTML.

Tach khoi routes_event.py de moi file duoi 200 LOC, va vi hai viec nay doc
trang thai chu khong sua - de rieng thi doc code de thay cai gi sua state cai
gi khong.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field

from . import artifact_link, report_event_html
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


class ArtifactRequest(BaseModel):
    url: str = Field(default="", max_length=500)
    generated_at: str = Field(default="", max_length=40)


@router.get("/event/artifact")
async def doc_artifact() -> dict:
    """Link artifact + luot da publish, va no CO PHAI luot hien tai khong.

    `khop=False` nghia la artifact dang la bao cao CU. Phai noi ra: gui cho
    team mot bao cao cu ma tuong moi la kieu sai im lang.
    """
    ban = artifact_link.doc()
    run = state.run
    return {
        **ban,
        "khop": bool(ban and run and ban.get("generated_at") == run.generated_at),
        "run_generated_at": run.generated_at if run else "",
    }


@router.post("/event/artifact")
async def ghi_artifact(request: ArtifactRequest) -> dict:
    """Claude goi sau khi publish xong. Tool khong tu publish duoc."""
    if not request.url.startswith("https://"):
        raise HTTPException(status_code=400,
                            detail="URL artifact phải bắt đầu bằng https://")
    return artifact_link.ghi(request.url, request.generated_at)


@router.get("/event/report", response_class=HTMLResponse)
async def report_html() -> HTMLResponse:
    run = _run()
    html = report_event_html.build(
        run.spec, run.results, run.summary, package=run.package,
        generated_at=run.generated_at, event_count=run.event_count,
        fa_silent=run.fa_silent, stream_died=run.stream_died,
        app_seen=run.app_seen, foreground=run.foreground,
        checked_package=run.checked_package,
        near_edge=run.near_edge, quick=run.quick,
    )
    return HTMLResponse(html)


def _warnings(run) -> list[str]:
    """Canh bao dua vao dau bao cao HTML."""
    out = []
    if run.checked_package and run.checked_package != run.package:
        out.append(
            f"ĐÃ CHẤM CHO APP {run.checked_package}: tên bạn dán "
            f"({run.package}) không có trên máy, tool lấy app đang mở lúc ghi. "
            "Nếu không phải app cần test thì dán lại tên đúng rồi ghi lại.")
    if not run.app_seen:
        out.append(
            "APP DƯỚI TEST KHÔNG CHẠY LẦN NÀO trong phiên ghi. Log Firebase do "
            "Google Play Services in ra nên không cho biết event thuộc app nào "
            "— event bắt được là của APP KHÁC. Kiểm lại tên package."
            + (f" Lúc dừng ghi máy đang mở {run.foreground} — rất có thể đây "
               "mới là tên cần dán." if run.foreground else ""))
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
