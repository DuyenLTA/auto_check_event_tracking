"""Nhung anh chup vao report duoi dang base64.

Nhung thang thay vi de file canh: report duoc gui qua chat, upload lam artifact,
mo tu thu muc Download - moi duong deu lam mat file kem, va mot the <img> gay
la bang chung bien mat ma khong ai biet.

Danh doi: base64 phinh ~33%. Voi PNG 1080x2280 (~200-400 KB) thi 10 case hai anh
van duoi 8 MB. Qua nguong thi bo bot anh, dung bo canh bao.
"""

from __future__ import annotations

import base64
from html import escape as esc

from .flow_screenshots import Shot

GHI_CHU = ("Ảnh là bằng chứng <b>ngữ cảnh</b> — Firebase bắn event bất đồng bộ "
           "nên ảnh có thể chụp sớm hơn lúc event thực sự bắn. Dùng ảnh để biết "
           "màn nào đang hiện, không dùng để kết luận thời điểm.")


def _figure(shot: Shot) -> str:
    data = base64.b64encode(shot.png).decode("ascii")
    return (f'<figure class="shot"><img alt="{esc(shot.moment)}" '
            f'src="data:image/png;base64,{data}">'
            f'<figcaption>{esc(shot.moment)}</figcaption></figure>')


def build_shots(album: dict[str, list[Shot]], bo_bot: int = 0) -> str:
    """HTML cho ca album. Khong co anh nao -> chuoi rong, khong de lai khoi rong."""
    khoi = []
    for case_label, shots in album.items():
        dung_duoc = [s for s in shots if s.png]
        if not dung_duoc:
            continue
        khoi.append(
            f'<section class="shots-case"><h3>{esc(case_label)}</h3>'
            f'<div class="shots-row">{"".join(_figure(s) for s in dung_duoc)}</div>'
            f'</section>')
    if not khoi:
        return ""
    them = (f" Đã bỏ {bo_bot} ảnh vì report sắp vượt trần dung lượng."
            if bo_bot else "")
    return ('<section class="shots"><h2>Ảnh màn hình</h2>'
            f'<p class="shots-note">{GHI_CHU}{them}</p>{"".join(khoi)}</section>')
