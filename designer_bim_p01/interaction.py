# SPDX-License-Identifier: GPL-3.0-or-later
"""Pure mapping between a world-space drag and an occurrence dimension."""
import math


def width_from_drag(start_width_mm: float, start_x_m: float, current_x_m: float, step_mm: float = 10) -> float:
    if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (start_width_mm,start_x_m,current_x_m,step_mm)):
        raise ValueError('Drag inputs must be finite')
    if start_width_mm <= 0 or step_mm <= 0:
        raise ValueError('Width and increment must be positive')
    # The right-hand handle moves, the instance centre stays fixed.
    raw = start_width_mm+2*(current_x_m-start_x_m)*1000
    return round(raw/step_mm)*step_mm
