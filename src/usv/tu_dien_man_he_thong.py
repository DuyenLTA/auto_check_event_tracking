"""Tu dien chu tren MAN HE THONG: viet flow bang tieng nao cung chay.

Picker anh, dialog quyen, sheet thanh toan Google Play - chu tren do theo
locale cua may (hoac cua tai khoan Play), khong theo ngon ngu chon trong app.
Khoa cung mot thu tieng thi doi may la ca case chet, va thong bao chi noi
"khong thay chu X" nen rat de tuong app hong.

Cach lam: `text: Xong` tu dong tim ca "Done", va nguoc lai. Chi no cho nhung
chuoi CO TRONG tu dien duoi day - go sai chinh ta thi van hong ra mat, khong
am tham bat nham node khac.

Them tieng moi: them vao dung nhom, khong tao nhom moi cho cung mot nut.
"""

from __future__ import annotations

# Moi nhom = mot nut/nhan tren man he thong, liet ke cac thu tieng da gap.
# Viet thuong het: so khop khong phan biet hoa thuong.
NHOM: tuple[tuple[str, ...], ...] = (
    ("done", "xong", "hoàn tất"),
    ("cancel", "huỷ", "hủy"),
    ("search", "tìm kiếm"),
    ("allow", "cho phép"),
    ("don't allow", "không cho phép", "đừng cho phép"),
    ("subscribe", "đăng ký"),
    ("continue", "tiếp tục"),
    ("next", "tiếp theo"),
    ("close", "đóng"),
    ("open", "mở"),
    ("got it", "đã hiểu"),
    ("skip", "bỏ qua"),
    ("install", "cài đặt"),
    # Desc o anh trong photo picker, mang ca ngay chup phia sau nen flow khoa
    # bang tien to `*`.
    ("photo taken on", "ảnh được chụp lúc"),
)

_TRA = {chu: nhom for nhom in NHOM for chu in nhom}


def no_bien_the(needle: str) -> tuple[str, ...]:
    """Chuoi can tim -> chinh no + cac thu tieng khac cua cung nut do.

    Giu nguyen hau to `*` (khop theo dau chuoi) cho moi bien the:

        "Xong"              -> ("Xong", "done", "hoàn tất")
        "Photo taken on*"   -> ("Photo taken on*", "ảnh được chụp lúc*")
        "Retro 80s"         -> ("Retro 80s",)        # khong co trong tu dien
    """
    chu = (needle or "").strip()
    if not chu:
        return ()
    sao = chu.endswith("*")
    goc = chu[:-1].strip() if sao else chu
    nhom = _TRA.get(goc.casefold())
    if not nhom:
        return (chu,)
    them = [f"{x}*" if sao else x for x in nhom if x != goc.casefold()]
    return (chu, *them)
