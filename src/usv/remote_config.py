"""Doi gia tri Firebase Remote Config cua app tren may, khong can quyen admin.

Dung de reset trang thai giua cac case trong flow: mot popup rating chi hien 1
lan / N session, nen lai app toi cung mot cho 4 lan KHONG lam no hien 4 lan.

KHONG dung `pm clear`: no xoa sach login va data, roi moi case phai dang nhap
lai. Cach o day la sua DUNG nhung file can sua.

Ba viec, thu tu quan trong:
  1. do tim frc_<appId>_* - appId khac nhau tung app nen phai DO TIM
  2. sua gia tri + moc throttle (ca hai, xem remote_config_patch)
  3. sua ca prefs MIRROR cua SDK Apero

Bay mirror: SDK Apero copy RC sang prefs rieng voi TEN KEY Y HET, va ten FILE
khac nhau tung app - do duoc: `tutorial_remote_first_open.xml` (34 key) tren
aimusic.aisonggenerator, con ban ghi chu cu la `vsl_template4_remote_first_open.xml`.
Nen phai DO TIM file mirror chu khong hardcode ten. Chi sua frc_*.json thi gan
nua key khong an ma khong bao loi gi.

Doi hoi app la build DEBUGGABLE - xem adb_appdata.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .remote_config_patch import (
    patch_activate_json, patch_prefs_xml, patch_throttle_xml, read_configs,
)

log = logging.getLogger(__name__)

FILES = "files"
PREFS = "shared_prefs"
_ACTIVATE_SUFFIX = "_firebase_activate.json"
_SETTINGS_SUFFIX = "_firebase_settings.xml"


@dataclass(frozen=True, slots=True)
class FrcPaths:
    activate: str = ""
    settings: str = ""

    @property
    def ok(self) -> bool:
        return bool(self.activate)


@dataclass(slots=True)
class OverrideResult:
    """Ket qua mot lan override. `blocked` -> khong ket luan gi ve app."""

    applied: dict[str, str] = field(default_factory=dict)
    mirrors: dict[str, list[str]] = field(default_factory=dict)
    blocked: str = ""
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.blocked

    def payload(self) -> dict:
        return {"applied": self.applied, "mirrors": self.mirrors,
                "blocked": self.blocked, "notes": self.notes}


async def find_paths(client, serial: str, package: str) -> FrcPaths:
    """Do tim ten file frc_* - appId nhung trong ten file, khac nhau tung app."""
    activate = settings = ""
    for name in await client.app_list(serial, package, FILES):
        if name.endswith(_ACTIVATE_SUFFIX):
            activate = f"{FILES}/{name}"
            break
    for name in await client.app_list(serial, package, PREFS):
        if name.endswith(_SETTINGS_SUFFIX):
            settings = f"{PREFS}/{name}"
            break
    return FrcPaths(activate=activate, settings=settings)


async def device_now_ms(client, serial: str) -> int:
    """Gio cua MAY, khong phai cua host: SDK so moc voi System.currentTimeMillis()."""
    return await client.device_time_ms(serial)


async def override(client, serial: str, package: str,
                   values: dict[str, str]) -> OverrideResult:
    """Dat gia tri RC roi chan fetch bang cach day moc throttle len bay gio."""
    result = OverrideResult()
    if not values:
        return result

    if not await client.is_debuggable(serial, package):
        result.blocked = (
            f"App {package} khong phai build debuggable nen khong sua duoc "
            "Remote Config tu ngoai. Dung build debug/internal, hoac bo buoc "
            "`reset` va tu dua app ve trang thai can test.")
        return result

    paths = await find_paths(client, serial, package)
    if not paths.ok:
        result.blocked = (
            "Khong thay file frc_*_firebase_activate.json trong app. Thuong la "
            "app chua fetch Remote Config lan nao - mo app mot lan roi thu lai.")
        return result

    now_ms = await device_now_ms(client, serial)
    current = await client.app_read(serial, package, paths.activate)
    try:
        await client.app_write(serial, package, paths.activate,
                               patch_activate_json(current, values, now_ms))
    except ValueError as exc:
        result.blocked = str(exc)
        return result

    if paths.settings:
        text = await client.app_read(serial, package, paths.settings)
        await client.app_write(serial, package, paths.settings,
                               patch_throttle_xml(text, now_ms))
    else:
        # Khong co file throttle -> khong chan duoc fetch. Patch van ghi duoc
        # nhung lan mo app sau app se fetch that va de mat. Noi ra.
        result.notes.append(
            "Khong thay file frc_*_firebase_settings.xml nen khong chan duoc "
            "fetch - gia tri vua dat co the bi ghi de khi mo lai app.")

    result.applied = {k: str(v) for k, v in values.items()}
    result.mirrors = await _patch_mirrors(client, serial, package, values)
    return result


async def _patch_mirrors(client, serial: str, package: str,
                         values: dict[str, str]) -> dict[str, list[str]]:
    """Sua cac prefs MIRROR co chua dung nhung key nay.

    Do tim thay vi hardcode ten file: moi app mirror mot tap key khac va ten file
    khac. Bo qua chinh file frc_* (da sua o tren).
    """
    touched: dict[str, list[str]] = {}
    for name in await client.app_list(serial, package, PREFS):
        if not name.endswith(".xml") or name.startswith("frc_"):
            continue
        path = f"{PREFS}/{name}"
        text = await client.app_read(serial, package, path)
        if not text:
            continue
        patched, changed = patch_prefs_xml(text, values)
        if changed:
            await client.app_write(serial, package, path, patched)
            touched[name] = sorted(changed)
    return touched


async def clear_prefs(client, serial: str, package: str,
                      files: list[str]) -> OverrideResult:
    """Xoa han vai file prefs - dung cho cai chan popup nam o state local.

    Do that tren app that: popup rating bi chan boi
    `apero_rate_prefs.xml` -> `star_vote_on_store`, KHONG phai boi Remote Config.
    Xoa dung file do la popup du dieu kien hien lai, ma khong mat login nhu
    `pm clear`.
    """
    result = OverrideResult()
    if not files:
        return result
    if not await client.is_debuggable(serial, package):
        result.blocked = (
            f"App {package} khong phai build debuggable nen khong xoa duoc prefs.")
        return result
    for name in files:
        await client.app_remove(serial, package, f"{PREFS}/{name}")
        result.notes.append(f"đã xoá shared_prefs/{name}")
    return result


async def verify(client, serial: str, package: str,
                 values: dict[str, str]) -> dict[str, str]:
    """Doc lai sau khi mo lai app. Lech -> nguoi goi phai danh BLOCKED.

    Build dev dat `minimumFetchInterval = 0` thi throttle vo hieu, app fetch that
    va de mat patch. Luc do KHONG duoc bao app sai - tool chua dat duoc tien de
    de test.
    """
    paths = await find_paths(client, serial, package)
    if not paths.ok:
        return {}
    configs = read_configs(await client.app_read(serial, package, paths.activate))
    return {key: configs.get(key, "") for key in values}
