"""Render report event thanh HTML tu chua (theo mau tool ad-checklist-diff).

Scorecard: MAU SO la so dong DA KIEM (pass + fail + chua ket luan).
`NOT_TESTED` va `EXTRA` ra chip rieng, KHONG BAO GIO vao mau so va khong vao so
fail - nguyen tac 1 cua repo. Tron vao la bao cao mot ti le sai va lam nguoi doc
tuong app hong nang hon thuc te.

Section chia theo `Screen Name` cua spec - khop dung pattern section-per-muc cua
report ads.
"""

from __future__ import annotations

from .check_models import (FAIL_VERDICTS, CheckResult, Summary, Verdict,
                           verdict_label)
from .event_spec_models import SpecSheet
from .report_event_callouts import _callouts, esc
from .report_event_css import CSS, FONTS

_NO_SCREEN = "Không khai màn"

# verdict -> class CSS. `muted` cho nhung gi KHONG phai loi cua app.
_STATUS = {
    Verdict.PASS: "pass",
    Verdict.NOT_VERIFIABLE: "pending",
    Verdict.NOT_TESTED: "muted",
    Verdict.EXTRA: "muted",
}


def _status_class(verdict: Verdict) -> str:
    return _STATUS.get(verdict, "fail")


def _split_element(element: str) -> tuple[str, str]:
    """'rating_star_clicked.star_value' -> (event, param). Khong co param -> '—'."""
    base, sep, param = element.partition(".")
    return (base, param) if sep else (element, "—")


def _screen_of(spec: SpecSheet) -> dict[str, str]:
    return {e.name: (e.screen or _NO_SCREEN) for e in spec.events}


def _triggered_of(spec: SpecSheet) -> dict[str, str]:
    return {e.name: e.triggered for e in spec.events}


def _row(item: CheckResult, triggered: dict[str, str],
         *, show_event: bool = True) -> str:
    """Mot dong bang. `show_event=False` -> de trong o Event.

    Spec 2 event nhung bang co 5 dong (2 dong event + 3 dong param). Lap ten
    event o moi dong thi doc vao tuong 5 event - da co nguoi doc bao cao roi
    hoi "5 event o dau ra". In ten o dong DAU cua moi event la du.
    """
    event, param = _split_element(item.element)
    base = event.split(" (")[0]
    cls = _status_class(item.verdict)
    note = item.delta or item.message
    return (
        f"<tr{' class=\"row-fail\"' if cls == 'fail' else ''}>"
        + (f"<td class='cell-ev'><code>{esc(event)}</code>"
           f"<span class='trig'>{esc(triggered.get(base, ''))}</span></td>"
           if show_event else "<td class='cell-ev'></td>")
        + f"<td class='cell-mono'>{esc(param)}</td>"
        f"<td class='cell-mono cell-want'>{esc(item.expected or '—')}</td>"
        f"<td class='cell-mono'>{esc(item.actual or '—')}</td>"
        f"<td><span class='status {cls}'><span class='dot'></span>"
        f"{esc(verdict_label(item.verdict))}</span>"
        f"{f'<div class=\"note\">{esc(note)}</div>' if note else ''}</td></tr>"
    )


def _section(name: str, rows: list[CheckResult], triggered: dict[str, str]) -> tuple[str, str]:
    checked = [r for r in rows if r.verdict not in
               (Verdict.NOT_TESTED, Verdict.EXTRA)]
    ok = sum(1 for r in checked if r.verdict is Verdict.PASS)
    level = ("fail" if any(r.verdict in FAIL_VERDICTS for r in rows)
             else "pass" if checked and ok == len(checked) else "pending")
    # Xep lai theo EVENT roi moi den param cua no, giu thu tu event nhu ban
    # dau. Truoc day sap theo loai check nen dong presence cua ca hai event
    # nam canh nhau roi moi den cac dong param - doc kieu do phai nhay mat len
    # xuong de biet param nao cua event nao.
    nhom: dict[str, list[CheckResult]] = {}
    for item in rows:
        nhom.setdefault(_split_element(item.element)[0], []).append(item)
    parts = []
    for ten, cua_event in nhom.items():
        # Dong khong co param (kiem event co ban khong) len truoc.
        cua_event.sort(key=lambda r: _split_element(r.element)[1] != "—")
        for thu_tu, item in enumerate(cua_event):
            parts.append(_row(item, triggered, show_event=thu_tu == 0))
    body = "".join(parts)
    # Mau so 0 nghia la ca man CHUA test dong nao. In "0/0 khop" thi nguoi doc
    # khong hieu gi; noi thang "chua test" moi dung viec da xay ra.
    if not checked:
        level, tally = "pending", f"chưa test ({len(rows)})"
    else:
        tally = f"{ok}/{len(checked)} khớp"
    bang = (
        f"<div class='table-scroll'><table><thead><tr><th>Event</th><th>Param</th>"
        f"<th>Spec cần</th><th>App gửi</th><th>Kết quả</th></tr></thead>"
        f"<tbody>{body}</tbody></table></div>"
    )
    # Spec de trong cot Screen Name -> khong co gi de nhom, va mot nhom ten
    # "Khong khai man" chi noi ve chinh cai bang spec chu khong noi gi ve app.
    # Bo ca chip lan tieu de, hien thang bang.
    if name == _NO_SCREEN:
        return "", f"<div class='section'>{bang}</div>"

    chip = f"<span class='section-chip {level}'>{esc(name)} <b>{esc(tally)}</b></span>"
    section = (
        f"<details class='section' open><summary>"
        f"<span class='section-title'>{esc(name)}</span>"
        f"<span class='section-frac {level}'>{esc(tally)}</span></summary>"
        f"{bang}</details>"
    )
    return chip, section


def build(spec: SpecSheet, results: list[CheckResult], summary: Summary, *,
          package: str = "", generated_at: str = "", event_count: int = 0,
          fa_silent: bool = False, stream_died: bool = False,
          app_seen: bool = True, foreground: str = "",
          checked_package: str = "",
          near_edge: tuple[str, ...] = (),
          quick: bool = False) -> str:
    screens = _screen_of(spec)
    triggered = _triggered_of(spec)

    grouped: dict[str, list[CheckResult]] = {}
    for item in results:
        if item.verdict is Verdict.EXTRA:
            continue          # da vao callout, khong lam loang bang
        event = _split_element(item.element)[0].split(" (")[0]
        grouped.setdefault(screens.get(event, _NO_SCREEN), []).append(item)

    chips, sections = [], []
    for name, rows in grouped.items():
        chip, section = _section(name, rows, triggered)
        if chip:
            chips.append(chip)
        sections.append(section)

    checked = summary.total_checked
    pct = round(summary.passed / checked * 100) if checked else 0
    tallies = []
    if summary.failed:
        tallies.append(f"<span class='section-chip fail'>sai <b>{summary.failed}</b></span>")
    if summary.not_verifiable:
        tallies.append("<span class='section-chip pending'>chưa kết luận "
                       f"<b>{summary.not_verifiable}</b></span>")
    if summary.not_tested:
        tallies.append(f"<span class='section-chip'>chưa test <b>{summary.not_tested}</b></span>")
    if summary.extra:
        tallies.append(f"<span class='section-chip'>app có thêm <b>{summary.extra}</b></span>")

    return f"""<title>Event Tracking Diff</title>
{FONTS}
{CSS}
<div class="wrap">
  <header class="report-head">
    <p class="eyebrow">Event Tracking · Firebase Analytics</p>
    <h1>Event Tracking Diff</h1>
    <p class="meta">{esc(package)} · <b>{len(spec.events)} event trong spec</b>
      · {checked} mục đã kiểm · {event_count} event đọc được từ logcat
      {f'· {esc(generated_at)}' if generated_at else ''}</p>
    <div class="scorecard">
      <div class="score-row"><span class="score-num">{summary.passed}</span>
        <span class="score-den">/ {checked} khớp</span></div>
      <div class="score-bar"><div class="score-bar-fill" style="width:{pct}%"></div></div>
      <div class="tallies">{''.join(tallies)}</div>
    </div>
    <div class="section-chips">{''.join(chips)}</div>
  </header>
  {_callouts(results, fa_silent, near_edge, quick, stream_died, app_seen,
               foreground, package, checked_package)}
  <div class="sections">{''.join(sections)}</div>
</div>
"""
