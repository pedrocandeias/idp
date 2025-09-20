from __future__ import annotations

from typing import Any, Dict, Tuple


def contrast_ratio(l1: float, l2: float) -> float:
    # l1,l2: relative luminance (0-1). Ensure l1 >= l2
    a, b = (l1, l2) if l1 >= l2 else (l2, l1)
    return (a + 0.05) / (b + 0.05)


def wcag_contrast_from_rgb(fg: Tuple[int, int, int], bg: Tuple[int, int, int]) -> float:
    def rel_lum(c: Tuple[int, int, int]) -> float:
        def chan(u: int) -> float:
            x = u / 255.0
            return x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4

        r, g, b = c
        return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b)

    return contrast_ratio(rel_lum(fg), rel_lum(bg))


def reach_envelope_ok(distance_cm: float, posture: str = "seated") -> bool:
    # Very simplified: seated reach <= 60cm, standing <= 75cm
    limit = 60.0 if posture == "seated" else 75.0
    return distance_cm <= limit


def strength_feasible(required_force_N: float, capability_N: float) -> bool:
    return capability_N >= required_force_N


def inclusivity_index(
    reach_ok: bool, strength_ok: bool, visual_ok: bool
) -> Dict[str, Any]:
    # Weighted aggregate: reach 0.4, strength 0.3, visual 0.3
    weights = {"reach": 0.4, "strength": 0.3, "visual": 0.3}
    score = (
        (1.0 if reach_ok else 0.0) * weights["reach"]
        + (1.0 if strength_ok else 0.0) * weights["strength"]
        + (1.0 if visual_ok else 0.0) * weights["visual"]
    )
    return {
        "score": score,
        "weights": weights,
        "components": {"reach": reach_ok, "strength": strength_ok, "visual": visual_ok},
    }
