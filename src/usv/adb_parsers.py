"""Kieu du lieu + ham parse thuan cua tang adb. Khong I/O -> test khong can device.

Bo loc PACKAGE_RE / SERIAL_RE dat o day (khong o tung route) de MOI route dung
CUNG mot bo loc. Ly do phai loc: ten package/serial di thang vao dong lenh
`adb shell`, ma `adb shell` NOI CAC ARG LAI VA CHAY QUA sh TREN MAY ANDROID.
Khong phai shell injection tren host, nhung "x; rm -rf /sdcard/*" se chay that
tren device. Dropdown khong the la bao dam vi API van nhan input tu do.
"""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

# Duong dan doan khi khong co ADB_PATH va khong co adb trong PATH.
FALLBACK_ADB_PATHS = (
    "~/Android/Sdk/platform-tools/adb",
    "~/Library/Android/sdk/platform-tools/adb",
    "/usr/local/bin/adb",
    "/opt/android-sdk/platform-tools/adb",
)

PACKAGE_RE = re.compile(r"[A-Za-z0-9._]+")
SERIAL_RE = re.compile(r"[A-Za-z0-9.:_-]+")


class AdbError(Exception):
    """Loi khi goi adb. Luon kem huong dan sua duoc."""


class AdbTransportError(AdbError):
    """Mat ket noi toi device/adb server - KHAC voi 'app chua chay'.

    Phan biet 2 loai la bat buoc: neu gop chung, rut cap USB se bi bao nham
    thanh loi app va tester di tim loi o app thay vi cam lai cap.
    """


@dataclass(frozen=True, slots=True)
class Device:
    serial: str
    state: str
    model: str = ""

    @property
    def label(self) -> str:
        return f"{self.model} ({self.serial})" if self.model else self.serial

    @property
    def usable(self) -> bool:
        return self.state == "device"


def find_adb(explicit: str | None = None) -> str:
    """ADB_PATH env -> PATH -> cac duong dan mac dinh cua Android SDK."""
    candidates = [explicit, os.environ.get("ADB_PATH"), shutil.which("adb")]
    candidates += [str(Path(p).expanduser()) for p in FALLBACK_ADB_PATHS]
    for candidate in candidates:
        if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return candidate
    raise AdbError(
        "Khong tim thay adb. Cach sua:\n"
        "  - Cai Android platform-tools, hoac\n"
        "  - Them adb vao PATH, hoac\n"
        "  - Dat bien moi truong ADB_PATH=/duong/dan/toi/adb"
    )


def check_serial(serial: str) -> str:
    """Chan serial la. Xem docstring module ve ly do."""
    if not serial or not SERIAL_RE.fullmatch(serial):
        raise AdbError(f"Serial khong hop le: {serial!r}")
    return serial


def check_package(package: str) -> str:
    """Chan ten package la. Xem docstring module ve ly do."""
    if not package or not PACKAGE_RE.fullmatch(package):
        raise AdbError(f"Ten package khong hop le: {package!r}")
    return package


def parse_devices(output: str) -> list[Device]:
    """Doc output cua 'adb devices -l'."""
    devices: list[Device] = []
    for raw in output.splitlines()[1:]:  # bo dong tieu de "List of devices attached"
        parts = raw.split()
        if len(parts) < 2:
            continue
        model = next((p.split(":", 1)[1] for p in parts[2:] if p.startswith("model:")), "")
        devices.append(Device(serial=parts[0], state=parts[1], model=model))
    return devices


def parse_packages(output: str) -> list[str]:
    """Doc output cua 'adb shell pm list packages -3'."""
    return sorted(
        line.removeprefix("package:").strip()
        for line in output.splitlines()
        if line.startswith("package:")
    )


def parse_wm_size(output: str) -> tuple[int, int] | None:
    """'Physical size: 1080x2280' -> (1080, 2280).

    Uu tien 'Override size' neu co: nguoi dung co the da doi resolution bang
    `wm size`, luc do Physical khong con la cai dang render.
    """
    physical: tuple[int, int] | None = None
    override: tuple[int, int] | None = None
    for line in output.splitlines():
        low = line.lower()
        match = re.search(r"(\d+)\s*x\s*(\d+)", line)
        if not match:
            continue
        value = (int(match.group(1)), int(match.group(2)))
        if "override" in low:
            override = value
        elif "physical" in low:
            physical = value
    return override or physical


def parse_wm_density(output: str) -> int | None:
    """'Physical density: 440' -> 440. Uu tien 'Override density' neu co."""
    physical: int | None = None
    override: int | None = None
    for line in output.splitlines():
        low = line.lower()
        match = re.search(r"(\d+)", line)
        if not match:
            continue
        value = int(match.group(1))
        if "override" in low:
            override = value
        elif "physical" in low:
            physical = value
    return override or physical


def parse_current_focus(output: str) -> str | None:
    """Lay package dang giu focus tu 'dumpsys window'.

    Dung de canh bao khi tester bam Capture nhung notification shade / launcher
    dang che app (da xay ra that trong luc spike: dump ra NotificationShade chu
    khong phai app). Tra None neu khong doc duoc.
    """
    for line in output.splitlines():
        if "mCurrentFocus" not in line:
            continue
        match = re.search(r"([A-Za-z0-9._]+)/[A-Za-z0-9._$]+", line)
        if match:
            return match.group(1)
        # Window khong thuoc app nao, vd 'Window{... NotificationShade}'
        match = re.search(r"\bu\d+\s+(\w+)\}", line)
        if match:
            return match.group(1)
    return None
