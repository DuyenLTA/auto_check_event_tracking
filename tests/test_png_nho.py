"""Thu nho anh ma khong dung thu vien ngoai.

Do that tren Pixel 7: `screencap -p` ra PNG 3.0 MB/tam. Giu nguyen co la 2 tam
da cham tran artifact 16 MB.
"""

from __future__ import annotations

import struct
import zlib

import pytest

from usv.png_nho import RawError, tu_raw


def _raw(rong: int, cao: int, header: int = 16, mau=(10, 20, 30, 255)) -> bytes:
    dau = struct.pack("<III", rong, cao, 1) + (b"\x00" * (header - 12))
    return dau + bytes(mau) * (rong * cao)


def _doc_ihdr(png: bytes) -> tuple[int, int, int, int]:
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert png[12:16] == b"IHDR"
    rong, cao, sau, loai = struct.unpack(">IIBB", png[16:26])
    return rong, cao, sau, loai


def test_ra_dung_PNG_truecolor_8bit():
    rong, cao, sau, loai = _doc_ihdr(tu_raw(_raw(8, 4), rong_toi_da=8))
    assert (rong, cao) == (8, 4)
    assert (sau, loai) == (8, 2)      # 8-bit, RGB


def test_thu_nho_theo_buoc_nhay():
    png = tu_raw(_raw(1080, 240), rong_toi_da=360)
    rong, cao, _, _ = _doc_ihdr(png)
    assert (rong, cao) == (360, 80)   # buoc 3 ca hai chieu, giu ti le


def test_nho_hon_han_anh_goc():
    raw = _raw(1080, 2400)
    png = tu_raw(raw)
    assert len(png) < len(raw) / 50, (len(png), len(raw))


def test_du_lieu_diem_dung_mau_va_bo_alpha():
    png = tu_raw(_raw(2, 2, mau=(1, 2, 3, 255)), rong_toi_da=2)
    i = png.index(b"IDAT")
    dai = struct.unpack(">I", png[i - 4:i])[0]
    than = zlib.decompress(png[i + 4:i + 4 + dai])
    # Hang dau: filter 0 (khong co hang tren de tru) roi 2 diem RGB.
    # Hang hai giong het hang dau -> filter 2 (Up) cho ra toan 0, zlib nen sau.
    assert than == (b"\x00" + b"\x01\x02\x03" * 2
                    + b"\x02" + b"\x00" * 6)


def test_header_12_byte_van_doc_duoc():
    """Ban Android cu khong co truong colorspace."""
    rong, cao, _, _ = _doc_ihdr(tu_raw(_raw(4, 2, header=12), rong_toi_da=4))
    assert (rong, cao) == (4, 2)


@pytest.mark.parametrize("raw", [b"", b"x" * 20, _raw(4, 4)[:-8]])
def test_raw_hong_thi_RawError_de_nguoi_goi_quay_ve_duong_cu(raw):
    with pytest.raises(RawError):
        tu_raw(raw)
