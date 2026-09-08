"""Doc config/event-check-rules.yaml. Validate CHAT - sai cu phap thi bao loi ro
rang chu khong chay bua.

Ly do phai chat: neu tester go sai ten check thanh 'event_presense' va tool im
lang bo qua, ho se doc mot report thieu check ma tuong la app khong co loi. Kieu
im lang do nguy hiem hon crash.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .resources import config_dir

CONFIG_NAME = "event-check-rules.yaml"

KNOWN_CHECKS = frozenset({"event_presence", "event_params"})
KNOWN_SEVERITY = frozenset({"error", "warning"})


class ConfigError(Exception):
    """Config sai. Message luon noi ro sai o dau va cach sua."""


@dataclass(frozen=True, slots=True)
class CheckSetting:
    enabled: bool
    severity: str = "error"
    options: dict = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CheckConfig:
    checks: dict[str, CheckSetting]

    def enabled(self, name: str) -> bool:
        setting = self.checks.get(name)
        return bool(setting and setting.enabled)

    def option(self, check: str, key: str, default=None):
        setting = self.checks.get(check)
        return setting.options.get(key, default) if setting else default

    def payload(self) -> dict:
        return {
            "enabled_checks": sorted(n for n in self.checks if self.enabled(n)),
            "disabled_checks": sorted(n for n in self.checks if not self.enabled(n)),
            "options": {n: s.options for n, s in self.checks.items()},
        }


def config_path() -> Path | None:
    directory = config_dir()
    if directory is None:
        return None
    candidate = directory / CONFIG_NAME
    return candidate if candidate.is_file() else None


def parse(raw: dict) -> CheckConfig:
    if not isinstance(raw, dict):
        raise ConfigError("File config phai la mot YAML object.")

    checks: dict[str, CheckSetting] = {}
    for name, entry in (raw.get("checks") or {}).items():
        if name not in KNOWN_CHECKS:
            raise ConfigError(
                f"checks.{name} khong phai ten check hop le. Chi nhan: "
                + ", ".join(sorted(KNOWN_CHECKS))
            )
        if not isinstance(entry, dict):
            raise ConfigError(f"checks.{name} phai la object co truong 'enabled'.")
        if "enabled" not in entry:
            raise ConfigError(f"checks.{name} thieu truong 'enabled'.")
        if not isinstance(entry["enabled"], bool):
            raise ConfigError(f"checks.{name}.enabled phai la true/false.")
        severity = str(entry.get("severity", "error"))
        if severity not in KNOWN_SEVERITY:
            raise ConfigError(
                f"checks.{name}.severity phai la 'error' hoac 'warning', "
                f"dang la {severity!r}."
            )
        options = {k: v for k, v in entry.items() if k not in {"enabled", "severity"}}
        checks[name] = CheckSetting(
            enabled=entry["enabled"], severity=severity, options=options)

    # Khong khai gi -> bat het. Tester chua co file config van chay duoc ngay,
    # nhung phai la BAT chu khong phai tat: tat mac dinh thi report rong ma
    # khong ai biet vi sao.
    if not checks:
        checks = {name: CheckSetting(enabled=True) for name in sorted(KNOWN_CHECKS)}
    return CheckConfig(checks=checks)


def load(path: Path | None = None) -> CheckConfig:
    """Doc file config. Khong co file -> dung mac dinh (khong phai loi)."""
    path = path or config_path()
    if path is None:
        return parse({})
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path.name} sai cu phap YAML:\n{exc}") from exc
    except OSError as exc:
        raise ConfigError(f"Khong doc duoc {path}: {exc}") from exc
    return parse(raw)
