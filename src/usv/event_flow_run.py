"""Chay flow: moi case reset trang thai, lai app, roi cho MOT event ban ra.

Thu tu trong mot case KHONG doi duoc:
  1. sua Remote Config / xoa prefs      app dang chay cung duoc
  2. force-stop + mo lai app            app doc gia tri moi luc process start
  3. doc lai de verify                  patch khong song -> BLOCKED
  4. chen moc USV_MARK                  moc mo cua so cua case
  5. chay cac step                      bam/quet/go chu/cho

STEP THAT BAI -> case do NOT_TESTED kem ly do, KHONG phai FAIL. Khong lai toi
duoc man can test thi tool chua do gi ca - ket luan app thieu event luc do la
bao oan. Cung nguyen tac voi fa_silent.

Moc mang NHAN cua case (`event | case.label`) chu khong chi mang ten event: mot
event co the co nhieu case (placement_name co 4 gia tri), khong phan biet duoc
nhan thi khong biet cua so nao ung voi case nao.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from . import remote_config
from .adb_parsers import AdbError
from .device_actions import swipe, tap
from .event_flow_models import Flow, FlowCase, Step
from .event_window import mark_label
from .logcat_stream import Recording, mark
from .models import DeviceNode
from .ui_dump import parse_dump

log = logging.getLogger(__name__)

# Cho app ve man dau sau khi mo lai. Khong cho thi step dau bam vao splash.
LAUNCH_SETTLE = 2.5
# Chu ky doc lai cay UI khi cho mot chuoi xuat hien.
POLL = 0.5


@dataclass(slots=True)
class CaseResult:
    case: FlowCase
    status: str = "ok"              # ok | not_tested | blocked
    reason: str = ""
    steps_done: int = 0
    notes: list[str] = field(default_factory=list)

    @property
    def ran(self) -> bool:
        return self.status == "ok"

    def payload(self) -> dict:
        return {"case": self.case.label, "event": self.case.event,
                "status": self.status, "reason": self.reason,
                "steps_done": self.steps_done, "notes": self.notes}


async def _nodes(client, serial: str, metrics) -> list[DeviceNode]:
    return parse_dump(await client.dump_ui(serial), metrics)


async def _wait_text(client, serial: str, metrics, needle: str,
                     timeout: float) -> bool:
    """Cho mot chuoi xuat hien tren man. Het gio -> False, nguoi goi tu xu."""
    folded = needle.casefold()
    deadline = timeout
    while deadline > 0:
        for node in await _nodes(client, serial, metrics):
            if folded in node.text.casefold() or folded in node.content_desc.casefold():
                return True
        await asyncio.sleep(POLL)
        deadline -= POLL
    return False


async def run_step(client, serial: str, metrics, package: str, step: Step) -> None:
    """Chay mot step. That bai -> AdbError co message noi ro sai o dau."""
    if step.kind == "launch":
        await client.force_stop(serial, package)
        await client.launch(serial, package)
        await asyncio.sleep(LAUNCH_SETTLE)
        return
    if step.kind == "wait":
        await asyncio.sleep(max(0.0, step.seconds))
        return
    if step.kind == "key":
        await client.input_keyevent(serial, step.text)
        return
    if step.kind == "type":
        await client.input_text(serial, step.text)
        return
    if step.kind == "wait_text":
        if not await _wait_text(client, serial, metrics, step.text, step.timeout):
            raise AdbError(
                f"Cho {step.text!r} xuat hien trong {step.timeout:g}s ma khong thay.")
        return
    if step.kind == "tap":
        await tap(client, serial, await _nodes(client, serial, metrics), step.selector)
        return
    if step.kind == "swipe":
        await swipe(client, serial, await _nodes(client, serial, metrics),
                    step.selector, step.text or "up")
        return
    raise AdbError(f"Step {step.kind!r} khong hieu.")


async def prepare(client, serial: str, package: str,
                  case: FlowCase) -> tuple[bool, str, list[str]]:
    """Reset + mo lai app + verify. Tra (di tiep duoc, ly do, ghi chu)."""
    notes: list[str] = []
    reset = case.reset

    if reset.clear_prefs:
        cleared = await remote_config.clear_prefs(
            client, serial, package, list(reset.clear_prefs))
        if not cleared.ok:
            return False, cleared.blocked, notes
        notes.extend(cleared.notes)

    if reset.remote_config:
        applied = await remote_config.override(
            client, serial, package, reset.remote_config)
        if not applied.ok:
            return False, applied.blocked, notes
        notes.extend(applied.notes)
        if applied.mirrors:
            notes.append("prefs mirror đã sửa: " + ", ".join(sorted(applied.mirrors)))

    if reset.relaunch:
        await client.force_stop(serial, package)
        await client.launch(serial, package)
        await asyncio.sleep(LAUNCH_SETTLE)

    if reset.remote_config:
        # Doc lai SAU khi mo lai app: build dev dat minimumFetchInterval = 0 thi
        # throttle vo hieu, app fetch that va de mat patch. Luc do tien de chua
        # dat -> BLOCKED, tuyet doi khong ket luan app sai.
        got = await remote_config.verify(client, serial, package, reset.remote_config)
        lech = {k: (v, got.get(k, "")) for k, v in reset.remote_config.items()
                if got.get(k, "") != str(v)}
        if lech:
            detail = ", ".join(f"{k}: cần {want!r} nhưng đang {have!r}"
                               for k, (want, have) in lech.items())
            return False, (
                "Remote Config không giữ được giá trị sau khi mở lại app "
                f"({detail}). Thường là bản build đặt minimumFetchInterval = 0 "
                "nên throttle vô hiệu và app fetch thật đè lên."), notes
    return True, "", notes


async def run_case(client, serial: str, metrics, package: str,
                   recording: Recording, case: FlowCase) -> CaseResult:
    result = CaseResult(case=case)
    try:
        ready, reason, notes = await prepare(client, serial, package, case)
    except AdbError as exc:
        return CaseResult(case=case, status="blocked", reason=str(exc))
    result.notes.extend(notes)
    if not ready:
        result.status, result.reason = "blocked", reason
        return result

    await mark(client, recording, mark_label(case.event, case.label))

    for step in case.steps:
        try:
            await run_step(client, serial, metrics, package, step)
        except AdbError as exc:
            result.status = "not_tested"
            result.reason = f"step `{step.label()}` thất bại: {exc}"
            return result
        result.steps_done += 1
    return result


async def run_flow(client, serial: str, metrics, package: str,
                   recording: Recording, flow: Flow) -> list[CaseResult]:
    """Chay tuan tu. Mot case blocked KHONG dung ca luot - cac case khac van do duoc."""
    out: list[CaseResult] = []
    for case in flow.cases:
        result = await run_case(client, serial, metrics, package, recording, case)
        if not result.ran:
            log.warning("Case %s: %s - %s", case.label, result.status, result.reason)
        out.append(result)
    return out


def expectations(results: list[CaseResult]) -> dict[str, dict[str, str]]:
    """Nhan case -> gia tri doi hoi, chi lay case DA CHAY duoc.

    Case blocked/not_tested khong chen moc nen khong co cua so nao mang nhan do.
    """
    return {r.case.label: dict(r.case.expect_params) for r in results if r.ran}
