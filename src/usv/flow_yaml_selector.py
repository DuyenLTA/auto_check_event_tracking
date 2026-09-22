"""Doc o YAML thanh selector: chon node nao tren man, va bang chuoi gi.

Tach khoi flow_yaml de moi file duoi 200 dong. Day la phan DUY NHAT biet mot o
YAML co the mang nhieu bien the ngon ngu - de rieng thi doc code la thay ngay
ranh gioi do, khong lan vao phan doc buoc.
"""

from __future__ import annotations

from .device_actions import Selector

# Chi tap/swipe moi lam viec tren mot node. `wait_text` va `type` cung co
# truong `text` nhung do la chu de TIM / de GO, doc no thanh selector thi
# `wait_text` bi danh dau fragile oan va Step.label() in ra sai viec.
SELECTOR_FIELDS = ("resource_id", "text", "desc", "cls")


def bien_the(gia_tri: object) -> tuple[str, ...]:
    """Doc mot o YAML thanh cac BIEN THE cua cung mot chuoi can tim.

    `text: Xong`            -> ("Xong",)
    `text: [Done, Xong]`    -> ("Done", "Xong")

    Cho phep khai nhieu thu tieng vi chuoi tren man HE THONG (picker anh,
    sheet thanh toan, dialog quyen) doi theo locale cua may chu khong theo
    ngon ngu chon trong app. Khoa cung mot thu tieng thi cam may khac locale
    la ca case chet - da gap that voi picker anh tren may vi-VN.
    """
    if isinstance(gia_tri, (list, tuple)):
        return tuple(x for x in (str(v).strip() for v in gia_tri) if x)
    chu = str(gia_tri or "").strip()
    return (chu,) if chu else ()


def doc_selector(raw: dict, where: str) -> tuple[Selector | None, list[str]]:
    """Dung MOT trong resource_id|text|desc. Hai truong -> khong biet uu tien
    cai nao, va chon ngam thi tester tuong minh da khoa theo cai kia."""
    used = [f for f in SELECTOR_FIELDS if bien_the(raw.get(f))]
    if not used:
        return None, []
    if len(used) > 1:
        return None, [f"{where}: selector khai {len(used)} truong "
                      f"({', '.join(used)}) — chỉ được dùng đúng một."]
    field = used[0]
    try:
        index = int(raw.get("index") or 0)
    except (TypeError, ValueError):
        return None, [f"{where}: `index` phải là số, đang là {raw.get('index')!r}."]
    chinh, *phu = bien_the(raw[field])
    return Selector(**{field: chinh}, alt=tuple(phu), index=index), []
