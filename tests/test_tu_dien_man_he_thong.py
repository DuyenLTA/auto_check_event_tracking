"""Tu dien chu man he thong: flow viet tieng nao cung chay duoc.

Chu tren picker anh / dialog quyen / sheet Play theo locale cua MAY, khong
theo ngon ngu chon trong app. Khoa cung mot thu tieng thi doi may la ca case
chet - da mat hai luot chay vi chuyen do.
"""

from __future__ import annotations

from usv.device_actions import Selector
from usv.tu_dien_man_he_thong import no_bien_the


def test_chu_trong_tu_dien_tim_luon_cac_thu_tieng_khac():
    assert "done" in no_bien_the("Xong")
    assert "xong" in no_bien_the("Done")
    assert "subscribe" in no_bien_the("Đăng ký")


def test_giu_nguyen_hau_to_sao_cho_moi_bien_the():
    """`*` = khop theo dau chuoi. Bien the dich ra cung phai giu no, khong thi
    desc "Ảnh được chụp lúc 11:15" khong con khop."""
    ra = no_bien_the("Photo taken on*")
    assert ra[0] == "Photo taken on*"
    assert all(x.endswith("*") for x in ra)
    assert "ảnh được chụp lúc*" in ra


def test_chu_ngoai_tu_dien_giu_nguyen_khong_doan_bua():
    """Go sai chinh ta van phai hong ra mat, khong am tham bat nham node."""
    assert no_bien_the("Retro 80s") == ("Retro 80s",)
    assert no_bien_the("") == ()


def test_selector_theo_chu_duoc_no_con_resource_id_thi_khong():
    """resource_id la ten trong code, khong phai chu hien cho nguoi doc - dich
    no la sai nghia."""
    assert "done" in Selector(text="Xong").needles
    assert Selector(resource_id="btnDone").needles == ("btnDone",)


def test_bien_the_khai_tay_van_duoc_giu_va_khong_trung():
    sel = Selector(text="Done", alt=("Xong",))
    assert sel.needles.count("Xong") + sel.needles.count("xong") <= 2
    assert "Done" == sel.needles[0]
