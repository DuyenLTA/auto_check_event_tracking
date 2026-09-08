"""Chay cac check event roi tong hop Summary.

Vi sao KHONG dung check_runner._REGISTRY: `check_runner.run` nhan MatchResult -
cac cap (design node, device node) da ghep. Check event nhan SpecSheet + cac cua
so log, la mot hinh dang dau vao khac han. Nhoi vao mot registry chung thi phai
bop meo mot trong hai ben.

Dung lai `CheckResult`, `Summary`, `CheckConfig` va `sort_for_report` - tu vung
verdict o mot cho duy nhat (check_models). Chi tang DIEU PHOI la rieng.
"""

from __future__ import annotations

from .check_config import CheckConfig
from .check_models import CheckResult, Summary
from .check_sort import sort_for_report
from .checks import event_params, event_presence
from .event_spec_models import SpecSheet
from .event_window import Window

_REGISTRY = {
    "event_presence": event_presence.run,
    "event_params": event_params.run,
}


def available_checks() -> list[str]:
    return list(_REGISTRY)


def run(spec: SpecSheet, windows: tuple[Window, ...], config: CheckConfig,
        *, fa_silent: bool = False) -> tuple[list[CheckResult], Summary]:
    results: list[CheckResult] = []
    for name, run_check in _REGISTRY.items():
        if not config.enabled(name):
            continue
        results.extend(run_check(spec, windows, config, fa_silent=fa_silent))

    ordered = sort_for_report(results)
    summary = Summary()
    for item in ordered:
        summary.add(item)
    return ordered, summary
