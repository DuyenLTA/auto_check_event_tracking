"""Gop luot chay le (`--case`) vao luot day du truoc do (`--base`).

Mot luot day du mat ~30 phut tren may that. Con vai case lai hut thi chi chay
lai DUNG cac case do (tester chot 05/10/2026), roi gop: report ra van du moi
event spec, khong phai chay lai ca luot.

Gop o tang CUA SO TUNG CASE, khong o tang dong ket qua: dong param
(`download.media_type`) khong mang ten case, mot event lai co nhieu case
(download o Result / Result video / History) - de theo event la de mat dong
cua case khong chay lai. Cua so thi mang nhan case (`Window.note`), nen lay
cua so base cho case khong chay lai, cua so moi cho case chay lai, roi CHAM LAI
tu dau tren bo cua so gop.

Case nao lay ban moi:
  - case khop `--case` -> luon lay moi, du ket qua la gi. Chay lai ma van hut
    thi report phai noi van hut, khong giau bang ket qua cu.
  - case tien de bi keo theo -> chi lay moi khi base hut ma lan nay chay duoc.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .event_flow_run import CaseResult
from .fa_event_parse import parse_log
from .event_window import cut


class MergeError(Exception):
    """File base khong doc duoc."""


@dataclass(frozen=True, slots=True)
class Nguon:
    """Mot file log phien + nhan case lay cua so tu file do."""
    log: str
    text: str
    nhan: frozenset[str]


@dataclass(frozen=True, slots=True)
class Base:
    payload: dict
    nguon: tuple[Nguon, ...]


def doc_base(path: Path) -> Base:
    """Doc stdout JSON cua luot truoc (dong JSON cuoi) + file log phien cua no."""
    try:
        dong = [d for d in path.read_text(encoding="utf-8").splitlines() if d.strip()]
        payload = json.loads(dong[-1])
    except (OSError, IndexError, json.JSONDecodeError) as exc:
        raise MergeError(f"Không đọc được --base {path}: {exc}") from exc
    nguon_raw = payload.get("sources")
    if not nguon_raw:
        raise MergeError(f"--base {path} không có `sources` (lượt chạy bằng bản tool "
                         "cũ) - không gộp được, cần một lượt đầy đủ mới làm base.")
    nguon = []
    for n in nguon_raw:
        try:
            text = Path(n["log"]).read_text(encoding="utf-8")
        except OSError as exc:
            raise MergeError(f"Không đọc được log của base {n['log']}: {exc}") from exc
        nguon.append(Nguon(log=n["log"], text=text, nhan=frozenset(n["labels"])))
    return Base(payload=payload, nguon=tuple(nguon))


def sources(nguon: tuple[Nguon, ...]) -> list[dict]:
    """Ghi vao payload de luot sau dung lam base."""
    return [{"log": n.log, "labels": sorted(n.nhan)} for n in nguon if n.nhan]


def case_base(base: Base, flow_cases: tuple) -> list[CaseResult]:
    """Dung lai CaseResult cua luot base tu payload, khop case theo nhan."""
    theo_nhan = {c.label: c for c in flow_cases}
    ra = []
    for c in base.payload.get("cases", []):
        case = theo_nhan.get(c["case"])
        if case is None:
            continue           # case da doi nhan/bi xoa khoi flow - bo
        ra.append(CaseResult(case=case, status=c["status"], reason=c["reason"],
                             steps_done=c.get("steps_done", 0),
                             notes=list(c.get("notes", []))))
    return ra


def gop(base: Base, base_cases: list[CaseResult], moi_cases: list[CaseResult],
        moi_events: list, moi_windows: tuple, chon: set[str], flow_cases: tuple,
        moi_log: str):
    """Tra (cases, windows, session_events, so case lay moi, nguon moi).

    `chon`: nhan case khop --case. `moi_log`: duong dan log cua luot nay.
    """
    cu = {c.case.label: c for c in base_cases}
    moi = {c.case.label: c for c in moi_cases}
    lay_moi = {nhan for nhan, c in moi.items()
               if nhan in chon or (c.ran and not (nhan in cu and cu[nhan].ran))}
    thu_tu = {c.label: i for i, c in enumerate(flow_cases)}
    cases = sorted([c for n, c in cu.items() if n not in lay_moi]
                   + [moi[n] for n in lay_moi],
                   key=lambda c: thu_tu.get(c.case.label, len(thu_tu)))
    windows: list = []
    session: list = []
    nguon_ra: list[Nguon] = []
    for n in base.nguon:
        events, markers = parse_log(n.text)
        giu = n.nhan - lay_moi
        windows.extend(w for w in cut(events, markers) if w.note in giu)
        session.extend(events)
        nguon_ra.append(Nguon(log=n.log, text="", nhan=frozenset(giu)))
    windows.extend(w for w in moi_windows if w.note in lay_moi)
    session.extend(moi_events)
    nguon_ra.append(Nguon(log=moi_log, text="", nhan=frozenset(lay_moi)))
    return cases, tuple(windows), session, len(lay_moi), tuple(nguon_ra)
