"""Placing a design in a block: which way up the block goes, and whether turning
the figure at an angle inside it lets the figure be bigger.

World coordinates, in mm: the block spans [0, blank] on each axis, x runs from
the back (0) to the front, y from the block's right side (0) to its left, and
z is up. The figure faces +x, turned by `yaw` degrees toward +y.
"""

from dataclasses import dataclass
from functools import lru_cache
from itertools import permutations

import numpy as np

from whittling_planner.designs import DESIGNS, shape
from whittling_planner.units import inches

MARGIN_MM = 1.0  # wood left around the figure on the sides and top; the base sits on the bottom face
YAWS = np.arange(-45.0, 45.01, 2.5)
GRAIN_SLACK_DEG = 30.0  # how far the grain may run off one of a design's good axes
WORTH_ANGLING = 1.08  # turn the figure only if that makes it at least this much bigger


@dataclass(frozen=True)
class Fit:
    """A design placed inside a blank."""

    key: str
    blank: np.ndarray  # mm, (x, y, z)
    scale: float  # mm per design unit
    yaw: float  # degrees; positive turns the nose toward the block's left side
    offset: np.ndarray  # world position (mm) of the design origin
    figure: np.ndarray  # the figure's own length, width and height, mm
    grain_axes: str  # world axes along the block's longest side: where its grain runs
    grain_ok: bool  # the block's grain runs along an axis the design is happy with
    straight_scale: float  # the best scale with the figure square to the block

    def target(self, x, y, z):
        """The design's signed distance in mm, at world points."""
        s, (ox, oy, oz) = self.scale, self.offset
        u, v, w = (x - ox) / s, (y - oy) / s, (z - oz) / s
        c, n = np.cos(np.radians(self.yaw)), np.sin(np.radians(self.yaw))
        return s * DESIGNS[self.key].sdf(u * c + v * n, -u * n + v * c, w)

    def to_world(self, q) -> np.ndarray:
        """Design-coordinate points (n, 3) → world mm."""
        q = np.atleast_2d(np.asarray(q, dtype=float))
        return self.offset + self.scale * _turn(q, self.yaw)


def _turn(p: np.ndarray, yaw: float) -> np.ndarray:
    """Rotate points (n, 3) about the vertical axis by `yaw` degrees."""
    c, n = np.cos(np.radians(yaw)), np.sin(np.radians(yaw))
    return np.column_stack([p[:, 0] * c - p[:, 1] * n, p[:, 0] * n + p[:, 1] * c, p[:, 2]])


def _grain_ok(good: str, grain_axes: str, yaw: float) -> bool:
    for axis in grain_axes:
        if axis == "z" and "z" in good:
            return True
        # a horizontal grain axis runs at |yaw| to the figure's own x or y axis
        if axis in "xy" and axis in good and abs(yaw) <= GRAIN_SLACK_DEG:
            return True
    return False


@lru_cache(maxsize=256)
def _candidates(key: str, block_mm: tuple[float, float, float]) -> list[tuple]:
    """(scale, yaw, blank, grain_axes, grain_ok) for every way of setting the
    block down and every turn of the figure."""
    points = shape(key).points
    height = points[:, 2].max()
    good = DESIGNS[key].grain
    longest = max(block_mm)
    turned = {yaw: np.ptp(_turn(points, yaw)[:, :2], axis=0) for yaw in YAWS}
    out = []
    for blank in sorted(set(permutations(block_mm))):
        X, Y, Z = blank
        grain_axes = "".join(a for a, v in zip("xyz", blank) if v >= longest - 0.5)
        for yaw, (ex, ey) in turned.items():
            scale = min((X - 2 * MARGIN_MM) / ex, (Y - 2 * MARGIN_MM) / ey, (Z - MARGIN_MM) / height)
            out.append((float(scale), float(yaw), blank, grain_axes, _grain_ok(good, grain_axes, yaw)))
    return out


def _best(cands: list[tuple]) -> tuple:
    usable = [c for c in cands if c[4]] or cands
    # biggest figure; among near ties, the least turned
    top = max(c[0] for c in usable)
    return min((c for c in usable if c[0] >= top * 0.995), key=lambda c: (abs(c[1]), -c[1]))


def fit_design(key: str, block_mm, angled: bool = True) -> Fit:
    """Place a design in a block (any orientation), as big as it will go."""
    block_mm = tuple(float(v) for v in block_mm)
    if min(block_mm) <= 2 * MARGIN_MM + 1:
        raise ValueError("block is too small")
    cands = _candidates(key, block_mm)
    straight = _best([c for c in cands if c[1] == 0.0])
    best = _best(cands) if angled else straight
    if best[0] < straight[0] * WORTH_ANGLING:
        best = straight
    scale, yaw, blank, grain_axes, grain_ok = best

    s = shape(key)
    turned = _turn(s.points, yaw)
    lo, hi = turned.min(axis=0), turned.max(axis=0)
    blank = np.array(blank)
    size = (hi - lo) * scale
    corner = np.array([(blank[0] - size[0]) / 2, (blank[1] - size[1]) / 2, 0.0])
    offset = corner - lo * scale
    offset[2] = 0.0  # the design's base (z = 0) on the block's bottom face
    return Fit(key, blank, scale, yaw, offset, (s.hi - s.lo) * scale, grain_axes, grain_ok, straight[0])


def describe(fit: Fit) -> str:
    """How to set the block down, in words."""
    X, Y, Z = (inches(v) for v in fit.blank)
    others = sorted(fit.blank[:2])
    if fit.blank[2] > others[1] + 0.5:
        return f"Stand the block on end, on a {X} × {Y} in face, so it's {Z} in tall."
    if fit.blank[2] < others[0] - 0.5 and abs(fit.blank[0] - fit.blank[1]) < 0.5:
        return f"Lay the block flat on a {X} × {Y} in face, so it's {Z} in tall."
    return (f"Lay the block on a {X} × {Y} in face, so it's {Z} in tall, "
            f"with the {X} in side running front to back.")


def turn_words(fit: Fit) -> str | None:
    if fit.yaw == 0:
        return None
    side = "left" if fit.yaw > 0 else "right"
    return (f"The figure sits turned {abs(fit.yaw):.0f}° in the block, nose toward the front {side} corner. "
            f"That makes it {100 * (fit.scale / fit.straight_scale - 1):.0f}% bigger than square on.")
