"""Link artifact cua bao cao - do NGUOI dung/Claude publish roi ghi vao day.

Tool KHONG publish duoc artifact: no chay o 127.0.0.1, khong co duong nao toi
claude.ai. Nhung URL artifact la CO DINH (republish cung file giu nguyen URL),
nen chi can biet URL mot lan la nut tren trang tro thang tuoi do - khong phai
cho ai ca.

Cai bat buoc phai luu kem: `generated_at` cua LUOT da publish. Thieu no thi
nut artifact luon trong nhu moi, va mot bao cao cu bi gui cho team nhu bao cao
cua lan chay vua roi - im lang va sai.
"""

from __future__ import annotations

import json
from pathlib import Path

TEN_FILE = "artifact.json"


def duong_dan(goc: Path | None = None) -> Path:
    return (goc or Path("out")) / TEN_FILE


def doc(goc: Path | None = None) -> dict:
    """{url, generated_at} - rong neu chua publish lan nao.

    File hong/thieu KHONG duoc lam sap trang: nut artifact chi la tien nghi,
    con bao cao local van xem duoc.
    """
    path = duong_dan(goc)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    url = str(data.get("url") or "")
    if not url.startswith("https://"):
        return {}
    return {"url": url, "generated_at": str(data.get("generated_at") or "")}


def ghi(url: str, generated_at: str, goc: Path | None = None) -> dict:
    path = duong_dan(goc)
    path.parent.mkdir(parents=True, exist_ok=True)
    ban = {"url": url, "generated_at": generated_at}
    path.write_text(json.dumps(ban, ensure_ascii=False, indent=2), encoding="utf-8")
    return ban
