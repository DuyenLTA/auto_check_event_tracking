"""Render report event thanh HTML tu chua.

Bo cuc (giong report rc-check tester da chot):
    header -> 2 the dem EVENT Sai / Khop (bam de loc) -> bang do neu luot
    chua xong -> khoi "can xu ly" -> canh bao -> thanh loc -> danh sach event
    gap/mo chia nhom Sai / Khop. Khong co muc anh chup (tester bo 05/10/2026).

Truoc day la mot bang ngang moi dong mot param, chia section theo Screen Name:
spec 62 event ra ~210 dong va dong sai duy nhat nam lan giua. Nguoi doc can
biet ngay CAI GI SAI, nen sai len dau va mo san, khop gap lai o cuoi.

So dem: the dem EVENT, dong `counts` dem MUC (event + param). Mau so cua muc la
so DA KIEM - `NOT_TESTED` va `EXTRA` khong bao gio vao mau so va khong vao so
fail (nguyen tac 1 cua repo).
"""

from __future__ import annotations

from .check_models import CheckResult, Summary
from .event_spec_models import SpecSheet
from .report_event_callouts import _callouts, esc
from .report_event_css import CSS, FONTS
from .report_event_filter_js import JS
from .report_event_list_css import LIST_CSS
from .report_event_list_html import (BUCKETS, group_events, render_list,
                                     render_todo, render_unfinished)
from .report_event_triage_html import triage_callout

_TILE_LABEL = {"fail": "event sai", "pass": "event khớp"}


def _tiles(groups) -> str:
    out = []
    for key, _, _ in BUCKETS:
        n = sum(1 for g in groups if g.bucket == key)
        out.append(f"<button class='tile {key}' data-f='{key}' aria-pressed='false'>"
                   f"<span class='num'>{n}</span>"
                   f"<span class='lab'>{_TILE_LABEL[key]}</span></button>")
    return f"<div class='tiles'>{''.join(out)}</div>"


def _bar() -> str:
    chips = "<button class='fchip' data-f='all' aria-pressed='true'>Tất cả</button>" + "".join(
        f"<button class='fchip' data-f='{k}' aria-pressed='false'>{esc(nhan)}</button>"
        for k, _, nhan in BUCKETS)
    return (
        f"<div class='bar' role='toolbar' aria-label='Lọc event'>{chips}"
        "<input class='search' id='evQ' type='search' placeholder='Tìm event, màn…' "
        "aria-label='Tìm event'>"
        "<button class='linkbtn' id='evAll'>Mở tất cả</button>"
        "<span class='cnt' id='evCount'></span></div>")


def build(spec: SpecSheet, results: list[CheckResult], summary: Summary, *,
          package: str = "", generated_at: str = "", event_count: int = 0,
          fa_silent: bool = False, stream_died: bool = False,
          app_seen: bool = True, foreground: str = "",
          checked_package: str = "",
          near_edge: tuple[str, ...] = (),
          quick: bool = False, triage=None,
          app_version: str = "") -> str:
    screens = {e.name: e.screen for e in spec.events}
    triggered = {e.name: e.triggered for e in spec.events}
    groups = group_events(results)
    # Event ngoai spec (ad_load, screen_view...) bat sat moc cung khong duoc
    # cham, liet ke ra chi lam loang canh bao.
    near_edge = tuple(n for n in near_edge if n in screens)

    checked = summary.total_checked
    # MAU SO la so muc DA KIEM. De tran "1 / 1 khop" thi nguoi doc tuong ca
    # spec da xanh - noi luon so chua test ngay canh.
    chua_test = f" · {summary.not_tested} chưa test" if summary.not_tested else ""
    sai = f" · {summary.failed} sai" if summary.failed else ""

    return f"""<title>Event Tracking Diff</title>
{FONTS}
{CSS}
{LIST_CSS}
<div class="wrap">
  <header class="report-head">
    <p class="eyebrow">Event Tracking · Firebase Analytics</p>
    <h1>Event Tracking Diff</h1>
    <p class="meta">{esc(package)}{f' · bản <b>{esc(app_version)}</b>' if app_version else ''}
      · <b>{len(spec.events)} event trong spec</b>
      · {event_count} event đọc được từ logcat
      {f'· {esc(generated_at)}' if generated_at else ''}</p>
    {_tiles(groups)}
    <p class="counts">Theo mục (event + param): {summary.passed} khớp / {checked} mục đã kiểm{sai}{chua_test}</p>
  </header>
  {render_unfinished(groups)}
  {render_todo(groups)}
  {_callouts(results, fa_silent, near_edge, quick, stream_died, app_seen,
             foreground, package, checked_package)}
  {triage_callout(triage)}
  {_bar()}
  <div class="sections">{render_list(groups, screens, triggered, triage)}
    <div class="empty" id="evEmpty" hidden>Không có event nào khớp bộ lọc.</div></div>
</div>
{JS}
"""
