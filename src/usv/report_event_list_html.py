"""Danh sach event gap/mo, chi HAI nhom: Sai -> Khop.

Tester chot 05/10/2026: report chi co pass/fail. "Chua test" / "chua ket luan"
khong phai ket luan ve app ma la viec agent chua lam xong (lai hut thi lai lai,
chua chac thi do tren may). Event con dong nhu vay KHONG vao danh sach - no ra
bang do "luot chua xong" o dau trang (`render_unfinished`), va workflow cam
publish ban do.

Truoc day la MOT bang ngang 5 cot, moi dong mot param: spec 62 event ra ~210
dong, dong sai duy nhat lan giua 200 dong khop va nguoi doc phai keo het trang
moi biet co gi can xu ly. Gio don vi la EVENT: mot dong tom tat, mo ra moi thay
tung param. Event sai mo san va nam tren cung; event khop gap lai o cuoi.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .check_models import FAIL_VERDICTS, CheckResult, Verdict, verdict_label
from .report_event_callouts import esc
from .report_event_row_collapse import gop_dong_trung
from .report_event_triage_html import triage_block

# (khoa nhom, tieu de nhom, nhan ngan tren pill). Thu tu = thu tu hien.
BUCKETS = (
    ("fail", "Sai — cần báo dev", "Sai"),
    ("pass", "Khớp spec", "Khớp"),
)
BUCKET_LABEL = {k: nhan for k, _, nhan in BUCKETS}

# verdict -> class CSS cua tung dong. `muted` cho nhung gi KHONG phai loi app.
_STATUS = {
    Verdict.PASS: "pass",
    Verdict.NOT_VERIFIABLE: "pending",
    Verdict.NOT_TESTED: "muted",
    Verdict.EXTRA: "muted",
}


def status_class(verdict: Verdict) -> str:
    return _STATUS.get(verdict, "fail")


def split_element(element: str) -> tuple[str, str]:
    """'rating_star_clicked.star_value' -> (event, param). Khong co param -> '—'."""
    base, sep, param = element.partition(".")
    return (base, param) if sep else (element, "—")


def context_of(item: CheckResult) -> str:
    """'picker_done (chon video luong Edit Video)' -> 'chon video luong Edit Video'.

    Mot event cham o nhieu buoc thi tool gan ten buoc vao sau ten event. Gop ve
    MOT event (spec dem 62 thi the dem cung phai ra tren 62, khong phai 76) va
    in ten buoc o tung dong de van biet dong nao cua buoc nao.
    """
    _, sep, ctx = split_element(item.element)[0].partition(" (")
    return ctx[:-1] if sep and ctx.endswith(")") else ""


@dataclass
class EventGroup:
    """Moi dong ket qua cua mot event (gop ca bien the '(buoc ...)')."""
    label: str
    rows: list[CheckResult] = field(default_factory=list)

    @property
    def base(self) -> str:
        return self.label

    @property
    def bucket(self) -> str:
        """'fail' / 'pass' / 'unfinished'. Co dong chua do thi KHONG xep vao
        Khop: 'khop' ma con param chua cham la PASS hut."""
        verdicts = {r.verdict for r in self.rows}
        if verdicts & FAIL_VERDICTS:
            return "fail"
        if verdicts <= {Verdict.PASS}:
            return "pass"
        return "unfinished"

    def tally(self) -> str:
        ok = sum(1 for r in self.rows if r.verdict is Verdict.PASS)
        return f"{ok}/{len(self.rows)} khớp"

    def reason(self) -> str:
        """Mot cau ngan cho dong tom tat va khoi 'can xu ly': dong xau nhat."""
        if self.bucket == "pass":
            return ""
        worst = next(r for r in self.rows if r.verdict is not Verdict.PASS)
        _, param = split_element(worst.element)
        ai = "event" if param == "—" else param
        if ctx := context_of(worst):
            ai += f" ({ctx})"
        cau = (worst.delta or worst.message or worst.actual or "").splitlines()
        return f"{ai}: {verdict_label(worst.verdict)}" + (f" — {cau[0]}" if cau else "")


def group_events(results: list[CheckResult]) -> list[EventGroup]:
    nhom: dict[str, EventGroup] = {}
    for item in results:
        if item.verdict is Verdict.EXTRA:
            continue          # da vao callout, khong lam loang danh sach
        label = split_element(item.element)[0].split(" (")[0]
        nhom.setdefault(label, EventGroup(label)).rows.append(item)
    return list(nhom.values())


def anchor(group: EventGroup) -> str:
    return "ev-" + "".join(c if c.isalnum() else "-" for c in group.label)


def _line(item: CheckResult, so_lan: int, triage) -> str:
    """Mot param: nhan + ten, roi App gui / Spec can / ghi chu cua CHINH dong do."""
    _, param = split_element(item.element)
    cls = status_class(item.verdict)
    note = item.delta or item.message
    ghi_chu = triage.cho(item.element) if triage and item.failed else None
    lap = (f"<span class='times' title='{so_lan} case cho ra dòng giống hệt nhau'>"
           f"×{so_lan}</span>" if so_lan > 1 else "")
    ten = "event được bắn" if param == "—" else param
    ctx = context_of(item)
    return (
        f"<li{' class=\"row-fail\"' if cls == 'fail' else ''}>"
        f"<div class='line-head'><span class='status {cls}'><span class='dot'></span>"
        f"{esc(verdict_label(item.verdict))}</span>"
        f"<span class='pname'>{esc(ten)}</span>{lap}"
        + (f"<span class='ctx'>bước: {esc(ctx)}</span>" if ctx else "") + "</div>"
        f"<dl class='kv'><dt>App gửi</dt><dd>{esc(item.actual or '—')}</dd>"
        f"<dt>Spec cần</dt><dd>{esc(item.expected or '—')}</dd></dl>"
        + (f"<div class='note'>{esc(note)}</div>" if note else "")
        + f"{triage_block(ghi_chu)}</li>"
    )


def _event(group: EventGroup, screen: str, triggered: str, triage) -> str:
    # Dong sai len dau (khong phai luot qua 4 dong khop moi thay), roi theo
    # buoc, roi dong presence truoc param - dong cung buoc nam lien nhau.
    rows = sorted(group.rows, key=lambda r: (not r.failed, context_of(r),
                                             split_element(r.element)[1] != "—"))
    lines = "".join(_line(item, n, triage) for item, n in gop_dong_trung(rows))
    b = group.bucket
    ctxs = dict.fromkeys(context_of(r) for r in group.rows)
    hay = " ".join(x for x in (group.label, screen, triggered, *ctxs) if x).lower()
    man = f"<span class='scr'>{esc(screen)}</span>" if screen else ""
    sub = group.reason() or triggered
    return (
        f"<details class='ev' id='{anchor(group)}' data-st='{b}' "
        f"data-q='{esc(hay)}'{' open' if b == 'fail' else ''}><summary>"
        f"<span class='status {b}'><span class='dot'></span>{BUCKET_LABEL[b]}</span>"
        f"<span class='ev-t'><span class='ev-name'><code>{esc(group.label)}</code>{man}</span>"
        f"<span class='ev-sub'>{esc(sub)}</span></span>"
        f"<span class='ev-frac'>{esc(group.tally())}</span></summary>"
        f"<div class='ev-body'>"
        + (f"<p class='trig'>{esc(triggered)}</p>" if triggered else "")
        + f"<ul class='lines'>{lines}</ul></div></details>"
    )


def render_list(groups: list[EventGroup], screens: dict[str, str],
                triggered: dict[str, str], triage) -> str:
    out = []
    for key, title, _ in BUCKETS:
        cua = [g for g in groups if g.bucket == key]
        if not cua:
            continue
        body = "".join(_event(g, screens.get(g.base, ""), triggered.get(g.base, ""),
                              triage) for g in cua)
        out.append(f"<section class='bucket' data-st='{key}'><h2 class='bucket-h {key}'>"
                   f"{esc(title)} <span>{len(cua)}</span></h2>{body}</section>")
    return "".join(out)


def render_todo(groups: list[EventGroup]) -> str:
    """Khoi 'can xu ly' dau trang: nguoi doc can biet PHAI LAM GI truoc."""
    cot = []
    cua = [g for g in groups if g.bucket == "fail"]
    if cua:
        items = "".join(
            f"<li><a href='#{anchor(g)}' class='jump'><code>{esc(g.label)}</code></a>"
            f"<span>{esc(g.reason())}</span></li>" for g in cua)
        cot.append(f"<div><h3 class='fail'>{esc(BUCKETS[0][1])}</h3><ul>{items}</ul></div>")
    if not cot:
        return ("<section class='todo-card all-ok'><h3>Không có gì cần xử lý</h3>"
                "<p>Mọi event đã kiểm đều khớp spec.</p></section>")
    return f"<section class='todo-card'>{''.join(cot)}</section>"


def render_unfinished(groups: list[EventGroup]) -> str:
    """Bang do: event chua ra pass/fail. Co bang nay = luot CHUA XONG, khong
    phai report de gui di - lai lai / do lai tren may roi chay lai."""
    cua = [g for g in groups if g.bucket == "unfinished"]
    if not cua:
        return ""
    items = "".join(f"<span class='chip'>{esc(g.label)} — {esc(g.reason())}</span>"
                    for g in cua)
    return ("<div class='callout alarm'><h3>Lượt chưa xong — "
            f"{len(cua)} event chưa ra pass/fail</h3>"
            "<p>Report chỉ được có Khớp hoặc Sai. Các event dưới đây chưa đo được "
            "(lái hụt hoặc chưa kết luận) — phải lái lại tới khi ra kết quả rồi "
            "chạy lại, <b>không publish</b> bản này.</p>"
            f"<div class='chip-list'>{items}</div></div>")
