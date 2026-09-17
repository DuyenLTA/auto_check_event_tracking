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

from .ad_close import tim_nut_dong
from .adb_parsers import AdbError
from .device_actions import swipe, tap
from .event_flow_models import Flow, FlowCase, Step
from .event_flow_reset import LAUNCH_SETTLE, prepare
from .event_window import mark_label
from .logcat_stream import Recording, mark
from .models import DeviceNode
from .flow_screen import cho_nut, nodes, wait_text
from .quyen_he_thong import tim_nut_cho_phep
from .ui_cache import CayUI

log = logging.getLogger(__name__)

# Chu ky doc lai cay UI khi cho mot chuoi xuat hien. `uiautomator dump` da mat
# ~2.2s tren may that nen ban than no la cai ham nhip; ngu them nua chi keo dai
# luot cham.
# Cho man lang lai sau khi dong quang cao: interstitial thuong co animation
# dong, bam ngay buoc sau la bam vao lop dang bay ra.
AD_SETTLE = 1.0
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


async def _bam_node(client, serial: str, node) -> None:
    """Bam vao TAM node - goc tren-trai co the nam ngoai vung bam duoc."""
    box = node.bounds_px
    await client.input_tap(serial, (box.left + box.right) / 2,
                           (box.top + box.bottom) / 2)


async def run_step(client, serial: str, metrics, package: str, step: Step,
                   cay: CayUI | None = None) -> None:
    """Chay mot step. That bai -> AdbError co message noi ro sai o dau."""
    if step.kind == "launch":
        await client.force_stop(serial, package)
        await client.launch(serial, package)
        await asyncio.sleep(LAUNCH_SETTLE)
        if cay is not None:
            cay.bo()
        return
    if step.kind == "wait":
        await asyncio.sleep(max(0.0, step.seconds))
        return
    if step.kind == "key":
        await client.input_keyevent(serial, step.text)
        if cay is not None:
            cay.bo()
        return
    if step.kind == "type":
        await client.input_text(serial, step.text)
        if cay is not None:
            cay.bo()
        return
    if step.kind == "wait_text":
        if not await wait_text(client, serial, metrics, step.text,
                               step.timeout, cay):
            raise AdbError(
                f"Chờ {step.text!r} xuất hiện trong {step.timeout:g}s mà không thấy.")
        return
    if step.kind == "allow":
        # Dialog quyen do he thong ve, nam DE tren app - moi selector cua app
        # deu khong thay gi cho toi khi no duoc bam. Khong co dialog = binh
        # thuong, im lang di tiep.
        node = await cho_nut(client, serial, metrics, cay, step.timeout,
                             tim_nut_cho_phep)
        if node is not None:
            await _bam_node(client, serial, node)
            log.info("Da cap quyen bang %s", node.label)
            if cay is not None:
                cay.bo()
            await asyncio.sleep(AD_SETTLE)
        return

    if step.kind == "close_ad":
        # Khong thay nut dong = khong co quang cao chan duong. Do la truong hop
        # binh thuong nhat, nen im lang di tiep chu KHONG bao loi.
        # `timeout` de cho quang cao KIP hien: splash ad mat 5-8s moi ra nut
        # Skip, kiem mot lan roi bo qua la luon truot.
        node = await cho_nut(client, serial, metrics, cay, step.timeout,
                             tim_nut_dong)
        if node is not None:
            await _bam_node(client, serial, node)
            log.info("Da dong quang cao bang %s", node.label)
            if cay is not None:
                cay.bo()
            await asyncio.sleep(AD_SETTLE)
        return

    if step.kind == "tap":
        await tap(client, serial, await nodes(client, serial, metrics, cay),
                  step.selector)
        if cay is not None:
            cay.bo()          # da bam -> man doi, cay vua doc thanh qua khu
        return
    if step.kind == "swipe":
        await swipe(client, serial, await nodes(client, serial, metrics, cay),
                    step.selector, step.text or "up")
        if cay is not None:
            cay.bo()
        return
    raise AdbError(f"Step {step.kind!r} không hiểu.")


async def run_case(client, serial: str, metrics, package: str,
                   recording: Recording, case: FlowCase,
                   on_shot=None) -> CaseResult:
    """`on_shot(moment)` - callback chup man. None thi khong chup gi.

    Chup quanh STEP CUOI chu khong moi step: step cuoi la cai lam event ban ra,
    con 30 tam anh cua duong di thi phinh report ma khong tra loi duoc cau hoi
    nao.
    """
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

    cay = CayUI()
    cuoi = len(case.steps) - 1
    for order, step in enumerate(case.steps):
        if on_shot is not None and order == cuoi:
            await on_shot("trước bước cuối")
        try:
            await run_step(client, serial, metrics, package, step, cay)
        except AdbError as exc:
            if step.optional:
                # Man dong (quang cao, popup) luc co luc khong. Bo qua va di
                # tiep, nhung GHI LAI: doc report phai thay duoc lan chay nay
                # di duong nao.
                result.notes.append(f"bỏ qua bước tuỳ chọn `{step.label()}`")
                continue
            result.status = "not_tested"
            result.reason = f"step `{step.label()}` thất bại: {exc}"
            if on_shot is not None:
                # Anh o DUNG cho lai hut - thu duy nhat noi duoc vi sao khong
                # bam trung: man khac han, quang cao che, hay dialog chan.
                await on_shot("lúc lái hụt")
            return result
        result.steps_done += 1
    if on_shot is not None:
        await on_shot("sau bước cuối")
    return result


async def run_flow(client, serial: str, metrics, package: str,
                   recording: Recording, flow: Flow, album=None) -> list[CaseResult]:
    """Chay tuan tu. Mot case blocked KHONG dung ca luot - cac case khac van do duoc."""
    out: list[CaseResult] = []
    for case in flow.cases:
        on_shot = album.recorder(case.label) if album is not None else None
        result = await run_case(client, serial, metrics, package, recording, case,
                                on_shot=on_shot)
        if not result.ran:
            log.warning("Case %s: %s - %s", case.label, result.status, result.reason)
        out.append(result)
    return out


def expectations(results: list[CaseResult]) -> dict[str, dict[str, str]]:
    """Nhan case -> gia tri doi hoi, chi lay case DA CHAY duoc.

    Case blocked/not_tested khong chen moc nen khong co cua so nao mang nhan do.
    """
    return {r.case.label: dict(r.case.expect_params) for r in results if r.ran}
