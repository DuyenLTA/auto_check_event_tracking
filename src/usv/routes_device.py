"""Route tang device: liet ke may va app da cai.

Chi de UI cho tester CHON may/app. Tool khong tu do app nao dang mo - tester
chon, roi tool tu force-stop + mo lai app do khi bat dau Ghi (property
log.tag.FA-SVC doc luc process start nen phai mo lai moi an).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from .adb_client import AdbClient
from .adb_parsers import AdbError

log = logging.getLogger(__name__)
router = APIRouter()


def client() -> AdbClient:
    """Tao AdbClient, doi loi 'khong tim thay adb' thanh 500 co message doc duoc."""
    try:
        return AdbClient()
    except AdbError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/devices")
async def list_devices() -> dict:
    adb = client()
    try:
        devices = await adb.devices()
    except AdbError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {
        "adb": adb.adb,
        "devices": [
            {"serial": d.serial, "state": d.state, "model": d.model,
             "label": d.label, "usable": d.usable}
            for d in devices
        ],
    }


@router.get("/packages")
async def list_packages(serial: str) -> dict:
    adb = client()
    try:
        packages = await adb.packages(serial)
    except AdbError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"serial": serial, "packages": packages}
