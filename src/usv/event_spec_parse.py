"""Doc bang spec event tracking tester DAN vao o text (TSV, copy tu Excel/Sheet).

KHONG TU GOP DONG - day la quyet dinh quan trong nhat cua module nay.

Spike da do tren chinh bang cua user: mot hang bi gay lam 2 dong thi noi lai
theo SO COT se MAT o rong o diem gay.

    "rating_placement_viewed\\tKhi man rating hien thi\\tplacement_name\\t"  -> 4 cot
    + "String\\tresult, exit_click, app_shortcut, home\\tVi tri"             -> 3 cot
    = 6 cot, PHAI la 7   <- o `Param Description` rong bi "String" chiem cho

Hau qua: parser thay 6 < 7 nen an luon hang sau, ra mot spec SAI ma khong bao gi.
Cung mot ly do voi check_config.py: kieu im lang nguy hiem hon crash.

Nen: hang sai so cot -> vao `errors` kem SO DONG va so cot dem duoc, de tester
tu sua trong o text. Khong doan.

Dan tu Excel vao <textarea> that thi giu mot hang mot dong va giu o rong bang
tab lien tiep - bang bi gay trong tin nhan chat la do chat reflow, khong phai
do clipboard.
"""

from __future__ import annotations

import csv
import io

from .event_spec_models import SpecEvent, SpecParam, SpecSheet

# Ten cot -> khoa chuan hoa. Chap nhan "Event_Name", "Event Name", "event name".
_REQUIRED = {"eventname", "params", "valuetype"}
_ALIASES = {
    "eventname": "event", "event": "event",
    "screenname": "screen", "screen": "screen",
    "triggered": "triggered", "trigger": "triggered",
    "params": "param", "param": "param", "parameter": "param",
    "paramdescription": "param_desc",
    "valuetype": "value_type", "type": "value_type",
    "value": "value", "values": "value",
    "valuedescription": "value_desc",
}


def _norm(name: str) -> str:
    """Bo dau gach, khoang trang, hoa/thuong -> khoa tra cuu."""
    return "".join(ch for ch in name.strip().casefold() if ch.isalnum())


def _rows(text: str) -> list[list[str]]:
    """Tach TSV bang csv.reader.

    Dung csv chu khong `split("\\t")`: Excel boc nguoc kep quanh o chua tab hoac
    xuong dong, va csv.reader hieu dung ca o nhieu dong - do la o hop le, khong
    phai hang bi gay.
    """
    reader = csv.reader(io.StringIO(text), delimiter="\t")
    return [row for row in reader if any(cell.strip() for cell in row)]


def parse_paste(text: str) -> SpecSheet:
    rows = _rows(text or "")
    if not rows:
        return SpecSheet(errors=("O text trong - chua dan bang spec nao vao.",))
    return parse_rows(rows)


def parse_rows(rows: list[list[str]]) -> SpecSheet:
    """Hang da tach san -> SpecSheet.

    Tach khoi parse_paste de duong Confluence dung chung: o ben do ranh gioi o
    lay tu luoi HTML (co rowspan), khong tu dau tab. Chi khac cach TACH O, con
    y nghia cac cot thi phai giong het - hai ban rieng la mot ngay hai duong
    hieu bang khac nhau.
    """
    header = rows[0]
    index: dict[str, int] = {}
    for pos, raw in enumerate(header):
        key = _ALIASES.get(_norm(raw))
        if key and key not in index:
            index[key] = pos

    missing = sorted(_REQUIRED - {k for k in _norm_keys(header)})
    if missing:
        return SpecSheet(
            columns=tuple(header),
            errors=(
                "Dong dau tien phai la dong TIEU DE cot. Thieu cot: "
                + ", ".join(_pretty(m) for m in missing)
                + f". Tim thay: {', '.join(h.strip() or '(rong)' for h in header)}",
            ),
        )

    ncol = len(header)
    errors: list[str] = []
    events: list[SpecEvent] = []
    params: list[SpecParam] = []
    current: SpecEvent | None = None

    def flush() -> None:
        nonlocal current, params
        if current is not None:
            events.append(SpecEvent(
                name=current.name, screen=current.screen,
                triggered=current.triggered, params=tuple(params)))
        current, params = None, []

    for line_no, row in enumerate(rows[1:], start=2):
        if len(row) != ncol:
            errors.append(
                f"Dong {line_no}: {len(row)} cot, can {ncol}. Hang nay co the bi "
                "gay lam nhieu dong khi dan - sua lai thanh MOT hang mot dong "
                "(o rong thi de tab lien tiep, dung xoa tab)."
            )
            continue

        def cell(key: str) -> str:
            pos = index.get(key)
            return row[pos].strip() if pos is not None and pos < len(row) else ""

        name = cell("event")
        if name:
            flush()
            current = SpecEvent(name=name, screen=cell("screen"),
                                triggered=cell("triggered"))
        if current is None:
            errors.append(
                f"Dong {line_no}: co param '{cell('param') or '(rong)'}' nhung "
                "chua co event nao phia tren. Hang param tiep theo cua mot event "
                "thi de trong cot Event_Name, nhung phai nam DUOI hang cua event do."
            )
            continue

        param_name = cell("param")
        if not param_name:
            continue  # event khong co param nao - hop le

        if param_name in {p.name for p in params}:
            errors.append(
                f"Dong {line_no}: param '{param_name}' khai hai lan cho event "
                f"'{current.name}'."
            )
            continue

        allowed = tuple(v.strip() for v in cell("value").split(",") if v.strip())
        params.append(SpecParam(
            name=param_name, value_type=cell("value_type"),
            allowed=allowed, description=cell("param_desc") or cell("value_desc"),
        ))

    flush()
    if not events and not errors:
        errors.append("Khong doc duoc event nao - bang chi co dong tieu de?")
    return SpecSheet(events=tuple(events), errors=tuple(errors),
                     columns=tuple(header))


def _norm_keys(header: list[str]) -> set[str]:
    """Khoa da chuan hoa cua cac cot, de bao thieu cot nao."""
    out = set()
    for raw in header:
        key = _norm(raw)
        if key in _ALIASES:
            # Bao theo ten CHUAN de thong bao on dinh, khong theo bien the tester go.
            out.add({"event": "eventname", "param": "params",
                     "value_type": "valuetype"}.get(_ALIASES[key], _ALIASES[key]))
    return out


def _pretty(key: str) -> str:
    return {"eventname": "Event_Name", "params": "Params",
            "valuetype": "Value Type"}.get(key, key)
