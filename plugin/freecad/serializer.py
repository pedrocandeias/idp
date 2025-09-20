from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, List, Optional, Tuple


@dataclass
class Control:
    name: str
    type: str = "generic"
    position_xyz: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    required_force_N: Optional[float] = None
    required_torque_Nm: Optional[float] = None
    label_color_rgb: Optional[Tuple[int, int, int]] = None
    label_size_mm: Optional[float] = None


def _boundbox_from_objects(objs: List[Any]) -> Optional[dict]:
    # Try FreeCAD-style BoundBox if available
    for o in objs:
        bb = getattr(getattr(o, "Shape", None), "BoundBox", None) or getattr(
            o, "BoundBox", None
        )
        if bb is not None:
            return {
                "xlen": float(getattr(bb, "XLength", 0.0)),
                "ylen": float(getattr(bb, "YLength", 0.0)),
                "zlen": float(getattr(bb, "ZLength", 0.0)),
            }
    return None


def _controls_from_objects(objs: List[Any]) -> List[Control]:
    controls: List[Control] = []
    for o in objs:
        name = getattr(o, "Label", None) or getattr(o, "Name", None) or ""
        if not name:
            continue
        if not str(name).upper().startswith("CTRL_"):
            continue
        # Placement/Base for position; default zeros if missing
        pos = (0.0, 0.0, 0.0)
        plc = getattr(o, "Placement", None)
        if plc is not None:
            base = getattr(plc, "Base", None)
            if base is not None:
                pos = (
                    float(getattr(base, "x", 0.0)),
                    float(getattr(base, "y", 0.0)),
                    float(getattr(base, "z", 0.0)),
                )
        ctype = "generic"
        if "KNOB" in str(name).upper():
            ctype = "knob"
        elif "BUTTON" in str(name).upper():
            ctype = "button"
        controls.append(Control(name=name, type=ctype, position_xyz=pos))
    return controls


def serialize_document(doc: Any) -> dict:
    """
    Serialize parametric data from a FreeCAD-like document.
    Expects doc to have .Objects list. For tests, pass a dummy object with the same shape.
    Returns a JSON-serializable dict structure used as 'params' alongside STEP.
    """
    objs = list(getattr(doc, "Objects", []) or [])
    bbox = _boundbox_from_objects(objs) or {"xlen": 0.0, "ylen": 0.0, "zlen": 0.0}
    controls = [asdict(c) for c in _controls_from_objects(objs)]
    return {
        "overall_dimensions_mm": bbox,
        "controls": controls,
        "meta": {"count": len(objs)},
    }
