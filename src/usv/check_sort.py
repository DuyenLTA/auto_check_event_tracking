"""Thu tu hien ket qua trong report: viec can lam len dau."""

from __future__ import annotations

from .check_models import CheckResult, Verdict

# Fail len dau - tester mo report la thay ngay viec can lam.
# Thu tu: FAIL -> NOT_VERIFIABLE -> NOT_TESTED -> EXTRA -> PASS.
_RANK = {
    Verdict.NOT_VERIFIABLE: 1,
    Verdict.NOT_TESTED: 2,
    Verdict.EXTRA: 3,
    Verdict.PASS: 4,
}


def sort_for_report(results: list[CheckResult]) -> list[CheckResult]:
    return sorted(results, key=lambda r: (_RANK.get(r.verdict, 0), r.check, r.element))
