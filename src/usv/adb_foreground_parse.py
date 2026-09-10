"""Doc "app nao dang o truoc" tu output cua dumpsys / cmd package.

Tach khoi adb_parsers vi ba ham nay tra loi cung mot cau hoi, va deu la doan
NHIN VAO MAN HINH - khac han cac parser kia (danh sach may, danh sach app) la
su that dut khoat. Chung dung chung mot bay: mot mau don le khong dai dien cho
ca phien.
"""

from __future__ import annotations

import re


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


def parse_resumed_package(output: str) -> str | None:
    """Package cua Activity dang o foreground, tu 'dumpsys activity activities'.

    Dung de CHI RA TEN DUNG khi tester dan sai package: sai mot dau cham la ca
    phien ghi khong ket luan duoc gi, ma tu do lai mot chuoi 30 ky tu bang mat
    thi rat de bo qua. Da gap that: dan 'com.ai.aiimage.aivideo.generator'
    trong khi may co 'com.ai.aiimage.aivideogenerator'.

    Dong that:
        mResumedActivity: ActivityRecord{8a8d4a9 u0 com.foo.bar/.MainActivity t212}
    """
    for line in output.splitlines():
        if "ResumedActivity" not in line:
            continue
        match = re.search(r"\bu\d+\s+([A-Za-z0-9._]+)/", line)
        if match:
            return match.group(1)
    return None


def parse_home_package(output: str) -> str | None:
    """Package cua launcher, tu 'cmd package resolve-activity --brief -a
    android.intent.action.MAIN -c android.intent.category.HOME'.

    Can de LOAI launcher ra khi doan app duoi test tu foreground. Do that: lay
    mau foreground dung mot lan luc Dung ghi thi bat duoc
    com.google.android.apps.nexuslauncher, va bao cao ghi "da cham cho
    launcher" - vo nghia.

    Lay bang resolve-activity chu khong doan theo ten chua chu 'launcher': moi
    may mot launcher khac nhau, va doan thi sai tren may co launcher ben thu ba.

    Dong cuoi cua output la 'package/.Activity'.
    """
    for line in reversed(output.strip().splitlines()):
        line = line.strip()
        if "/" in line and " " not in line:
            return line.split("/")[0] or None
    return None
