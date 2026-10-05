"""Check event_timing: event co ban DUNG LUC cu bam kich hoat khong.

`event_presence` chi noi event co ban trong cua so case - ca case co the dai
60s (mo app, qua splash, onboarding roi moi bam). App ban `setting_click` tu
luc vua vao Home, chua ai bam gi, thi presence van PASS. Check nay do tu MOC
CU BAM (`@bấm`, ghi ngay truoc lenh input cua buoc kich hoat) toi luc event
ban:

    tre < -SAI_SO_MS            -> FAIL_TIMING: ban TRUOC khi bam
    tre > nguong                -> FAIL_TIMING: ban tre qua nguong
    con lai                     -> PASS, ghi "ban sau cu bam X ms"

Nguong: case khai `max_delay_ms` thi dung no (event cho server tra ve, vd
report_submit, download luu xong, gen_*), khong thi theo config - event
`*_view` (man hien ra) rong hon event bam nut.

Cua so khong co moc cu bam (case khong co buoc kich hoat chay duoc) thi KHONG
ra dong nao - presence van noi event co ban hay khong.
"""

from __future__ import annotations

from ..check_models import CheckResult, Verdict
from ..event_spec_models import SpecSheet
from ..event_window import AFTER_PREFIX, Window, to_ms

# Moc ghi bang lenh adb rieng, chay TRUOC lenh input vai chuc ms; event ban
# ngay khi bam co the in som hon moc mot chut do hai tien trinh log. Sai so
# nho nay khong phai "ban truoc khi bam".
SAI_SO_MS = 150.0


def run(spec: SpecSheet, windows: tuple[Window, ...], config, *,
        fa_silent: bool = False, stream_died: bool = False,
        app_seen_running: bool = True, session_events: tuple = ()) -> list[CheckResult]:
    if not app_seen_running:
        return []
    setting = config.checks.get("event_timing")
    options = setting.options if setting else {}
    click_ms = float(options.get("click_max_ms", 1500))
    view_ms = float(options.get("view_max_ms", 5000))
    seen_min = float(options.get("seen_min_ms", -3500))
    seen_max = float(options.get("seen_max_ms", 1000))
    known = {e.name for e in spec.events}
    out: list[CheckResult] = []
    for window in windows:
        if window.spec_event not in known or window.tap_ms is None:
            continue
        hits = window.named(window.spec_event)
        if not hits:
            continue                     # presence da bao thieu
        stamp = to_ms(hits[0].timestamp)
        if stamp is None:
            continue
        tre = stamp - window.tap_ms
        buoc = window.tap_step or "bước kích hoạt"
        san = -SAI_SO_MS
        if buoc.startswith("wait_text"):
            # Moc = luc TOOL THAY man (dump ~2.2s/lan) -> tool thay tre hon app
            # ve man. Event *_view ban luc man hien nen duoc phep TRUOC moc.
            san, nguong = seen_min, seen_max
            mong = f"bắn trong [{seen_min:g}, +{seen_max:g}] ms quanh lúc màn hiện (`{buoc}`)"
        else:
            nguong = window.max_delay_ms if window.max_delay_ms is not None else (
                view_ms if window.spec_event.endswith("_view") else click_ms)
            if buoc.startswith(AFTER_PREFIX):
                san = 0.0
            mong = f"bắn trong {nguong:g} ms sau `{buoc}`"
        if window.max_delay_ms is not None:
            nguong = window.max_delay_ms
        label = f"{window.spec_event} (thời điểm" + (
            f" · {window.note})" if window.note else ")")
        if tre < san:
            out.append(CheckResult(
                element=label, check="event_timing", verdict=Verdict.FAIL_TIMING,
                expected=mong, actual=f"bắn TRƯỚC cú bấm {-tre:.0f} ms",
                delta=f"{tre:+.0f} ms",
                message=(f"Event bắn {-tre:.0f} ms TRƯỚC khi tool bấm `{buoc}` — "
                         "app bắn sai lúc, không phải do cú bấm này.")))
        elif tre > nguong:
            out.append(CheckResult(
                element=label, check="event_timing", verdict=Verdict.FAIL_TIMING,
                expected=mong, actual=f"bắn sau cú bấm {tre:.0f} ms",
                delta=f"+{tre - nguong:.0f} ms quá ngưỡng",
                message=(f"Event bắn {tre:.0f} ms sau cú bấm `{buoc}`, quá ngưỡng "
                         f"{nguong:g} ms. Nếu event chờ server/xử lý thì khai "
                         "`max_delay_ms` cho case.")))
        else:
            out.append(CheckResult(
                element=label, check="event_timing", verdict=Verdict.PASS,
                expected=mong, actual=(f"bắn sau mốc {tre:.0f} ms" if tre >= 0 else
                                       f"bắn trước lúc tool thấy màn {-tre:.0f} ms"),
                message=(f"Event bắn {tre:.0f} ms so với `{buoc}`." if tre < 0 else
                         f"Event bắn {tre:.0f} ms sau `{buoc}`.")))
    return out
