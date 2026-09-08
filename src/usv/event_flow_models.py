"""Tu vung flow: mot case lai app toi mot trang thai roi cho MOT event ban ra.

MOT CASE MOT EVENT (user chot). Nen mot case = mot cua so marker = mot event
mong doi, va `event_window.cut` cat san theo moc nen khong phai lam gi them.

Vi sao `expect_params` nam trong case chu khong lay tu spec: spec khai
`placement_name` duoc phep la result/exit_click/app_shortcut/home - bon gia tri.
Case thi lai app toi DUNG MOT trong bon cho do, nen no biet gia tri nao PHAI ra.
Spec noi "duoc phep", case noi "lan nay phai la cai nay".
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .device_actions import Selector


@dataclass(frozen=True, slots=True)
class Step:
    """Mot thao tac. `kind` quyet dinh truong nao co nghia."""

    kind: str                       # launch|tap|swipe|type|key|wait|wait_text
    selector: Selector | None = None
    text: str = ""                  # type: chu can go; swipe: huong
    seconds: float = 0.0            # wait
    timeout: float = 10.0           # wait_text

    def label(self) -> str:
        if self.selector is not None:
            return f"{self.kind} {self.selector.label()}"
        if self.kind == "wait":
            return f"wait {self.seconds:g}s"
        return f"{self.kind} {self.text!r}" if self.text else self.kind


@dataclass(frozen=True, slots=True)
class Reset:
    """Dua app ve trang thai can thiet TRUOC khi chay step.

    `remote_config` sua gia tri RC (kem moc throttle va prefs mirror).
    `clear_prefs` xoa han vai file prefs - dung cho cai chan popup nam o state
    local, vd apero_rate_prefs.xml giu star_vote_on_store.

    KHONG co `pm clear`: no xoa sach login va data, roi moi case phai dang nhap
    lai. Xem remote_config.
    """

    remote_config: dict[str, str] = field(default_factory=dict)
    clear_prefs: tuple[str, ...] = ()
    relaunch: bool = True           # force-stop + mo lai de app doc gia tri moi

    @property
    def empty(self) -> bool:
        return not self.remote_config and not self.clear_prefs


@dataclass(frozen=True, slots=True)
class FlowCase:
    """Mot case: reset -> lai app -> cho mot event."""

    event: str
    name: str = ""
    expect_params: dict[str, str] = field(default_factory=dict)
    steps: tuple[Step, ...] = ()
    reset: Reset = field(default_factory=Reset)

    @property
    def label(self) -> str:
        return self.name or (
            f"{self.event} ({', '.join(f'{k}={v}' for k, v in self.expect_params.items())})"
            if self.expect_params else self.event)

    @property
    def fragile_steps(self) -> tuple[str, ...]:
        """Step khop theo chu - vo khi doi ngon ngu. De canh bao, khong chan."""
        return tuple(s.label() for s in self.steps
                     if s.selector is not None and s.selector.fragile)

    def payload(self) -> dict:
        return {"event": self.event, "name": self.label,
                "expect_params": self.expect_params,
                "steps": [s.label() for s in self.steps],
                "reset": {"remote_config": self.reset.remote_config,
                          "clear_prefs": list(self.reset.clear_prefs),
                          "relaunch": self.reset.relaunch},
                "fragile": list(self.fragile_steps)}


@dataclass(frozen=True, slots=True)
class Flow:
    package: str = ""
    cases: tuple[FlowCase, ...] = ()
    errors: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return bool(self.cases) and not self.errors

    def payload(self) -> dict:
        return {"ok": self.ok, "package": self.package,
                "case_count": len(self.cases),
                "cases": [c.payload() for c in self.cases],
                "errors": list(self.errors)}
