"""Render ghi chu triage trong report.

Tach khoi report_event_html de moi file duoi 200 dong, va vi day la hai
nguon khac han nhau: phan kia in thu TOOL DO duoc tu log, phan nay in SUY
LUAN cua agent. De rieng thi doc code la thay ngay ranh gioi do.
"""

from __future__ import annotations

from .report_event_callouts import esc


def triage_block(note) -> str:
    """Khoi ghi chu triage duoi mot dong FAIL.

    Trinh bay khac han phan tren de khong ai nham: phan tren la thu tool DO
    duoc tu log, phan nay la SUY LUAN cua agent. Co phieu phan bien thi in ra
    - '2/3 agent dong y' noi duoc muc chac chan ma mot cau khang dinh khong
    noi duoc.
    """
    if note is None:
        return ""
    phieu = (f"<span class='triage-vote'>{esc(note.phieu)}</span>"
             if note.phieu else "")
    bang_chung = (f"<p class='ev'>{esc(note.bang_chung)}</p>"
                  if note.bang_chung else "")
    return (
        "<div class='triage'><div class='triage-head'>"
        f"<span class='triage-tag'>Nhiều khả năng: {esc(note.nhan)}</span>"
        f"{phieu}</div>"
        f"<p>{esc(note.ly_do)}</p>{bang_chung}</div>"
    )


def triage_callout(triage) -> str:
    """Noi ro con bao nhieu loi CHUA duoc triage.

    Cat bot im lang thi bao cao trong nhu da soi het moi loi, va nguoi doc bo
    qua dung cai chua ai nhin toi.
    """
    if triage is None or not triage.bo_sot:
        return ""
    return (
        "<div class='callout'><h3>Còn "
        f"{triage.bo_sot} lỗi chưa được soi</h3>"
        "<p>Phần ghi chú <i>Nhiều khả năng…</i> chỉ có ở một số dòng. Các dòng "
        "còn lại chưa ai xem nguyên nhân — không phải chúng không có vấn đề."
        "</p></div>")
