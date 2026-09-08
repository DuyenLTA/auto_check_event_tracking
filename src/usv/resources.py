"""Tim thu muc web/ va config/ ke ca khi cai bang `pip install .` (khong -e).

Uu tien file trong package (duoc dong goi qua package-data), sau do moi tim
thu muc repo - de chay tu source cung duoc.
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
    """config/ nam o goc repo (src/usv -> parents[1] la goc).

    Khi cai bang `pip install .` (khong -e) thi khong co thu muc repo -> lay ban
    dong goi trong package tai usv/data/.
    """
    for candidate in (_HERE.parents[1] / "config", _HERE / "data"):
        if candidate.is_dir():
            return candidate
    return None
