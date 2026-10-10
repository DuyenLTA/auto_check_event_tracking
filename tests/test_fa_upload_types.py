"""Kieu that cua param doc tu payload upload Firebase trong logcat.

Dinh dang dong log chep tu may that (Pixel 7, AIP922 3.5.0, `-v time`).
"""

from __future__ import annotations

from usv.check_models import Verdict
from usv.checks.event_params import _check_params
from usv.event_spec_parse import parse_paste
from usv.fa_event_parse import parse_log
from usv.fa_upload_types import parse_upload_events

P = "10-02 10:11:20.549 V/FA-SVC  ( 5727): "


def _upload(name: str, params: list[tuple[str, str, str]]) -> str:
    lines = ["    event {", f"      name: {name}", "      timestamp_millis: 1790910412573"]
    for key, kind, value in params:
        lines += ["      param {", f"        name: {key}", f"        {kind}_value: {value}", "      }"]
    lines += ["    }"]
    return "\n".join(P + line for line in lines)


LOGGED = (P + "Logging event: origin=app,name=style_click,params=Bundle[{"
          "style_id=100111, ga_event_origin(_o)=app, position=1}]")

LOG = "\n".join([
    LOGGED,
    P + "Uploading data. app, uncompressed size, data: 1234",
    P + "batch {",
    P + "  bundle {",
    _upload("session_start(_s)", [("ga_session_id(_sid)", "int", "1790910412")]),
    _upload("style_click", [("ga_event_origin(_o)", "string", "app"),
                            ("style_id", "int", "100111"),
                            ("position", "int", "1")]),
    P + "    user_property {",
    P + "      name: first_open_time(_fot)",
    P + "      int_value: 1790668800000",
    P + "    }",
    P + "  }",
    P + "}",
])

SPEC = parse_paste("\t".join(["Event_Name", "Params", "Value Type"]) + "\n"
                   + "style_click\tstyle_id\tString\n"
                   + "\tposition\tInt\n")


def test_doc_ten_va_kieu_tung_param_theo_do_sau_ngoac():
    ups = parse_upload_events(LOG)
    assert [name for name, _ in ups] == ["session_start", "style_click"]
    assert ups[1][1]["style_id"] == ("int", "100111")
    # user_property nam ngoai `event {` -> khong lan vao event nao.
    assert "first_open_time" not in ups[1][1]


def test_event_log_duoc_gan_kieu_tu_khoi_upload_cung_gia_tri():
    events, _ = parse_log(LOG)
    click = [e for e in events if e.name == "style_click"][0]
    assert click.param_types["style_id"] == "int"


def test_spec_string_ma_upload_ghi_int_la_fail_type():
    events, _ = parse_log(LOG)
    click = [e for e in events if e.name == "style_click"][0]
    out = _check_params(SPEC.events[0], click.params, False, frozenset(), {},
                        click.param_types)
    verdicts = {r.element: r.verdict for r in out}
    assert verdicts["style_click.style_id"] == Verdict.FAIL_TYPE
    assert verdicts["style_click.position"] == Verdict.PASS


def test_khong_co_khoi_upload_thi_van_not_verifiable():
    """Batch chua kip gui trong phien ghi: khong doan kieu."""
    events, _ = parse_log(LOGGED)
    click = events[0]
    assert click.param_types == {}
    out = _check_params(SPEC.events[0], click.params, False, frozenset(), {},
                        click.param_types)
    assert {r.element: r.verdict for r in out}["style_click.style_id"] == Verdict.NOT_VERIFIABLE
