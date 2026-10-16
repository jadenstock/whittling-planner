"""Grain check: find thin parts that would be short-grained and likely to snap.

Wood splits easily along its grain. A thin part is strong when its fibres are
long: they run from its tip back into the thick body of the figure, or along
the part itself, like a dowel. It is weak when the fibres run across it, so
they start and end within its thickness (short grain).
"""

import numpy as np
from scipy.ndimage import distance_transform_edt, label

THIN_MM = 6.0  # parts thinner than this count as thin
LONG_RUN_MM = 15.0  # fibres at least this long make a thin part strong
PROTRUDE_MM = 3.0  # ignore thin slivers that stick out less than this (e.g. edges of the base)

AXIS_WORDS = {
    "x": "along the length (front to back)",
    "y": "side to side",
    "z": "up and down",
}


def _run_ids(inside: np.ndarray, axis: int) -> np.ndarray:
    """Give each straight run of solid cells along `axis` its own id."""
    a = np.moveaxis(inside, axis, -1)
    starts = a.copy()
    starts[..., 1:] &= ~a[..., :-1]
    ids = np.cumsum(starts.ravel()).reshape(a.shape)
    return np.moveaxis(ids, -1, axis)


def thin_parts(inside: np.ndarray, h: float) -> tuple[np.ndarray, np.ndarray]:
    """Cells in parts thinner than THIN_MM, and each cell's distance (mm) from
    the thick body (a morphological opening, done with distance transforms)."""
    r = THIN_MM / 2
    depth = distance_transform_edt(inside, sampling=h)
    core = depth > r
    if not core.any():
        return inside.copy(), np.full(inside.shape, np.inf)
    reach = distance_transform_edt(~core, sampling=h)
    return inside & (reach > r), reach - r


def fragile(inside: np.ndarray, h: float, axis: int) -> np.ndarray:
    """Cells in thin parts whose fibres (along `axis`) are short and never reach the thick body."""
    thin, reach = thin_parts(inside, h)
    ids = _run_ids(inside, axis)
    anchored = np.bincount(ids[inside & ~thin], minlength=ids.max() + 1) > 0
    long_run = np.bincount(ids[inside], minlength=ids.max() + 1) * h >= LONG_RUN_MM
    weak = thin & ~(anchored | long_run)[ids]
    # keep only weak parts that actually stick out
    labels, n = label(weak)
    if n == 0:
        return weak
    sticks_out = np.zeros(n + 1, bool)
    np.maximum.at(sticks_out, labels[weak], reach[weak] > PROTRUDE_MM)
    return sticks_out[labels] & weak


def analyse(inside: np.ndarray, h: float, blank: np.ndarray) -> dict:
    """Fragile volume for each grain direction, and the recommended one."""
    masks = {a: fragile(inside, h, i) for i, a in enumerate("xyz")}
    volumes = {a: float(m.sum() * h**3) for a, m in masks.items()}
    parts = {a: int(label(m)[1]) for a, m in masks.items()}
    best = min(volumes.values())
    # among directions within 10% (or 5 mm³) of the best, prefer the blank's longest side:
    # long-grain blanks are what you'll find for sale
    near = [a for a in "xyz" if volumes[a] <= best * 1.1 + 5.0]
    recommended = max(near, key=lambda a: blank["xyz".index(a)])
    return {"masks": masks, "volumes": volumes, "parts": parts, "recommended": recommended}
