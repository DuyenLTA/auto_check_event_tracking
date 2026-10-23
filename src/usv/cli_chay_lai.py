"""Tu chay lai case lai hut ngay trong mot lenh `usv-check`.

Truoc day viec nay do agent lam: doc JSON, thay case `not_tested` / `blocked`
thi goi lai `--case <nhan> --base <file>`. Khong co agent thi case hut nam
nguyen trong report. Phan lon case hut la man len cham (quang cao load lau,
popup den muon) - chay lai mot lan la qua. Nen tool tu lam buoc do, dung co
che `--case` + `--base` san co: chi chay lai dung case hut, roi gop vao luot
day du nhu tester van lam tay.

Chay lai KHONG sua flow. Case hut vi selector sai thi lan sau van hut - report
ghi nguyen ly do, va do la viec cua nguoi (hoac `/record-flow`).
"""

from __future__ import annotations

import json
from pathlib import Path

# Trang thai case dang chay lai: lai hut, hoac reset khong an. `ok` la da do.
TRANG_THAI_HUT = ("not_tested", "blocked")


def case_hut(payload: dict) -> tuple[str, ...]:
    """Nhan cac case chua do duoc trong payload, giu thu tu, bo trung."""
    nhan = [str(c.get("case", "")) for c in payload.get("cases") or []
            if c.get("status") in TRANG_THAI_HUT and c.get("case")]
    return tuple(dict.fromkeys(nhan))


def ghi_base(payload: dict) -> Path:
    """Ghi payload canh file report de lam `--base` cho lan chay lai.

    `doc_base` doc dong JSON cuoi cua file - dung dinh dang stdout cua usv-check.
    """
    path = Path(payload["report"]).with_suffix(".json")
    path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
