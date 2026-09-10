"""Check event_presence: event co ban khong, va co ban trung khong.

Ba muc ket luan, va cai thu ba la quan trong nhat:
  - co cua so, ban 1 lan          -> PASS
  - co cua so, ban 0 lan          -> FAIL_MISSING
  - co cua so, ban >1 lan         -> FAIL_DUPLICATE
  - KHONG cua so nao              -> NOT_TESTED (tester chua danh dau buoc)

NOT_TESTED khong phai fail: tool chua do gi ca thi khong duoc ket luan gi ve app.
Khong do duoc thi khong ket luan - khong bao fail.

BAN TRUNG cham theo TUNG CUA SO, khong theo ca phien. Do that: `track_ad_request`
ban 17 lan trong mot lan mo app la binh thuong. Cham theo phien la bao oan.
"""

from __future__ import annotations

from ..check_models import CheckResult, Verdict
from ..event_spec_models import SpecSheet
from ..event_window import Window


def run(spec: SpecSheet, windows: tuple[Window, ...], config,
        *, fa_silent: bool = False, stream_died: bool = False,
        app_seen_running: bool = True) -> list[CheckResult]:
    setting = config.checks.get("event_presence")
    catch_duplicate = bool(setting.options.get("duplicate", True)) if setting else True

    out: list[CheckResult] = []
    by_event: dict[str, list[Window]] = {}
    for window in windows:
        by_event.setdefault(window.spec_event, []).append(window)

    if not app_seen_running:
        # Phai chan o NGOAI cung, truoc ca nhanh "co thay event": log FA-SVC do
        # Google Play Services in ra, KHONG phai process cua app (do tren may:
        # PID app 4524, moi dong "Logging event:" mang PID 31649 =
        # com.google.android.gms). Nen logcat khong noi duoc event thuoc app
        # nao. App khong he chay thi khong con gi de gan - "thay event" luc do
        # la thay event cua app KHAC, va bao PASS la PASS GIA.
        return [CheckResult(
            element=event.name, check="event_presence",
            verdict=Verdict.NOT_VERIFIABLE, expected="event được bắn ra",
            message=("App dưới test không chạy lần nào trong phiên ghi. Log "
                     "Firebase do Google Play Services in ra nên không cho "
                     "biết event thuộc app nào — event bắt được ở đây là của "
                     "app khác, không kết luận được gì về app này. Kiểm lại "
                     "tên package, và mở app SAU khi bấm Ghi."),
        ) for event in spec.events]

    for event in spec.events:
        found = by_event.get(event.name, [])
        if not found:
            out.append(CheckResult(
                element=event.name, check="event_presence",
                verdict=Verdict.NOT_TESTED,
                expected="event được bắn ra",
                message=("Chưa đánh dấu bước nào cho event này nên tool chưa đo "
                         "gì — không kết luận được. Bấm nút "
                         f"{event.triggered or event.name!r} rồi làm động tác đó."),
            ))
            continue

        for window in found:
            hits = window.named(event.name)
            label = _label(event.name, window, len(found))
            if not hits:
                # fa_silent: khong doc duoc log Firebase thi khong the noi app
                # thieu event. Phan biet hai chuyen nay la ly do R3 ton tai.
                if stream_died:
                    # Phien ghi chet giua duong (rut may/adb dut) nen phan sau
                    # khong duoc ghi. "Khong thay event" luc nay khong noi gi
                    # ve app. Dat TRUOC fa_silent: dut stream la ly do manh hon.
                    out.append(CheckResult(
                        element=label, check="event_presence",
                        verdict=Verdict.NOT_VERIFIABLE,
                        expected="event được bắn ra",
                        message=("Phiên ghi bị đứt giữa đường (máy rớt khỏi "
                                 "USB hoặc adb dừng) nên phần sau không được "
                                 "ghi — không kết luận được là app thiếu "
                                 "event. Cắm lại máy và ghi lại."),
                    ))
                    continue
                if fa_silent:
                    out.append(CheckResult(
                        element=label, check="event_presence",
                        verdict=Verdict.NOT_VERIFIABLE,
                        expected="event được bắn ra",
                        message=("Không đọc được dòng log FA-SVC nào trong cả "
                                 "phiên ghi — rất có thể build này strip log "
                                 "Firebase, chứ không phải app thiếu event."),
                    ))
                    continue
                out.append(CheckResult(
                    element=label, check="event_presence",
                    verdict=Verdict.FAIL_MISSING,
                    expected="event được bắn ra", actual="không bắn",
                    message=(f"Bước này có {len(window.app_events)} event khác "
                             f"được bắn nhưng không có {event.name!r}."),
                ))
                continue

            if len(hits) > 1 and catch_duplicate:
                stamps = ", ".join(h.timestamp for h in hits)
                out.append(CheckResult(
                    element=label, check="event_presence",
                    verdict=Verdict.FAIL_DUPLICATE,
                    expected="bắn 1 lần", actual=f"bắn {len(hits)} lần",
                    delta=f"thừa {len(hits) - 1} lần",
                    message=(f"Trong một bước mà bắn {len(hits)} lần, vào lúc "
                             f"{stamps}. Nếu app có retry thì tắt "
                             "`event_presence.duplicate` trong YAML."),
                ))
                continue

            out.append(CheckResult(
                element=label, check="event_presence", verdict=Verdict.PASS,
                expected="event được bắn ra", actual=f"bắn lúc {hits[0].timestamp}",
                message="Event được bắn đúng ở bước này.",
            ))

    return out


def _label(name: str, window: Window, total: int) -> str:
    """Cung mot event test o nhieu buoc thi phai phan biet duoc trong report."""
    if total <= 1 or not window.note:
        return name
    return f"{name} ({window.note})"
