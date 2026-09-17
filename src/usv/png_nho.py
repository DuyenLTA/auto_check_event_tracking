"""Anh chup thu nho, khong them thu vien nao.

Do tren may that (Pixel 7, 1080x2400): mot `screencap -p` ra PNG **3.0 MB**.
Base64 phinh them 1/3 -> 4 MB moi tam. Hai tam la cham tran artifact 16 MB, ma
mot luot cham that co hang chuc case. Anh la bang chung NGU CANH ("man nao dang
hien"), khong ai zoom vao doc chu, nen ha do phan giai la mat mot thu khong
dung toi.

Cach lam: lay `screencap` RAW (khong `-p`) roi lay mau theo buoc nhay, va tu ghi
PNG. KHONG giai ma PNG, nen khong can Pillow:
  - raw = header + RGBA_8888 thuan
  - lay moi buoc nhay mot diem, bo kenh alpha (screencap luon 255)
  - ghi IHDR/IDAT/IEND, zlib nen phan du lieu

Header raw dai 12 byte (w, h, format) tren ban cu va 16 byte tu khi them truong
colorspace - do tren may that ra 16. Suy header bang cach thu ca hai roi xem cai
nao khop `w*h*4`, chu khong doan theo phien ban Android.
"""

from __future__ import annotations

import struct
import zlib

RONG_MAC_DINH = 360          # du nhin ra man nao, ~100 KB mot tam
RGBA = 4


class RawError(Exception):
    """Raw khong doc duoc - nguoi goi quay ve duong `screencap -p`."""


def _kich_thuoc(raw: bytes) -> tuple[int, int, int]:
    """(rong, cao, do dai header). Sai dinh dang -> RawError."""
    if len(raw) < 16:
        raise RawError("raw quá ngắn.")
    rong, cao = struct.unpack("<II", raw[:8])
    for header in (16, 12):
        if rong * cao * RGBA == len(raw) - header:
            return rong, cao, header
    raise RawError(f"raw {len(raw)} byte không khớp {rong}x{cao} RGBA.")


def _chunk(loai: bytes, du_lieu: bytes) -> bytes:
    return (struct.pack(">I", len(du_lieu)) + loai + du_lieu
            + struct.pack(">I", zlib.crc32(loai + du_lieu) & 0xFFFFFFFF))


def _loc(hang: bytes, truoc: bytes) -> bytes:
    """Scanline da loc, kem byte chon filter.

    Filter `Up` (hieu voi hang tren) an dut filter 0 tren anh man hinh: phan
    lon man la nen phang hoac chuyen mau doc, nen hieu hai hang gan nhu toan 0
    va zlib nen rat sau. Chon theo tong tri tuyet doi - dung heuristic chuan
    cua libpng, khong phai doan.
    """
    if not truoc:
        return b"\x00" + hang
    up = bytes((a - b) & 0xFF for a, b in zip(hang, truoc))
    nang_0 = sum(min(b, 256 - b) for b in hang)
    nang_up = sum(min(b, 256 - b) for b in up)
    return (b"\x02" + up) if nang_up < nang_0 else (b"\x00" + hang)


def _png(rong: int, cao: int, hang: list[bytes]) -> bytes:
    ihdr = struct.pack(">IIBBBBB", rong, cao, 8, 2, 0, 0, 0)   # 8-bit, truecolor RGB
    phan, truoc = [], b""
    for h in hang:
        phan.append(_loc(h, truoc))
        truoc = h
    than = b"".join(phan)
    return (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr)
            + _chunk(b"IDAT", zlib.compress(than, 6)) + _chunk(b"IEND", b""))


def tu_raw(raw: bytes, rong_toi_da: int = RONG_MAC_DINH) -> bytes:
    """RGBA raw cua screencap -> PNG da thu nho."""
    rong, cao, header = _kich_thuoc(raw)
    buoc = max(1, -(-rong // max(1, rong_toi_da)))     # lam tron len
    rong_moi = len(range(0, rong, buoc))
    cao_moi = len(range(0, cao, buoc))

    hang: list[bytes] = []
    for y in range(0, cao, buoc):
        dau_hang = header + y * rong * RGBA
        diem = bytearray()
        for x in range(0, rong, buoc):
            i = dau_hang + x * RGBA
            diem += raw[i:i + 3]                        # bo alpha
        hang.append(bytes(diem))
    return _png(rong_moi, cao_moi, hang)
