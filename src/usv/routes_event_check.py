"""Route pha CHAM: doi chieu log da ghi voi spec, va don de lam lai.

Tach khoi routes_event vi hai pha nay doc lap: pha GHI dieu khien may that qua
adb, pha CHAM chi lam viec tren du lieu da nam trong bo nho. Sua mot ben khong
phai doc ben kia.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from . import event_check_runner, logcat_stream
from .check_config import ConfigError, load as load_config
from .event_state import EventRun, now_vn, state
from .fa_event_parse import parse_log

router = APIRouter()


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
        # So EVENT trong spec, tach khoi so DONG kiem: spec 2 event co the ra
        # 5 dong (2 dong event + 3 dong param), va nguoi doc dem dong roi hoi
        # "5 event o dau ra".
        "spec_event_count": len(state.spec.events),
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
