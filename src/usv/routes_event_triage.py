"""Route nhan ghi chu triage tu agent.

Tool khong tu suy ra duoc "app thieu that hay spec cu" - viec do can doc trang
spec va log tho. Agent chay trong Claude Code lam viec do roi POST ket qua vao
day. Tool chi luu va hien.

Vi sao BAT BUOC khop `generated_at`: ghi chu cua luot truoc dan vao luot sau
la kieu sai im lang te nhat - nguoi doc thay mot ket luan tu tin ve mot lan
chay khac. Da gap dung benh nay o nut artifact, nen chan ngay tu dau.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .event_state import state
from .event_triage import TriageError, doc

router = APIRouter()


class TriageRequest(BaseModel):
    # Moc cua luot dang xem. Bat buoc: khong co no thi khong kiem duoc ghi chu
    # nay thuoc lan chay nao.
    generated_at: str = Field(min_length=1, max_length=40)
    notes: list[dict] = Field(default_factory=list)
    bo_sot: int | None = None


def _run():
    run = state.run
    if run is None:
        raise HTTPException(status_code=409,
                            detail="Chưa chấm lần nào - bấm Chấm trước đã.")
    return run


def _fail_elements(run) -> set[str]:
    return {r.element for r in run.results if r.failed}


@router.get("/event/triage")
async def doc_triage() -> dict:
    run = state.run
    if run is None or run.triage is None:
        return {"co": False, "notes": [], "bo_sot": 0, "generated_at": ""}
    return {"co": True, **run.triage.payload()}


@router.post("/event/triage")
async def ghi_triage(request: TriageRequest) -> dict:
    run = _run()
    if request.generated_at != run.generated_at:
        raise HTTPException(
            status_code=409,
            detail=(f"Ghi chú này của lượt {request.generated_at!r} nhưng lượt "
                    f"đang xem là {run.generated_at!r}. Chấm lại rồi triage "
                    "lượt mới."))

    payload = {"notes": request.notes}
    if request.bo_sot is not None:
        payload["bo_sot"] = request.bo_sot
    try:
        batch = doc(payload, fail_elements=_fail_elements(run),
                    generated_at=run.generated_at)
    except TriageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    run.triage = batch
    return {"da_ghi": len(batch.notes), "bo_sot": batch.bo_sot,
            "generated_at": batch.generated_at}
