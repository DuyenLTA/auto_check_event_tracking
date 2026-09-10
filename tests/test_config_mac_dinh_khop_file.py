"""Gia tri mac dinh trong code phai KHOP file config/event-check-rules.yaml.

Vi sao: file config nam o goc repo, ngoai src/, nen `pip install .` (khong -e)
KHONG mang no theo - luc do tool chay bang mac dinh viet trong code. Hai duong
chay ay chi cho cung ket qua khi hai ben trung gia tri.

Do duoc: cai `pip install .` roi goi resources.config_dir() -> None, va
config.checks[...].options -> {} cho ca hai check.

Test nay khong doi hai ben phai giong nhau mai mai. No chi khong cho lech TRONG
IM LANG: doi mot gia tri trong yaml ma quen doi mac dinh thi hai kieu cai cho
hai ket qua khac nhau, va khong ai biet cho den khi doc bao cao thay la.
"""

from __future__ import annotations

import yaml

from usv.check_config import load
from usv.checks import event_params, event_presence
from usv.resources import config_dir

# Mac dinh doc thang tu cho dung no, khong go lai bang tay - go lai thi test
# chi so mot ban chep voi mot ban chep khac.
MAC_DINH = {
    "event_presence": {"duplicate": True},
    "event_params": {"param_extra": True, "global_param_heuristic": False},
}


def _file_config() -> dict:
    thu_muc = config_dir()
    assert thu_muc is not None, "chay tu source thi phai thay config/"
    raw = yaml.safe_load((thu_muc / "event-check-rules.yaml").read_text(
        encoding="utf-8")) or {}
    return raw.get("checks") or {}


def test_moi_khoa_trong_file_deu_khop_mac_dinh():
    khai = _file_config()
    lech = []
    for ten, mong_doi in MAC_DINH.items():
        co = khai.get(ten) or {}
        for khoa, gia_tri in mong_doi.items():
            if khoa in co and co[khoa] != gia_tri:
                lech.append(f"{ten}.{khoa}: file={co[khoa]} nhung mac dinh={gia_tri}")
    assert not lech, (
        "File config lech mac dinh trong code:\n  " + "\n  ".join(lech)
        + "\nCai bang `pip install .` khong thay file config nen se chay theo "
          "mac dinh -> hai kieu cai cho hai ket qua khac nhau. Sua mac dinh "
          "trong code cho khop, hoac doi test nay neu co y de lech.")


def test_moi_check_trong_file_deu_duoc_bat():
    """Tat mot check trong file thi ban `pip install .` van bat -> phai biet."""
    khai = _file_config()
    tat = [ten for ten, c in khai.items() if (c or {}).get("enabled") is False]
    assert not tat, (
        f"File config tat check {tat}, nhung mac dinh la BAT HET. Ban cai bang "
        "`pip install .` se van cham cac check do.")


def test_hai_kieu_cai_cho_CUNG_verdict_tren_log_that():
    """Do bang HANH VI, khong bang chuoi.

    Cham cung mot log + cung mot spec hai lan: mot lan voi file config, mot lan
    voi config KHONG khai gi (dung canh ban `pip install .` khong thay file).
    Hai ket qua phai giong nhau tung dong. Day moi la dieu can dung; so sanh
    tung khoa o tren chi la cach chi ra CHO nao lech khi no lech.
    """
    from pathlib import Path

    from usv import event_check_runner
    from usv.check_config import parse
    from usv.event_spec_parse import parse_paste
    from usv.event_window import whole_session
    from usv.fa_event_parse import parse_log

    fixtures = Path(__file__).parent / "fixtures"
    spec = parse_paste((fixtures / "event-spec-rating.tsv").read_text(
        encoding="utf-8"))
    assert spec.errors == (), spec.errors
    events = [e for e in parse_log(
        (fixtures / "fa-events-aip922.log").read_text(encoding="utf-8"))[0]
        if e.from_app]
    windows = whole_session(tuple(e.name for e in spec.events), events)

    def cham(config):
        results, _ = event_check_runner.run(
            spec, windows, config, session_events=tuple(events))
        return [(r.check, r.element, str(r.verdict)) for r in results]

    theo_file = cham(load())
    # parse({}) la DUNG duong ma load() di khi config_path() tra None -
    # tuc la canh ban `pip install .`. Khong tu dung CheckConfig o day:
    # lam vay la test mot vat the do chinh test dung ra.
    theo_mac_dinh = cham(parse({}))
    assert theo_file == theo_mac_dinh, (
        "Cai bang ./start.sh (doc config/) va cai bang `pip install .` (khong "
        "thay config/) dang cho verdict khac nhau.")
