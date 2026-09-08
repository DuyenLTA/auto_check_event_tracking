"""Tu vung ket qua kiem tra: Verdict, CheckResult, Summary.

Tu vung verdict nam MOT CHO - module khac chi dung lai, khong dinh nghia them.

BA NGUYEN TAC bat di bat dich:

1. EXTRA va NOT_TESTED KHONG BAO GIO tinh vao `fail`. Event app ban ma spec
   khong khai co the la spec chua cap nhat; event chua danh dau buoc nao thi
   tool chua do gi ca. Ca hai deu khong phai loi cua app, va fail oan mot loat
   la cach nhanh nhat de tester bo khong dung tool nua.

2. Khong verify duoc thi noi khong verify duoc (NOT_VERIFIABLE), khong pass gia.
   Vd kieu String vs Number: logcat in Long 3 va chuoi "3" y het nhau.

3. Moi CheckResult phai co `message` doc duoc, khong phai dump so.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Verdict(StrEnum):
    PASS = "PASS"
    FAIL_MISSING = "FAIL_MISSING"        # spec khai ma app khong ban / khong gui
    FAIL_VALUE = "FAIL_VALUE"            # gia tri ngoai danh sach spec cho phep
    FAIL_TYPE = "FAIL_TYPE"              # spec Number ma app ban chu
    FAIL_DUPLICATE = "FAIL_DUPLICATE"    # mot buoc ma event ban nhieu lan
    FAIL_PARAM_EXTRA = "FAIL_PARAM_EXTRA"  # app gui param spec khong khai
    NOT_VERIFIABLE = "NOT_VERIFIABLE"    # logcat khong phan biet duoc String/Number
    NOT_TESTED = "NOT_TESTED"            # chua danh dau buoc nao - KHONG phai fail
    EXTRA = "EXTRA"                      # app co, spec khong khai


# Nhan tieng Viet de hien cho nguoi doc. GIA TRI enum giu nguyen dang ma
# ("FAIL_VALUE"): no di vao file xlsx xuat ra, vao test, va vao report da luu -
# doi gia tri se lam cac ban cu doc khong khop nua. Chi doi CACH IN.
VERDICT_LABEL = {
    Verdict.PASS: "Khớp",
    Verdict.FAIL_MISSING: "Thiếu",
    Verdict.NOT_VERIFIABLE: "Chưa kết luận",
    Verdict.EXTRA: "App có thêm",
    Verdict.FAIL_VALUE: "Sai giá trị",
    Verdict.FAIL_TYPE: "Sai kiểu",
    Verdict.FAIL_DUPLICATE: "Bắn trùng",
    Verdict.FAIL_PARAM_EXTRA: "Thừa param",
    Verdict.NOT_TESTED: "Chưa test",
}


def verdict_label(verdict: "Verdict") -> str:
    """Nhan cho nguoi doc; roi ve chinh ma neu gap verdict la."""
    return VERDICT_LABEL.get(verdict, str(verdict))


# Nhom verdict -> mau, dung chung cho web UI va report HTML.
FAIL_VERDICTS = frozenset({
    Verdict.FAIL_MISSING, Verdict.FAIL_VALUE, Verdict.FAIL_TYPE,
    Verdict.FAIL_DUPLICATE, Verdict.FAIL_PARAM_EXTRA,
})

VERDICT_ICON = {
    Verdict.PASS: "🟢",
    Verdict.NOT_VERIFIABLE: "🟡",
    Verdict.EXTRA: "➕",
    Verdict.NOT_TESTED: "⬜",
}


def icon(verdict: Verdict) -> str:
    return VERDICT_ICON.get(verdict, "🔴")


@dataclass(frozen=True, slots=True)
class CheckResult:
    """Mot ket luan ve mot thuoc tinh cua mot element."""

    element: str                 # ten design node, hoac resource-id khi la EXTRA
    check: str                   # presence | order | text | size | gap | padding | color
    verdict: Verdict
    expected: str = ""
    actual: str = ""
    delta: str = ""              # "lech +4dp" - de doc, khong phai so tho
    message: str = ""
    device_label: str = ""
    confidence: float = 1.0
    tier: int = -1

    @property
    def failed(self) -> bool:
        return self.verdict in FAIL_VERDICTS

    def payload(self) -> dict:
        return {
            "element": self.element,
            "check": self.check,
            "verdict": str(self.verdict),
            "icon": icon(self.verdict),
            "expected": self.expected,
            "actual": self.actual,
            "delta": self.delta,
            "message": self.message,
            "device": self.device_label,
            "confidence": self.confidence,
            "tier": self.tier,
        }


@dataclass(slots=True)
class Summary:
    """Con so tren dau report. `fail` KHONG gom extra/not_tested (nguyen tac 1)."""

    passed: int = 0
    failed: int = 0
    not_verifiable: int = 0
    extra: int = 0
    not_tested: int = 0
    by_check: dict[str, int] = field(default_factory=dict)
    by_verdict: dict[str, int] = field(default_factory=dict)

    @property
    def total_checked(self) -> int:
        return self.passed + self.failed + self.not_verifiable

    @property
    def pass_ratio(self) -> float:
        base = self.passed + self.failed
        return round(self.passed / base, 3) if base else 0.0

    def add(self, result: CheckResult) -> None:
        self.by_verdict[str(result.verdict)] = self.by_verdict.get(str(result.verdict), 0) + 1
        if result.verdict is Verdict.EXTRA:
            self.extra += 1
            return
        # Return som nhu unmatched/extra, va vi DUNG mot ly do: chua danh dau
        # buoc nao cho event nay thi tool chua do gi ca. Roi xuong nhanh `else`
        # phia duoi la bi dem thanh FAIL - nguyen tac 1.
        if result.verdict is Verdict.NOT_TESTED:
            self.not_tested += 1
            return
        self.by_check[result.check] = self.by_check.get(result.check, 0) + 1
        if result.verdict is Verdict.PASS:
            self.passed += 1
        elif result.verdict is Verdict.NOT_VERIFIABLE:
            self.not_verifiable += 1
        else:
            self.failed += 1

    def headline(self) -> str:
        return (
            f"{self.passed} pass / {self.failed} fail / "
            f"{self.not_verifiable} khong verify duoc / "
            f"{self.extra} spec khong khai / "
            f"{self.not_tested} chua test"
        )

    def payload(self) -> dict:
        return {
            "pass": self.passed,
            "fail": self.failed,
            "not_verifiable": self.not_verifiable,
            "extra": self.extra,
            "not_tested": self.not_tested,
            "total_checked": self.total_checked,
            "pass_ratio": self.pass_ratio,
            "by_check": self.by_check,
            "by_verdict": self.by_verdict,
            "headline": self.headline(),
        }
