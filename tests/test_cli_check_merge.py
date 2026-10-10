"""Gop luot chay le vao luot base o tang cua so tung case."""

from __future__ import annotations

from usv.cli_check_merge import Base, Nguon, gop
from usv.event_flow_models import FlowCase
from usv.event_flow_run import CaseResult
from usv.event_window import cut_log, mark_label

MARK = "09-08 15:00:{sec:02d}.000 I/USV_MARK( 9): {label}"
EVENT = ("09-08 15:00:{sec:02d}.500 V/FA-SVC  ( 9): Logging event: origin=app,"
         "name={name},params=Bundle[{{a=1}}]")

A = FlowCase(event="download", name="Download ở Result")
B = FlowCase(event="download", name="Download ở History")
FLOW = (A, B)


def log(*buoc):
    """buoc: (giay, case, [event ban trong buoc])."""
    dong = []
    for sec, case, names in buoc:
        dong.append(MARK.format(sec=sec, label=mark_label(case.event, case.label)))
        dong += [EVENT.format(sec=sec, name=n) for n in names]
    return "\n".join(dong)


def base_hut_a():
    text = log((1, A, []), (5, B, ["download"]))
    nguon = (Nguon(log="base.log", text=text, nhan=frozenset({A.label, B.label})),)
    cases = [CaseResult(case=A, status="not_tested", reason="hut"),
             CaseResult(case=B)]
    return Base(payload={}, nguon=nguon), cases


def test_case_chay_lai_thay_cua_so_case_kia_giu_nguyen():
    base, base_cases = base_hut_a()
    moi_text = log((10, A, ["download"]))
    moi_windows = cut_log(moi_text)
    cases, windows, _, so_moi, nguon = gop(
        base, base_cases, [CaseResult(case=A)], [], moi_windows,
        {A.label}, FLOW, "moi.log")
    assert so_moi == 1
    assert [c.status for c in cases] == ["ok", "ok"]
    # Ca hai case cung event `download` van con du cua so - khong de mat case B.
    assert sorted(w.note for w in windows) == sorted([A.label, B.label])
    assert {n.log: n.nhan for n in nguon} == {"base.log": {B.label},
                                              "moi.log": {A.label}}


def test_chay_lai_van_hut_thi_lay_ban_moi_khong_giau():
    base, base_cases = base_hut_a()
    cases, *_ = gop(base, base_cases,
                    [CaseResult(case=A, status="not_tested", reason="van hut")],
                    [], (), {A.label}, FLOW, "moi.log")
    assert cases[0].reason == "van hut"


def test_case_tien_de_base_da_ok_thi_giu_base():
    base, base_cases = base_hut_a()
    moi_windows = cut_log(log((10, B, [])))
    cases, windows, *_ = gop(base, base_cases, [CaseResult(case=B)], [],
                             moi_windows, set(), FLOW, "moi.log")
    giu = [w for w in windows if w.note == B.label]
    assert len(giu) == 1 and giu[0].named("download")   # cua so base, co event
