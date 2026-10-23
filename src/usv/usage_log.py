"""Tu them mot dong vao docs/usage-log.md khi link artifact duoc ghi.

Chi chen dong moi ngay sau dong cuoi cua bang (truoc doan "**Tổng:**"), khong
dong vao phan con lai cua file.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

TEST_TAY_PHUT = 60            # tester uoc tinh: kiem event 1 tinh nang tren 1 app
DEFAULT_PATH = Path("docs") / "usage-log.md"


def build_row(*, package: str, version: str, passed: int, failed: int,
              duration_s: float, url: str, ngay: str | None = None) -> str:
    phut = max(1, round(duration_s / 60))
    tong = passed + failed
    ket_qua = f"{passed}/{tong} khớp" + (f", {failed} sai" if failed else "")
    bug = "chờ tester xác nhận" if failed else "0"
    ngay = ngay or datetime.now().strftime("%d/%m/%Y")
    cells = [ngay, package, version or "—", "1", ket_qua, bug,
             f"[artifact]({url})", f"{phut} phút (đo: {round(duration_s)} giây)",
             f"{TEST_TAY_PHUT} phút", f"{TEST_TAY_PHUT - phut} phút"]
    return "| " + " | ".join(cells) + " |"


def append_row(path: Path, row: str) -> bool:
    """True nếu đã chèn. Không có bảng / dòng đã tồn tại -> False, file giữ nguyên."""
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    if row in lines:
        return False
    tong = next((i for i, ln in enumerate(lines) if ln.startswith("**Tổng:**")),
                len(lines))
    last = next((i for i in range(tong - 1, -1, -1) if lines[i].startswith("|")), None)
    if last is None:
        return False
    lines.insert(last + 1, row)
    path.write_text("\n".join(lines), encoding="utf-8")
    return True
