"""Doi don vi px <-> dp. Pure -> test khong can device.

Vi sao phai co: `uiautomator dump` tra bounds bang PIXEL VAT LY, con moi thu
khac (kich thuoc nut, khoang cach) noi bang dp. May test la 1080x2280 @440dpi
-> scale 2.75 -> man hinh that rong 392.7dp.

Dung o phase 7: tim node theo selector roi bam vao tam bounds cua no.

Cong thuc Android: scale = density / 160 (160dpi = mdpi = 1dp bang 1px).
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import Bounds

BASELINE_DENSITY = 160  # mdpi


@dataclass(frozen=True, slots=True)
class ScreenMetrics:
    """Thong so man hinh cua 1 lan capture. Bat buoc di kem moi ket qua check:
    doi may la moi con so dp doi theo."""

    width_px: int
    height_px: int
    density: int

    @property
    def scale(self) -> float:
        return self.density / BASELINE_DENSITY

    @property
    def width_dp(self) -> float:
        return round(self.width_px / self.scale, 1)

    @property
    def height_dp(self) -> float:
        return round(self.height_px / self.scale, 1)

    def to_dp(self, px: float) -> float:
        return round(px / self.scale, 1)

    def to_px(self, dp: float) -> float:
        return round(dp * self.scale, 1)

    def bounds_to_dp(self, bounds: Bounds) -> Bounds:
        return bounds.scaled(1.0 / self.scale)

    @property
    def label(self) -> str:
        return (
            f"{self.width_px}x{self.height_px} px @{self.density}dpi "
            f"-> {self.width_dp}x{self.height_dp} dp (scale {self.scale:g})"
        )

    def payload(self) -> dict:
        return {
            "width_px": self.width_px,
            "height_px": self.height_px,
            "density": self.density,
            "scale": self.scale,
            "width_dp": self.width_dp,
            "height_dp": self.height_dp,
            "label": self.label,
        }
