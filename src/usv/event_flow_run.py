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

from .ad_close import tim_nut_dong, tim_nut_dong_popup
from .adb_parsers import AdbError
from .device_actions import swipe, tap
from .event_flow_models import Flow, FlowCase, Step
from .event_flow_reset import LAUNCH_SETTLE, prepare
from .event_window import mark_label
from .logcat_stream import Recording, mark
from .models import DeviceNode
from .flow_screen import (bam_node as _bam_node, cho_nut,
                          dong_man_chan, man_chan, nodes,
                          wait_text)
from .quyen_he_thong import tim_nut_cho_phep
from .ui_cache import CayUI

log = logging.getLogger(__name__)

# Chu ky doc lai cay UI khi cho mot chuoi xuat hien. `uiautomator dump` da mat
# ~2.2s tren may that nen ban than no la cai ham nhip; ngu them nua chi keo dai
# luot cham.
# Cho man lang lai sau khi dong quang cao: interstitial thuong co animation
# dong, bam ngay buoc sau la bam vao lop dang bay ra.
AD_SETTLE = 1.0
# So vong thu dong mot popup. Lop che (paywall, quang cao) an mat cu tap dau
# tien, nen mot vong la khong du; nhieu hon ba thi thuong la man khac han.
VONG_DONG_POPUP = 3
# Cho man dung lai truoc khi chup tam "sau buoc cuoi": bam xong thi bottom
# sheet / dialog cua he thong con dang bay ra, chup ngay la duoc mot tam nua
# trong nua man - do duoc tren may that khi bam "Add Widget Now". Tam nay la
# bang chung NGU CANH ("cuoi buoc cuoi man nao dang hien"), khong phai bang
# chung thoi diem, nen cham mot nhip khong lam sai ket qua cham nao.
SHOT_SETTLE = 1.0
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


async def _dong_popup(client, serial: str, metrics, neo: str,
                      cay: CayUI | None) -> None:
    """Bam X cua popup mang chu `neo`, kiem lai, con thi don lop che roi bam lai.

    Bam mot phat roi tin la xong thi hong: nut X co that va tim dung, nhung
    PAYWALL dang phu len tren nen cu tap roi vao lop tren - do duoc tren may
    that, anh chup luc lai hut cho thay popup van nguyen sau khi "da bam".
    Nen phai doc lai man: popup con thi don lop che (chi mau CHAC, khong dong
    nham popup khac) roi bam lai.
    """
    thap = neo.strip().casefold()

    async def con_hien() -> bool:
        return any(thap in n.text.casefold() or thap in n.content_desc.casefold()
                   for n in await nodes(client, serial, metrics, cay))

    da_bam = False
    for _ in range(VONG_DONG_POPUP):
        tren_man = await nodes(client, serial, metrics, cay)
        if not any(thap in n.text.casefold() or thap in n.content_desc.casefold()
                   for n in tren_man):
            return                      # popup da dong
        # Bam roi ma van con -> co lop che. Don no truoc, dung bam lai vo ich.
        nut = None if da_bam else tim_nut_dong_popup(tren_man, neo)
        if nut is None:
            nut = tim_nut_dong(tren_man, chi_chac=True,
                               **await man_chan(client, serial))
            da_bam = False              # don xong thi thu lai nut cua popup
            if nut is None:
                raise AdbError(
                    f"Thấy popup {neo!r} nhưng không đóng được: không tìm ra nút "
                    "đóng nào dùng được trên màn.")
        else:
            da_bam = True
        await _bam_node(client, serial, nut)
        if cay is not None:
            cay.bo()
        await asyncio.sleep(AD_SETTLE)
    # Cu bam cuoi cung cung phai duoc kiem: khong thi mot popup dong dung o
    # vong chot lai bao that bai.
    if not await con_hien():
        return
    raise AdbError(f"Bấm đóng {VONG_DONG_POPUP} lần mà popup {neo!r} vẫn còn.")


async def _don_quang_cao(client, serial: str, metrics, cay: CayUI | None) -> bool:
    """Dong quang cao dang chan duong. True neu co dong duoc gi.

    Chi mau CHAC (hoac bat ky mau nao khi dang dung trong man quang cao): o man
    app, nut "Close" mot chu la nut dong popup cua app - dong nham no la tu tay
    tat cai man dang can do.
    """
    tren_man = await nodes(client, serial, metrics, cay)
    nut = tim_nut_dong(tren_man, chi_chac=True,
                       **await man_chan(client, serial))
    if nut is None:
        return False
    log.info("Don quang cao chan duong bang %s", nut.label)
    await _bam_node(client, serial, nut)
    if cay is not None:
        cay.bo()
    await asyncio.sleep(AD_SETTLE)
    return True


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
    if step.kind == "close_popup":
        # Dong popup theo DANH TINH cua no, khong theo thu tu trong day.
        #
        # Vi sao can rieng mot kind: ba popup o man home (Add Widget, Check-In,
        # rating) deu dat nut X la content-desc="Close". Viet "tap desc=Close"
        # ba lan theo thu tu thi hom nao mot popup khong hien - Check-In chi
        # hien 1 lan/ngay - cu bam do trot xuong popup ke tiep va dong mat
        # chinh cai man dang can do.
        #
        # Khong thay popup KHONG phai loi: popup vang mat la chuyen binh thuong.
        # Don quang cao NGAY TRONG luc cho: paywall len tre thi popup cua app
        # nam duoi no va chua vao cay UI, cho suong het gio la bo qua nham -
        # do duoc, popup Add Widget hien ngay sau khi paywall bi dong.
        if not await wait_text(client, serial, metrics, step.text, step.timeout,
                               cay, don_man_chan=True):
            log.info("Khong thay popup %r - bo qua", step.text)
            return
        await _dong_popup(client, serial, metrics, step.text, cay)
        return

    if step.kind == "intent":
        # Mo thang mot man bang intent. Man Rating o app shortcut khong co nut
        # nao trong app dan sang - day la duong duy nhat toi no.
        await client.start_intent(serial, step.text, step.component)
        await asyncio.sleep(LAUNCH_SETTLE)
        if cay is not None:
            cay.bo()
        return

    if step.kind == "wait_text":
        cho = (step.text, *step.text_alt)
        if not await wait_text(client, serial, metrics, cho, step.timeout, cay):
            ten = " | ".join(repr(x) for x in cho)
            raise AdbError(
                f"Chờ {ten} xuất hiện trong {step.timeout:g}s mà không thấy.")
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
        # Dang dung TRONG man quang cao thi nut "Close" mot chu chac chan la
        # nut dong quang cao - noi long mau o do. Quang cao thuong (rewarded)
        # dat nut dong trong WebView khong co resource_id nao, nen luat "phai
        # co to tien la khung ads" khong bat duoc; do duoc khi di do placement
        # `result`, phai xem ba quang cao thuong moi gen duoc anh.
        # Paywall nhan ra qua ten activity, X tim theo hinh - chay moi thu
        # tieng. Xem `dong_man_chan`.
        await dong_man_chan(client, serial, metrics, cay, step.timeout)
        return

    if step.kind == "tap":
        try:
            await tap(client, serial, await nodes(client, serial, metrics, cay),
                      step.selector)
        except AdbError:
            # Khong thay element: truoc khi bao hut, thu don quang cao chan
            # duong roi bam lai MOT lan. App quang cao day thi lop chen co the
            # len giua hai buoc bat ky - va o duoi quang cao, man dang can van
            # o do. Viec nay thuoc ve moi buoc `tap`, khong phai thu de tung
            # flow tu nho chen `close_ad` vao dung cho.
            if not await _don_quang_cao(client, serial, metrics, cay):
                raise
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
        await asyncio.sleep(SHOT_SETTLE)
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
