"""Chay flow. Khong can may - client va logcat duoc thay ban gia.

Hai bat buoc:
  - STEP THAT BAI -> not_tested, KHONG phai fail. Khong lai toi duoc man can
    test thi tool chua do gi ca.
  - RESET khong an -> blocked, cung khong phai fail.
"""

from __future__ import annotations

import asyncio

import pytest

from usv import event_flow_run, remote_config
from usv.adb_parsers import AdbError
from usv.density import ScreenMetrics
from usv.device_actions import Selector
from usv.event_flow_models import Flow, FlowCase, Reset, Step
from usv.event_flow_run import expectations, run_case, run_flow
from usv.event_window import cut_log, mark_label, with_expectations
from usv.logcat_stream import Recording

METRICS = ScreenMetrics(width_px=1080, height_px=2280, density=440)

DUMP = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0"><node index="0" text="" resource-id="" class="a.b.FrameLayout"
 package="com.x" content-desc="" clickable="false" enabled="true" visible-to-user="true"
 bounds="[0,0][1080,2280]"><node index="0" text="Home" resource-id="com.x:id/btnHome"
 class="a.b.TextView" package="com.x" content-desc="" clickable="true" enabled="true"
 visible-to-user="true" bounds="[100,200][300,400]" /></node></hierarchy>"""


class FakeClient:
    def __init__(self) -> None:
        self.log: list[str] = []
        self.marks: list[str] = []
        self.taps = 0
        self.debuggable = True

    async def dump_ui(self, serial):
        return DUMP

    async def force_stop(self, serial, package):
        self.log.append("force_stop")

    async def launch(self, serial, package):
        self.log.append("launch")

    async def input_tap(self, serial, x, y):
        self.taps += 1

    async def input_keyevent(self, serial, name):
        self.log.append(f"key:{name}")

    async def input_text(self, serial, text):
        self.log.append(f"type:{text}")

    async def shell_log(self, serial, tag, message):
        self.marks.append(message)

    async def is_debuggable(self, serial, package):
        return self.debuggable


@pytest.fixture(autouse=True)
def _no_wait(monkeypatch):
    async def instant(_s):
        return None
    monkeypatch.setattr(event_flow_run.asyncio, "sleep", instant)


@pytest.fixture
def recording():
    return Recording(serial="S1", package="com.x", stopped=False)


def _case(**kw):
    base = dict(event="rating_placement_viewed", name="rating tai home",
                expect_params={"placement_name": "home"},
                steps=(Step(kind="tap", selector=Selector(resource_id="btnHome")),))
    base.update(kw)
    return FlowCase(**base)


def run(coro):
    return asyncio.run(coro)


def test_case_chay_duoc_thi_chen_moc_va_chay_het_step(recording):
    client = FakeClient()
    result = run(run_case(client, "S1", METRICS, "com.x", recording, _case()))
    assert result.status == "ok"
    assert result.steps_done == 1
    assert client.taps == 1
    assert client.marks == [mark_label("rating_placement_viewed", "rating tai home")]


def test_moc_mang_NHAN_CASE_de_phan_biet_nhieu_case_cung_event(recording):
    """placement_name co 4 gia tri -> 4 case cung mot event."""
    client = FakeClient()
    for place in ("home", "result"):
        run(run_case(client, "S1", METRICS, "com.x", recording,
                     _case(name=f"rating tai {place}",
                           expect_params={"placement_name": place})))
    assert client.marks == [
        mark_label("rating_placement_viewed", "rating tai home"),
        mark_label("rating_placement_viewed", "rating tai result"),
    ]


def test_step_that_bai_ra_NOT_TESTED_khong_phai_fail(recording):
    client = FakeClient()
    case = _case(steps=(Step(kind="tap", selector=Selector(resource_id="khong_co")),))
    result = run(run_case(client, "S1", METRICS, "com.x", recording, case))
    assert result.status == "not_tested"
    assert "that bai" in result.reason or "thất bại" in result.reason
    assert client.taps == 0


def test_step_that_bai_giua_duong_ghi_lai_da_chay_bao_nhieu(recording):
    client = FakeClient()
    case = _case(steps=(
        Step(kind="tap", selector=Selector(resource_id="btnHome")),
        Step(kind="tap", selector=Selector(resource_id="khong_co")),
    ))
    result = run(run_case(client, "S1", METRICS, "com.x", recording, case))
    assert result.steps_done == 1
    assert result.status == "not_tested"


def test_step_la_bao_loi(recording):
    client = FakeClient()
    result = run(run_case(client, "S1", METRICS, "com.x", recording,
                          _case(steps=(Step(kind="nhay_lung_tung"),))))
    assert result.status == "not_tested"


def test_reset_bi_chan_ra_BLOCKED_khong_phai_fail(recording, monkeypatch):
    client = FakeClient()
    client.debuggable = False
    case = _case(reset=Reset(remote_config={"enable_rate": "true"}))
    result = run(run_case(client, "S1", METRICS, "com.x", recording, case))
    assert result.status == "blocked"
    assert "debuggable" in result.reason


def test_reset_khong_giu_duoc_gia_tri_ra_BLOCKED(recording, monkeypatch):
    """Build dev dat minimumFetchInterval = 0 -> throttle vo hieu."""
    client = FakeClient()

    async def fake_override(*_a, **_k):
        return remote_config.OverrideResult(applied={"enable_rate": "true"})

    async def fake_verify(*_a, **_k):
        return {"enable_rate": "false"}      # app fetch that, de mat patch

    monkeypatch.setattr(remote_config, "override", fake_override)
    monkeypatch.setattr(remote_config, "verify", fake_verify)
    case = _case(reset=Reset(remote_config={"enable_rate": "true"}))
    result = run(run_case(client, "S1", METRICS, "com.x", recording, case))
    assert result.status == "blocked"
    assert "minimumFetchInterval" in result.reason


def test_reset_mo_lai_app_truoc_khi_chen_moc(recording, monkeypatch):
    """App doc gia tri moi luc process start, nen phai mo lai TRUOC khi do."""
    client = FakeClient()

    async def fake_override(*_a, **_k):
        return remote_config.OverrideResult(applied={"k": "v"})

    async def fake_verify(*_a, **_k):
        return {"k": "v"}

    monkeypatch.setattr(remote_config, "override", fake_override)
    monkeypatch.setattr(remote_config, "verify", fake_verify)
    run(run_case(client, "S1", METRICS, "com.x", recording,
                 _case(reset=Reset(remote_config={"k": "v"}))))
    assert client.log[:2] == ["force_stop", "launch"]


def test_mot_case_blocked_khong_dung_ca_luot(recording, monkeypatch):
    client = FakeClient()
    ok_case = _case(name="case chay duoc")
    bad_case = _case(name="case bi chan", steps=(
        Step(kind="tap", selector=Selector(resource_id="khong_co")),))
    results = run(run_flow(client, "S1", METRICS, "com.x", recording,
                           Flow(package="com.x", cases=(bad_case, ok_case))))
    assert [r.status for r in results] == ["not_tested", "ok"]


def test_expectations_chi_lay_case_da_chay(recording):
    client = FakeClient()
    ok_case = _case(name="chay duoc", expect_params={"placement_name": "home"})
    bad_case = _case(name="khong chay", expect_params={"placement_name": "result"},
                     steps=(Step(kind="tap", selector=Selector(resource_id="x")),))
    results = run(run_flow(client, "S1", METRICS, "com.x", recording,
                           Flow(cases=(ok_case, bad_case))))
    assert expectations(results) == {"chay duoc": {"placement_name": "home"}}


def test_gan_gia_tri_doi_hoi_vao_cua_so_theo_NHAN_khong_theo_thu_tu():
    """Case that bai khong chen moc -> zip theo thu tu se gan lech."""
    log = "\n".join([
        "09-08 15:00:01.000 I/USV_MARK( 9): "
        + mark_label("rating_placement_viewed", "case B"),
        "09-08 15:00:02.000 V/FA-SVC ( 9): Logging event: origin=app,"
        "name=rating_placement_viewed,params=Bundle[{placement_name=result}]",
    ])
    windows = with_expectations(cut_log(log), {
        "case A": {"placement_name": "home"},
        "case B": {"placement_name": "result"},
    })
    assert windows[0].expect_params == {"placement_name": "result"}


def test_cua_so_khong_co_nhan_khop_thi_de_rong():
    log = ("09-08 15:00:01.000 I/USV_MARK( 9): "
           + mark_label("ev_a", "nhan khong khop"))
    windows = with_expectations(cut_log(log), {"nhan khac": {"a": "1"}})
    assert windows[0].expect_params == {}
