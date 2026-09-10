"""Tim thu muc web/ va config/.

web/ nam trong package nen luon co, ke ca khi cai bang `pip install .`.

config/ thi nam o GOC REPO, ngoai src/, nen khong dong goi vao wheel duoc -
cai kieu `pip install .` se khong thay no va tool chay bang gia tri mac dinh
trong code. Hai ben trung nhau tung gia tri, co test giu cho khong lech:
tests/test_config_mac_dinh_khop_file.py.
"""

from __future__ import annotations

from pathlib import Path

_HERE = Path(__file__).resolve().parent


def web_dir() -> Path | None:
    for candidate in (_HERE / "web", _HERE.parents[1] / "web"):
        if candidate.is_dir():
            return candidate
    return None


def config_dir() -> Path | None:
    """config/ o goc repo (src/usv -> parents[1] la goc), None neu khong co.

    None KHONG phai loi: check_config.load() se dung mac dinh. Xem docstring
    dau file.
    """
    candidate = _HERE.parents[1] / "config"
    return candidate if candidate.is_dir() else None
