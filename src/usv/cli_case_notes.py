"""Vi sao mot event ra NOT_TESTED: chua co flow, hay lai hut giua duong.

`event_presence` chi biet "khong co cua so nao mang ten event nay" nen no viet
message theo duong web (bam nut, lam dong tac). Duong CLI thi BIET ly do that:
flow khong co case nao cho event do, hay case co chay ma step chet o dau. Doi
message lai la khac nhau giua mot bao cao dung duoc va mot bao cao bat nguoi
doc tu di mo log ra dem.

Chi doi `message`, TUYET DOI khong doi `verdict`: NOT_TESTED khong bao gio duoc
bien thanh FAIL chi vi may khong lai toi noi.
"""

from __future__ import annotations

from dataclasses import replace

from .check_models import CheckResult, Verdict
from .event_flow_run import CaseResult

CHUA_CO_FILE = ("Chưa có file flow cho app này nên tool chưa lái tới màn đó — "
                "chưa đo gì cả. Tạo flow bằng `record` rồi chạy lại.")
CHUA_CO_CASE = ("Chưa có case nào cho event này trong {flows} — tool chưa lái "
                "tới màn đó. Thêm một case rồi chạy lại.")


def drop_windows(windows: tuple, case_results: list[CaseResult]) -> tuple:
    """Bo cua so cua case KHONG chay xong.

    Moc duoc chen TRUOC khi chay step, nen mot case chet o step 2 van de lai
    mot cua so nhin y het cua so that. Giu lai la cham mot man chua bao gio lai
    toi: app khong ban event o do -> FAIL_MISSING oan, ma app co ban vi ly do
    khac -> PASS gia. Ca hai deu sai, va deu im lang.
    """
    hut = {(item.case.event, item.case.label)
           for item in case_results if not item.ran}
    return tuple(w for w in windows if (w.spec_event, w.note) not in hut)


def _ly_do(cases: list[CaseResult]) -> str:
    """Gop ly do cua cac case cung mot event. Case chay duoc thi khong gop."""
    phan = []
    for item in cases:
        if item.ran:
            continue
        dau = "Tiền đề chưa đạt" if item.status == "blocked" else "Lái hụt"
        nhan = item.case.label
        phan.append(f"{dau} ở case {nhan!r}: {item.reason}")
    return " | ".join(phan)


def annotate(results: list[CheckResult], case_results: list[CaseResult], *,
             flows: str = "", co_flow: bool = True) -> list[CheckResult]:
    """Viet lai message cho moi dong NOT_TESTED cua check `event_presence`."""
    theo_event: dict[str, list[CaseResult]] = {}
    for item in case_results:
        theo_event.setdefault(item.case.event, []).append(item)

    ra: list[CheckResult] = []
    for row in results:
        if row.verdict is not Verdict.NOT_TESTED or row.check != "event_presence":
            ra.append(row)
            continue
        cases = theo_event.get(row.element, [])
        if not cases:
            message = CHUA_CO_FILE if not co_flow else \
                CHUA_CO_CASE.format(flows=flows or "file flow")
        else:
            message = _ly_do(cases) or row.message
        ra.append(replace(row, message=message))
    return ra
