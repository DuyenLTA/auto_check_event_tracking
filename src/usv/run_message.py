"""Quyet dinh tin Discord cho mot luot usv-check: stop hay done, noi gi.

Ham thuan tuy (khong IO) de test duoc quyet dinh ma khong can may that.
"""

from __future__ import annotations

MAX_FAIL_LINES = 10


def _phut_giay(seconds: float) -> str:
    total = int(round(seconds))
    return f"{total // 60} phút {total % 60} giây" if total >= 60 else f"{total} giây"


def _fail_rows(payload: dict) -> list[str]:
    rows = []
    for row in payload.get("results", []):
        if str(row.get("verdict", "")).startswith("FAIL"):
            ly_do = str(row.get("message") or row.get("verdict"))
            rows.append(f"• {row.get('element', '?')}: {ly_do}")
    return rows


def build_run_message(payload: dict, duration_s: float | None = None
                      ) -> tuple[str, str, list[str], str | None]:
    """payload = dong JSON stdout cua usv-check -> (kind, title, lines, action)."""
    fail = int(payload.get("fail", 0))
    passed = int(payload.get("pass", 0))
    not_tested = int(payload.get("not_tested", 0))
    chua_ket_luan = int(payload.get("not_verifiable", 0)) + int(payload.get("blocked", 0))
    cho = not_tested + chua_ket_luan
    lines = [f"{payload.get('package', '?')} {payload.get('app_version', '')}".strip(),
             f"{passed} khớp / {fail} sai / {not_tested} chưa test"
             + (f" / {chua_ket_luan} chưa kết luận" if chua_ket_luan else "")]
    if duration_s is not None:
        lines.append(f"Thời gian tool: {_phut_giay(duration_s)}")
    lines.append(f"Report: {payload.get('report', '')}")

    if cho > 0 and payload.get("khong_claude"):
        # Khong co agent sua flow: noi "agent dang sua" la hua mot viec khong
        # ai lam. Report van gui di, so dong can nguoi ghi ro.
        lines += _fail_rows(payload)[:MAX_FAIL_LINES]
        return ("stop", f"Xong, {cho} dòng cần người xem"
                + (f" · {fail} dòng Sai" if fail else ""), lines,
                "Mở report đính kèm: lái tay các dòng 'Cần người xem', "
                "xác nhận dòng Sai trước khi báo dev")
    if cho > 0:
        return ("stop", "Lượt chưa xong", lines,
                "Agent đang sửa flow và chạy lại case hụt")
    if fail > 0:
        rows = _fail_rows(payload)
        shown = rows[:MAX_FAIL_LINES]
        if len(rows) > len(shown):
            shown.append(f"… còn {len(rows) - len(shown)} dòng nữa")
        return ("stop", f"Có {fail} dòng Sai cần tester xác nhận", lines + shown,
                "Xác nhận từng dòng trước khi báo dev / log Jira")
    return "done", "Lượt chấm xong, tất cả khớp", lines, None
