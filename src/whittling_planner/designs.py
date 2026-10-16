"""Built-in designs, modelled as blends of simple shapes.

Design coordinates: the figure faces +x (nose direction), +y is the figure's
left, +z is up, and the flat base sits on z = 0. Each design is drawn in
inches, sized to fill the smallest block it was made for, so it uses the wood
well. A figure can still go in any block: placement scales and turns it to fit.

"Rustic" designs are built from flat facets (convex hulls and squared blocks),
like Scandinavian flat-plane carving, where the knife cuts are left showing.
"""

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Callable

import numpy as np

from whittling_planner.sdf import (
    box,
    capsule,
    chain,
    ellipsoid,
    facet_box,
    hull,
    mirror_y,
    smax,
    smin,
    sphere,
    subtract,
    tube,
)

# Blocks you can buy, in inches. Carving blocks are sold with the grain running
# along their longest side.
BLOCKS: dict[str, tuple[float, float, float]] = {
    "2x1x1": (2.0, 1.0, 1.0),
    "4x1x1": (4.0, 1.0, 1.0),
    "4x2x2": (4.0, 2.0, 2.0),
    "2x2x1": (2.0, 2.0, 1.0),
}

LEVELS = ("Beginner", "Easy", "Intermediate")


@dataclass(frozen=True)
class Design:
    key: str
    subject: str  # what it is: "Duck"
    name: str  # this version of it: "Sitting duck"
    style: str  # "Classic" (smooth) or "Rustic" (flat facets)
    level: str  # one of LEVELS
    blocks: tuple[str, ...]  # the blocks it was drawn for
    grain: str  # design axes the grain can run along without making weak spots
    blurb: str
    details: str  # what the freehand detail stage carves
    sdf: Callable
    touches: tuple[str, ...] = ()  # finishing touches particular to this design
    # spots to measure for the finishing touches, in design coordinates;
    # a spot with y > 0 is one of a mirrored pair, like the eyes
    spots: tuple[tuple[str, tuple[float, float, float]], ...] = field(default=())
    # the cuts the detail stage calls for, and where: (cut key from learn.CUTS, where)
    cuts: tuple[tuple[str, str], ...] = ()


def flat_base(d, z):
    """Cut everything below z = 0 so the figure stands up."""
    return np.maximum(d, -z)


def pair(fn):
    """A part and its mirror image across the figure's centerline."""
    return mirror_y(fn)


# ---------------------------------------------------------------- ducks


def sitting_duck(x, y, z):
    body = ellipsoid(x, y, z, (-0.12, 0.0, 0.40), (0.76, 0.45, 0.50))
    chest = ellipsoid(x, y, z, (0.22, 0.0, 0.52), (0.44, 0.42, 0.46))
    tail = capsule(x, y, z, (-0.55, 0.0, 0.58), (-0.92, 0.0, 0.86), 0.24, 0.05)
    neck = capsule(x, y, z, (0.24, 0.0, 0.80), (0.36, 0.0, 1.34), 0.27, 0.23)
    head = ellipsoid(x, y, z, (0.36, 0.0, 1.55), (0.36, 0.32, 0.34))
    bill = ellipsoid(x, y, z, (0.74, 0.0, 1.45), (0.24, 0.16, 0.08))
    d = smin(body, chest, 0.15)
    d = smin(d, tail, 0.18)
    d = smin(d, neck, 0.16)
    d = smin(d, head, 0.12)
    d = smin(d, bill, 0.06)
    return flat_base(d, z)


def decoy(x, y, z):
    body = ellipsoid(x, y, z, (-0.10, 0.0, 0.18), (0.86, 0.44, 0.40))
    breast = ellipsoid(x, y, z, (0.38, 0.0, 0.25), (0.46, 0.40, 0.33))
    tail = capsule(x, y, z, (-0.62, 0.0, 0.36), (-0.97, 0.0, 0.46), 0.16, 0.04)
    neck = capsule(x, y, z, (0.40, 0.0, 0.45), (0.47, 0.0, 0.70), 0.17, 0.15)
    head = ellipsoid(x, y, z, (0.50, 0.0, 0.77), (0.24, 0.19, 0.17))
    bill = ellipsoid(x, y, z, (0.78, 0.0, 0.72), (0.19, 0.10, 0.05))
    d = smin(body, breast, 0.12)
    d = smin(d, tail, 0.12)
    d = smin(d, neck, 0.10)
    d = smin(d, head, 0.08)
    d = smin(d, bill, 0.04)
    return flat_base(d, z)


def rustic_duck(x, y, z):
    body = hull(
        [(0.80, 0.24, 0.0), (0.32, 0.40, 0.0), (-0.45, 0.38, 0.0), (-0.85, 0.18, 0.0),
         (0.86, 0.26, 0.20), (0.40, 0.44, 0.24), (-0.50, 0.42, 0.26), (-0.98, 0.10, 0.44),
         (0.55, 0.22, 0.48), (-0.45, 0.26, 0.56), (-0.88, 0.07, 0.54)],
        mirror=True,
    )
    neck = hull([(0.30, 0.19, 0.40), (0.66, 0.19, 0.40), (0.36, 0.15, 0.68), (0.60, 0.15, 0.68)], mirror=True)
    head = hull(
        [(0.30, 0.14, 0.70), (0.30, 0.10, 0.90), (0.42, 0.08, 0.97), (0.58, 0.08, 0.96), (0.48, 0.18, 0.78),
         (0.62, 0.16, 0.80), (0.70, 0.12, 0.88), (0.70, 0.13, 0.72), (0.56, 0.14, 0.62), (0.36, 0.15, 0.60)],
        mirror=True,
    )
    bill = hull([(0.64, 0.10, 0.70), (0.64, 0.10, 0.82), (0.98, 0.06, 0.70), (0.98, 0.05, 0.75)], mirror=True)
    d = np.minimum(np.minimum(body(x, y, z), neck(x, y, z)), np.minimum(head(x, y, z), bill(x, y, z)))
    return flat_base(d, z)


def ducks_in_a_row(x, y, z):
    plinth = box(x, y, z, (0.0, 0.0, 0.07), (1.95, 0.40, 0.08), 0.05)
    lift = 0.12

    def duck_at(x0, s):
        return s * decoy((x - x0) / s, y / s, (z - lift) / s)

    d = smin(plinth, duck_at(0.98, 0.92), 0.04)
    d = smin(d, duck_at(-0.55, 0.52), 0.04)
    d = smin(d, duck_at(-1.48, 0.52), 0.04)
    return flat_base(d, z)


# ---------------------------------------------------------------- cats


def sitting_cat(x, y, z):
    haunches = ellipsoid(x, y, z, (-0.10, 0.0, 0.30), (0.34, 0.38, 0.33))
    torso = capsule(x, y, z, (-0.08, 0.0, 0.34), (0.04, 0.0, 1.06), 0.32, 0.20)
    chest = ellipsoid(x, y, z, (0.10, 0.0, 0.82), (0.22, 0.22, 0.30))
    legs = pair(lambda x, y, z: capsule(x, y, z, (0.18, 0.11, 0.86), (0.25, 0.11, 0.07), 0.095, 0.085))
    paws = pair(lambda x, y, z: ellipsoid(x, y, z, (0.31, 0.11, 0.06), (0.12, 0.09, 0.06)))
    head = ellipsoid(x, y, z, (0.08, 0.0, 1.44), (0.25, 0.29, 0.25))
    muzzle = ellipsoid(x, y, z, (0.27, 0.0, 1.37), (0.11, 0.14, 0.10))
    ears = pair(lambda x, y, z: capsule(x, y, z, (0.06, 0.16, 1.58), (0.03, 0.21, 1.88), 0.11, 0.02))
    tail = tube(
        x, y, z,
        [(-0.40, -0.04, 0.08), (-0.36, -0.28, 0.08), (-0.10, -0.40, 0.07), (0.18, -0.32, 0.065), (0.36, -0.15, 0.06)],
        [0.09, 0.09, 0.085, 0.075, 0.07], k=0.03,
    )
    d = smin(haunches, torso, 0.14)
    d = smin(d, chest, 0.08)
    d = smin(d, legs(x, y, z), 0.05)
    d = smin(d, paws(x, y, z), 0.04)
    d = smin(d, head, 0.08)
    d = smin(d, muzzle, 0.04)
    d = smin(d, ears(x, y, z), 0.04)
    d = smin(d, tail, 0.06)
    return flat_base(d, z)


def rustic_cat(x, y, z):
    body = hull(
        [(0.38, 0.30, 0.0), (0.44, 0.16, 0.0), (-0.40, 0.40, 0.0), (-0.44, 0.20, 0.0),
         (0.34, 0.28, 0.50), (-0.42, 0.36, 0.45),
         (0.22, 0.24, 1.16), (-0.20, 0.26, 1.12), (0.04, 0.20, 1.32)],
        mirror=True,
    )
    paws = pair(hull([(0.30, 0.04, 0.0), (0.46, 0.04, 0.0), (0.30, 0.22, 0.0), (0.46, 0.22, 0.0),
                      (0.30, 0.04, 0.13), (0.42, 0.06, 0.12), (0.30, 0.22, 0.13), (0.42, 0.20, 0.12)]))
    head = facet_box(x, y, z, (0.06, 0.0, 1.46), (0.24, 0.28, 0.23), 0.10)
    muzzle = hull([(0.24, 0.13, 1.30), (0.24, 0.13, 1.48), (0.37, 0.07, 1.33), (0.37, 0.07, 1.44)], mirror=True)
    ears = pair(hull([(-0.06, 0.08, 1.60), (0.16, 0.08, 1.60), (-0.06, 0.27, 1.56), (0.16, 0.27, 1.56),
                      (0.03, 0.21, 1.90), (0.07, 0.21, 1.90)]))
    tail = hull([(-0.44, -0.12, 0.0), (-0.44, -0.12, 0.26), (-0.34, -0.47, 0.0), (-0.34, -0.47, 0.25),
                 (0.10, -0.47, 0.0), (0.10, -0.47, 0.23), (0.34, -0.30, 0.0), (0.34, -0.30, 0.22)])
    d = np.minimum(body(x, y, z), paws(x, y, z))
    d = np.minimum(d, head)
    d = np.minimum(d, muzzle(x, y, z))
    d = np.minimum(d, ears(x, y, z))
    d = np.minimum(d, tail(x, y, z))
    return flat_base(d, z)


def loaf_cat(x, y, z):
    body = box(x, y, z, (-0.16, 0.0, 0.30), (0.72, 0.37, 0.32), 0.26)
    chest = ellipsoid(x, y, z, (0.44, 0.0, 0.32), (0.26, 0.34, 0.32))
    head = ellipsoid(x, y, z, (0.52, 0.0, 0.60), (0.30, 0.35, 0.28))
    muzzle = ellipsoid(x, y, z, (0.76, 0.0, 0.53), (0.12, 0.16, 0.10))
    ears = pair(lambda x, y, z: capsule(x, y, z, (0.52, 0.18, 0.74), (0.50, 0.23, 0.93), 0.14, 0.065))
    paws = pair(lambda x, y, z: ellipsoid(x, y, z, (0.62, 0.14, 0.06), (0.13, 0.09, 0.06)))
    tail = tube(
        x, y, z,
        [(-0.84, -0.10, 0.11), (-0.74, -0.34, 0.11), (-0.35, -0.40, 0.11), (0.08, -0.38, 0.10)],
        [0.12, 0.12, 0.115, 0.10], k=0.03,
    )
    d = smin(body, chest, 0.10)
    d = smin(d, head, 0.12)
    d = smin(d, muzzle, 0.04)
    d = smin(d, ears(x, y, z), 0.05)
    d = smin(d, paws(x, y, z), 0.04)
    d = smin(d, tail, 0.05)
    return flat_base(d, z)


def sleeping_cat(x, y, z):
    cushion = ellipsoid(x, y, z, (-0.10, -0.02, 0.24), (0.82, 0.78, 0.52))
    haunch = ellipsoid(x, y, z, (-0.36, -0.28, 0.36), (0.48, 0.46, 0.44))
    head = ellipsoid(x, y, z, (0.50, 0.30, 0.46), (0.31, 0.32, 0.27))
    muzzle = ellipsoid(x, y, z, (0.70, 0.12, 0.36), (0.13, 0.15, 0.11))
    ear_a = capsule(x, y, z, (0.40, 0.42, 0.62), (0.36, 0.50, 0.86), 0.11, 0.02)
    ear_b = capsule(x, y, z, (0.62, 0.36, 0.64), (0.68, 0.42, 0.87), 0.11, 0.02)
    tail = tube(
        x, y, z,
        [(-0.86, 0.10, 0.10), (-0.70, -0.52, 0.10), (-0.10, -0.84, 0.09), (0.48, -0.64, 0.08), (0.74, -0.18, 0.08),
         (0.76, 0.02, 0.08)],
        [0.13, 0.13, 0.12, 0.11, 0.10, 0.09], k=0.04,
    )
    d = smin(cushion, haunch, 0.15)
    d = smin(d, head, 0.10)
    d = smin(d, muzzle, 0.05)
    d = smin(d, smin(ear_a, ear_b, 0.0), 0.04)
    d = smin(d, tail, 0.06)
    return flat_base(d, z)


# ---------------------------------------------------------------- bears


def standing_bear(x, y, z):
    legs = pair(lambda x, y, z: capsule(x, y, z, (-0.04, 0.19, 0.56), (0.0, 0.19, 0.08), 0.17, 0.15))
    feet = pair(lambda x, y, z: ellipsoid(x, y, z, (0.12, 0.19, 0.07), (0.22, 0.14, 0.08)))
    body = ellipsoid(x, y, z, (-0.05, 0.0, 0.84), (0.36, 0.40, 0.50))
    belly = ellipsoid(x, y, z, (0.08, 0.0, 0.76), (0.30, 0.33, 0.38))
    shoulders = ellipsoid(x, y, z, (-0.02, 0.0, 1.20), (0.30, 0.37, 0.27))
    arms = pair(lambda x, y, z: capsule(x, y, z, (0.0, 0.34, 1.20), (0.18, 0.27, 0.80), 0.12, 0.10))
    head = ellipsoid(x, y, z, (0.04, 0.0, 1.57), (0.26, 0.27, 0.25))
    muzzle = ellipsoid(x, y, z, (0.28, 0.0, 1.51), (0.15, 0.12, 0.10))
    nose = ellipsoid(x, y, z, (0.42, 0.0, 1.55), (0.04, 0.05, 0.035))
    ears = pair(lambda x, y, z: ellipsoid(x, y, z, (-0.02, 0.19, 1.79), (0.07, 0.09, 0.09)))
    d = smin(body, belly, 0.10)
    d = smin(d, shoulders, 0.12)
    d = smin(d, legs(x, y, z), 0.10)
    d = smin(d, feet(x, y, z), 0.06)
    d = smin(d, arms(x, y, z), 0.06)
    d = smin(d, head, 0.10)
    d = smin(d, muzzle, 0.06)
    d = smin(d, nose, 0.02)
    d = smin(d, ears(x, y, z), 0.04)
    return flat_base(d, z)


def walking_bear(x, y, z):
    body = ellipsoid(x, y, z, (-0.14, 0.0, 0.60), (0.62, 0.38, 0.30))
    hump = ellipsoid(x, y, z, (0.16, 0.0, 0.70), (0.30, 0.33, 0.24))
    rump = ellipsoid(x, y, z, (-0.56, 0.0, 0.62), (0.30, 0.36, 0.29))
    front = pair(lambda x, y, z: capsule(x, y, z, (0.28, 0.21, 0.56), (0.34, 0.21, 0.08), 0.14, 0.12))
    back = pair(lambda x, y, z: capsule(x, y, z, (-0.56, 0.21, 0.56), (-0.54, 0.21, 0.08), 0.16, 0.13))
    feet = pair(lambda x, y, z: smin(
        ellipsoid(x, y, z, (0.42, 0.21, 0.06), (0.15, 0.11, 0.06)),
        ellipsoid(x, y, z, (-0.47, 0.21, 0.06), (0.15, 0.12, 0.06)), 0.0))
    neck = capsule(x, y, z, (0.38, 0.0, 0.70), (0.62, 0.0, 0.62), 0.21, 0.18)
    head = ellipsoid(x, y, z, (0.68, 0.0, 0.60), (0.22, 0.21, 0.20))
    muzzle = ellipsoid(x, y, z, (0.88, 0.0, 0.54), (0.13, 0.10, 0.09))
    ears = pair(lambda x, y, z: ellipsoid(x, y, z, (0.62, 0.14, 0.78), (0.06, 0.07, 0.07)))
    d = smin(body, hump, 0.12)
    d = smin(d, rump, 0.12)
    d = smin(d, front(x, y, z), 0.08)
    d = smin(d, back(x, y, z), 0.10)
    d = smin(d, feet(x, y, z), 0.05)
    d = smin(d, neck, 0.10)
    d = smin(d, head, 0.08)
    d = smin(d, muzzle, 0.05)
    d = smin(d, ears(x, y, z), 0.04)
    return flat_base(d, z)


def rustic_bear(x, y, z):
    body = hull(
        [(-0.90, 0.30, 0.0), (0.56, 0.30, 0.0), (-0.92, 0.28, 0.62), (-0.70, 0.34, 0.78), (-0.30, 0.36, 0.84),
         (0.10, 0.36, 0.93), (0.44, 0.32, 0.82), (0.58, 0.30, 0.42)],
        mirror=True,
    )
    belly_gap = facet_box(x, y, z, (-0.15, 0.0, 0.0), (0.34, 0.6, 0.22), 0.06)
    leg_gap = facet_box(x, y, z, (0.18, 0.0, 0.0), (0.40, 0.08, 0.30), 0.02)
    leg_gap = np.minimum(leg_gap, facet_box(x, y, z, (-0.62, 0.0, 0.0), (0.40, 0.08, 0.30), 0.02))
    head = hull(
        [(0.40, 0.22, 0.52), (0.40, 0.20, 0.84), (0.70, 0.16, 0.80), (0.98, 0.08, 0.62), (0.98, 0.08, 0.48),
         (0.74, 0.14, 0.40)],
        mirror=True,
    )
    ears = pair(hull([(0.42, 0.08, 0.74), (0.62, 0.08, 0.74), (0.42, 0.27, 0.72), (0.60, 0.27, 0.72),
                      (0.46, 0.11, 0.93), (0.56, 0.11, 0.93), (0.46, 0.23, 0.92), (0.55, 0.23, 0.92)]))
    d = np.maximum(body(x, y, z), -np.minimum(belly_gap, leg_gap))
    d = np.minimum(d, head(x, y, z))
    d = np.minimum(d, ears(x, y, z))
    return flat_base(d, z)


# ---------------------------------------------------------------- others


def gnome(x, y, z):
    body = facet_box(x, y, z, (-0.05, 0.0, 0.96), (0.40, 0.43, 0.96), 0.16)
    hat = hull(
        [(0.42, 0.18, 1.86), (0.18, 0.45, 1.86), (-0.18, 0.45, 1.86), (-0.46, 0.18, 1.86),
         (0.42, 0.18, 2.00), (0.18, 0.45, 2.00), (-0.18, 0.45, 2.00), (-0.46, 0.18, 2.00),
         (-0.14, 0.03, 3.94), (-0.18, 0.03, 3.94)],
        mirror=True,
    )
    beard = hull(
        [(0.30, 0.36, 1.86), (0.42, 0.30, 1.80), (0.44, 0.22, 1.10), (0.40, 0.06, 0.52), (0.30, 0.04, 0.46),
         (0.22, 0.34, 1.20)],
        mirror=True,
    )
    nose = ellipsoid(x, y, z, (0.36, 0.0, 1.86), (0.10, 0.11, 0.11))
    feet = pair(hull([(0.20, 0.06, 0.0), (0.42, 0.08, 0.0), (0.20, 0.30, 0.0), (0.41, 0.28, 0.0),
                      (0.16, 0.08, 0.32), (0.36, 0.10, 0.30), (0.16, 0.28, 0.32), (0.36, 0.26, 0.30)]))
    d = np.minimum(body, hat(x, y, z))
    d = np.minimum(d, beard(x, y, z))
    d = smin(d, nose, 0.03)
    d = np.minimum(d, feet(x, y, z))
    return flat_base(d, z)


def penguin(x, y, z):
    body = ellipsoid(x, y, z, (-0.02, 0.0, 0.74), (0.41, 0.39, 0.84))
    head = ellipsoid(x, y, z, (0.02, 0.0, 1.62), (0.29, 0.28, 0.30))
    beak = capsule(x, y, z, (0.24, 0.0, 1.62), (0.40, 0.0, 1.59), 0.10, 0.055)
    flippers = pair(lambda x, y, z: ellipsoid(x, y, z, (-0.04, 0.36, 0.90), (0.18, 0.09, 0.44)))
    feet = pair(lambda x, y, z: ellipsoid(x, y, z, (0.21, 0.14, 0.07), (0.16, 0.13, 0.12)))
    tail = capsule(x, y, z, (-0.26, 0.0, 0.20), (-0.36, 0.0, 0.10), 0.13, 0.10)
    d = smin(body, head, 0.14)
    d = smin(d, beak, 0.04)
    d = smin(d, flippers(x, y, z), 0.05)
    d = smin(d, feet(x, y, z), 0.04)
    d = smin(d, tail, 0.05)
    return flat_base(d, z)


def owl(x, y, z):
    body = ellipsoid(x, y, z, (0.0, 0.0, 0.70), (0.40, 0.43, 0.80))
    head = ellipsoid(x, y, z, (0.02, 0.0, 1.44), (0.37, 0.44, 0.37))
    tufts = pair(lambda x, y, z: capsule(x, y, z, (-0.02, 0.24, 1.66), (-0.05, 0.32, 1.90), 0.11, 0.05))
    wings = pair(lambda x, y, z: ellipsoid(x, y, z, (-0.05, 0.34, 0.86), (0.30, 0.12, 0.50)))
    beak = ellipsoid(x, y, z, (0.38, 0.0, 1.36), (0.07, 0.05, 0.10))
    feet = pair(lambda x, y, z: ellipsoid(x, y, z, (0.27, 0.14, 0.07), (0.13, 0.11, 0.10)))
    discs = pair(lambda x, y, z: sphere(x, y, z, (0.52, 0.16, 1.46), 0.18))
    d = smin(body, head, 0.16)
    d = smin(d, tufts(x, y, z), 0.05)
    d = smin(d, wings(x, y, z), 0.04)
    d = subtract(d, discs(x, y, z), 0.03)
    d = smin(d, beak, 0.03)
    d = smin(d, feet(x, y, z), 0.04)
    return flat_base(d, z)


def mushroom(x, y, z):
    stem = capsule(x, y, z, (-0.02, 0.0, 0.0), (0.0, 0.0, 1.30), 0.27, 0.18)
    cap = smax(ellipsoid(x, y, z, (0.0, 0.0, 1.40), (0.46, 0.46, 0.54)), 1.18 - z, 0.05)
    baby_stem = capsule(x, y, z, (0.20, -0.20, 0.0), (0.21, -0.22, 0.42), 0.11, 0.08)
    baby_cap = smax(ellipsoid(x, y, z, (0.21, -0.22, 0.48), (0.19, 0.19, 0.20)), 0.36 - z, 0.03)
    d = smin(stem, cap, 0.04)
    d = smin(d, baby_stem, 0.10)
    d = smin(d, baby_cap, 0.03)
    return flat_base(d, z)


def whale(x, y, z):
    body = ellipsoid(x, y, z, (0.18, 0.0, 0.34), (0.76, 0.42, 0.37))
    stock = tube(x, y, z, [(-0.30, 0.0, 0.40), (-0.62, 0.0, 0.52), (-0.80, 0.0, 0.72)], [0.28, 0.16, 0.09], k=0.05)
    flukes = hull(
        [(-0.62, 0.08, 0.58), (-0.62, 0.08, 0.90), (-0.78, 0.36, 0.62), (-0.88, 0.36, 0.90), (-0.98, 0.12, 0.62),
         (-0.98, 0.12, 0.90)],
        mirror=True,
    )
    flippers = pair(lambda x, y, z: capsule(x, y, z, (0.38, 0.30, 0.20), (0.20, 0.42, 0.11), 0.10, 0.07))
    d = smin(body, stock, 0.12)
    d = smin(d, flukes(x, y, z), 0.05)
    d = smin(d, flippers(x, y, z), 0.04)
    return flat_base(d, z)


def turtle(x, y, z):
    shell = ellipsoid(x, y, z, (-0.06, 0.0, 0.14), (0.76, 0.66, 0.68))
    neck = capsule(x, y, z, (0.56, 0.0, 0.22), (0.80, 0.0, 0.28), 0.18, 0.16)
    head = ellipsoid(x, y, z, (0.84, 0.0, 0.29), (0.17, 0.15, 0.14))
    front = pair(lambda x, y, z: ellipsoid(x, y, z, (0.44, 0.58, 0.12), (0.24, 0.24, 0.14)))
    back = pair(lambda x, y, z: ellipsoid(x, y, z, (-0.54, 0.52, 0.11), (0.22, 0.22, 0.13)))
    tail = capsule(x, y, z, (-0.74, 0.0, 0.14), (-0.90, 0.0, 0.10), 0.10, 0.07)
    d = smin(shell, neck, 0.08)
    d = smin(d, head, 0.06)
    d = smin(d, front(x, y, z), 0.08)
    d = smin(d, back(x, y, z), 0.08)
    d = smin(d, tail, 0.04)
    return flat_base(d, z)


def frog(x, y, z):
    body = ellipsoid(x, y, z, (-0.04, 0.0, 0.32), (0.70, 0.60, 0.36))
    head = ellipsoid(x, y, z, (0.44, 0.0, 0.46), (0.42, 0.56, 0.30))
    eyes = pair(lambda x, y, z: sphere(x, y, z, (0.46, 0.32, 0.76), 0.17))
    haunches = pair(lambda x, y, z: ellipsoid(x, y, z, (-0.36, 0.60, 0.22), (0.46, 0.30, 0.22)))
    back_feet = pair(lambda x, y, z: ellipsoid(x, y, z, (0.06, 0.72, 0.09), (0.24, 0.15, 0.12)))
    arms = pair(lambda x, y, z: capsule(x, y, z, (0.50, 0.40, 0.30), (0.72, 0.47, 0.09), 0.11, 0.10))
    hands = pair(lambda x, y, z: ellipsoid(x, y, z, (0.74, 0.46, 0.09), (0.14, 0.13, 0.12)))
    d = smin(body, head, 0.14)
    d = smin(d, eyes(x, y, z), 0.06)
    d = smin(d, haunches(x, y, z), 0.10)
    d = smin(d, back_feet(x, y, z), 0.05)
    d = smin(d, arms(x, y, z), 0.05)
    d = smin(d, hands(x, y, z), 0.04)
    return flat_base(d, z)


def dachshund(x, y, z):
    body = capsule(x, y, z, (-1.20, 0.0, 0.52), (0.86, 0.0, 0.52), 0.36)
    chest = ellipsoid(x, y, z, (0.86, 0.0, 0.44), (0.42, 0.36, 0.36))
    front = pair(lambda x, y, z: capsule(x, y, z, (0.98, 0.20, 0.40), (1.08, 0.20, 0.07), 0.13, 0.11))
    back = pair(lambda x, y, z: capsule(x, y, z, (-1.18, 0.20, 0.42), (-1.18, 0.20, 0.07), 0.15, 0.12))
    feet = pair(lambda x, y, z: smin(
        ellipsoid(x, y, z, (1.15, 0.20, 0.05), (0.16, 0.11, 0.05)),
        ellipsoid(x, y, z, (-1.10, 0.20, 0.05), (0.16, 0.12, 0.05)), 0.0))
    neck = capsule(x, y, z, (1.06, 0.0, 0.60), (1.34, 0.0, 0.76), 0.20, 0.16)
    head = ellipsoid(x, y, z, (1.44, 0.0, 0.78), (0.23, 0.19, 0.17))
    snout = capsule(x, y, z, (1.56, 0.0, 0.76), (1.88, 0.0, 0.69), 0.12, 0.075)
    ears = pair(lambda x, y, z: ellipsoid(x, y, z, (1.38, 0.20, 0.66), (0.14, 0.07, 0.20)))
    tail = capsule(x, y, z, (-1.42, 0.0, 0.62), (-1.90, 0.0, 0.80), 0.08, 0.035)
    d = smin(body, chest, 0.12)
    d = smin(d, front(x, y, z), 0.06)
    d = smin(d, back(x, y, z), 0.07)
    d = smin(d, feet(x, y, z), 0.04)
    d = smin(d, neck, 0.10)
    d = smin(d, head, 0.08)
    d = smin(d, snout, 0.06)
    d = smin(d, ears(x, y, z), 0.04)
    d = smin(d, tail, 0.05)
    return flat_base(d, z)


# ---------------------------------------------------------------- catalog

TALL = ("2x1x1", "4x2x2")  # a 1 × 1 × 2 shape: the block stands on end
LONG = ("2x1x1", "4x2x2")  # a 2 × 1 × 1 shape: the block lies on its side

FACETS = "Leave the knife facets showing; don't sand them smooth. Crisp, flat cuts are the rustic look."
EYES = "Eyes: check the marks are level from the front, then press in a round eye punch or cut a small triangle-shaped chip."

DESIGNS: dict[str, Design] = {
    d.key: d
    for d in [
        Design(
            "duck-sitting", "Duck", "Sitting duck", "Classic", "Easy", ("2x2x1",), "x",
            "A plump duck with its head held high. Uses a 2 × 2 × 1 block stood on its edge.",
            "under the bill, where the neck meets the body, and the tail",
            sitting_duck,
            (EYES, "Wings: outline each wing with a shallow V-cut, sweeping from the shoulder back to the tail.",
             "Bill: a light cut where the bill meets the head."),
            (("eyes", (0.56, 0.24, 1.62)),),
            cuts=(
                ("stop", "where the neck meets the back and the chest, and under the bill"),
                ("scoop", "the curve of the neck, front and back"),
                ("push", "the end-grain tip of the bill"),
            ),
        ),
        Design(
            "duck-decoy", "Duck", "Decoy", "Classic", "Easy", LONG, "x",
            "A long, low duck like an old hunting decoy: the most forgiving duck to carve.",
            "under the bill and where the neck meets the back",
            decoy,
            (EYES, "Wings: a V-cut along each side marks the folded wing.",
             "Paint: decoys look right painted, with a dark head and a light breast."),
            (("eyes", (0.62, 0.15, 0.82)),),
            cuts=(
                ("stop", "where the head meets the back, and under the bill"),
                ("scoop", "the dip of the neck behind the head"),
                ("pull", "rounding the long body"),
            ),
        ),
        Design(
            "duck-rustic", "Duck", "Rustic duck", "Rustic", "Beginner", LONG, "x",
            "A flat-plane decoy: every surface is a single straight knife cut.",
            "the flat facets of the head and bill",
            rustic_duck,
            (FACETS, "Eyes: a small triangle chip cut on each side of the head."),
            (("eyes", (0.56, 0.12, 0.85)),),
            cuts=(
                ("facet", "every surface: one flat cut each"),
                ("stop", "where the head meets the back"),
            ),
        ),
        Design(
            "ducks-row", "Duck", "Ducks in a row", "Classic", "Easy", ("4x1x1",), "x",
            "A mother duck and two ducklings on a strip of water. Made for a 4 × 1 × 1 stick.",
            "the gaps between the ducks, under each bill, and around the necks",
            ducks_in_a_row,
            ("Gaps: work the gaps between the ducks from both sides, with stop cuts, so the base doesn't split.",
             "Water: a few long, shallow gouge or V-cuts along the base suggest ripples.", EYES),
            (("mother's eyes", (1.55, 0.14, 0.88)),),
            cuts=(
                ("stop", "both sides of each gap between the ducks"),
                ("lever", "cleaning out the narrow gaps with the knife tip"),
                ("scoop", "around each neck"),
            ),
        ),
        Design(
            "cat-sitting", "Cat", "Sitting cat", "Classic", "Intermediate", TALL, "z",
            "An upright cat with its tail wrapped around its paws.",
            "between the front legs, under the chin, where the tail meets the body, and the ears",
            sitting_cat,
            (EYES, "Face: a small V-cut for the mouth and two shallow lines for the nose.",
             "Ears: hollow the front of each ear slightly with the knife tip."),
            (("eyes", (0.29, 0.12, 1.48)),),
            cuts=(
                ("stop", "under the chin, between the front legs, and where the tail meets the body"),
                ("lever", "the ears, a little at a time from both sides"),
                ("vcut", "the line between the front legs"),
            ),
        ),
        Design(
            "cat-rustic", "Cat", "Rustic cat", "Rustic", "Beginner", TALL, "z",
            "A blocky sitting cat in flat planes, with the tail carved as a band around the base.",
            "the ears, the facets of the head, and the edge of the tail band",
            rustic_cat,
            (FACETS, "Eyes: two small triangle chips.", "Whiskers: three light knife lines each side of the muzzle."),
            (("eyes", (0.31, 0.12, 1.52)),),
            cuts=(
                ("facet", "the planes of the body and head"),
                ("stop", "the top edge of the tail band, and the notch between the ears"),
            ),
        ),
        Design(
            "cat-loaf", "Cat", "Loaf cat", "Classic", "Beginner", LONG, "x",
            "A cat tucked into a loaf, paws hidden, tail along its side. Almost no thin parts.",
            "around the head and ears, and along the tail",
            loaf_cat,
            (EYES, "Face: a small V-cut for the mouth and nose.", "Fur: optional short knife strokes along the back."),
            (("eyes", (0.74, 0.14, 0.66)),),
            cuts=(
                ("stop", "around the head, where it meets the body"),
                ("pull", "rounding the loaf"),
                ("lever", "the ears"),
            ),
        ),
        Design(
            "cat-sleeping", "Cat", "Sleeping cat", "Classic", "Easy", ("2x2x1",), "xy",
            "A cat curled up asleep, tail around its nose. Made for a 2 × 2 × 1 block lying flat.",
            "around the head and ears, and along the tail where it meets the body",
            sleeping_cat,
            ("Closed eyes: two short curved knife lines.",
             "Fur: long, flowing knife strokes following the curl of the body."),
            (("head", (0.62, 0.36, 0.70)),),
            cuts=(
                ("stop", "along the tail where it lies on the body, and around the head"),
                ("pull", "rounding the curled body"),
                ("lever", "the ears"),
            ),
        ),
        Design(
            "bear-standing", "Bear", "Standing bear", "Classic", "Easy", TALL, "z",
            "A bear up on its hind legs, arms down. Chunky, with nothing thin to break.",
            "between the arms and the body, between the legs, and around the muzzle and ears",
            standing_bear,
            (EYES, "Fur: short knife strokes or small gouge cuts over the body, following the shape.",
             "Claws: three tiny V-cuts on each foot."),
            (("eyes", (0.22, 0.10, 1.65)),),
            cuts=(
                ("stop", "under the arms, between the legs and under the muzzle"),
                ("scoop", "the hollow between the legs"),
                ("lever", "around the ears and the muzzle"),
            ),
        ),
        Design(
            "bear-walking", "Bear", "Walking bear", "Classic", "Intermediate", LONG, "x",
            "A bear on all fours, head low, with a shoulder hump.",
            "between the legs, under the belly, under the chin, and the ears",
            walking_bear,
            (EYES, "Fur: short strokes along the back and the hump.", "Claws: small V-cuts on each foot."),
            (("eyes", (0.82, 0.10, 0.66)),),
            cuts=(
                ("stop", "the inside corners between the legs and the belly, and under the chin"),
                ("scoop", "under the belly, from both ends toward the middle"),
                ("lever", "between the legs, and the ears"),
            ),
        ),
        Design(
            "bear-rustic", "Bear", "Rustic bear", "Rustic", "Easy", LONG, "x",
            "A folk-art bear in flat planes, legs as solid blocks. A classic first animal.",
            "the gap under the belly, the slots between the legs, and the facets of the head",
            rustic_bear,
            (FACETS, "Eyes: two small triangle chips.", "Nose: blacken the tip of the snout with a marker or paint."),
            (("eyes", (0.74, 0.12, 0.72)),),
            cuts=(
                ("stop", "the gap under the belly and the slots between the legs: a stop cut at each leg, then slice out between them"),
                ("facet", "the planes of the head and body"),
            ),
        ),
        Design(
            "gnome", "Gnome", "Gnome", "Rustic", "Beginner", ("4x1x1",), "z",
            "The classic first carving: tall hat, big nose, long beard. Made for a 4 × 1 × 1 stick.",
            "under the hat brim around the nose, and the edges of the beard",
            gnome,
            (FACETS, "Beard: long V-cuts down the beard.", "Paint: a red hat and a dot of pink on the nose."),
            (("nose", (0.46, 0.0, 1.86)),),
            cuts=(
                ("stop", "under the hat brim and around the nose"),
                ("facet", "the hat and the robe"),
                ("push", "rounding the end of the nose"),
            ),
        ),
        Design(
            "penguin", "Penguin", "Penguin", "Classic", "Beginner", TALL, "z",
            "A round, upright penguin. Simple curves and a short beak.",
            "under the beak and around the flippers and feet",
            penguin,
            (EYES, "Paint: black back and head, white front, orange beak and feet."),
            (("eyes", (0.22, 0.15, 1.70)),),
            cuts=(
                ("pull", "rounding the body, from the top down"),
                ("push", "the beak, and the end grain on top of the head"),
                ("stop", "under the beak, and along the flippers and feet"),
            ),
        ),
        Design(
            "owl", "Owl", "Owl", "Classic", "Easy", TALL, "z",
            "A plump owl with ear tufts and a dished face.",
            "the dished face around each eye, the beak, the tufts, and the wing edges",
            owl,
            ("Eyes: big round eyes in the middle of each dish: an eye punch, or a circle cut with the knife tip.",
             "Feathers: small scalloped cuts on the chest, and long V-cuts along the wings."),
            (("eyes", (0.36, 0.16, 1.46)),),
            cuts=(
                ("scoop", "the two dished eye hollows, each from its rim toward the middle"),
                ("stop", "around the edge of the face and under the beak"),
                ("lever", "between the ear tufts"),
            ),
        ),
        Design(
            "mushroom", "Mushroom", "Toadstool", "Classic", "Beginner", TALL, "z",
            "A tall toadstool with a little one at its foot. Keep the cap's rim thick.",
            "under the caps, around the stems, and between the two mushrooms",
            mushroom,
            ("Gills: fine knife lines under each cap, running out from the stem.",
             "Paint: red caps with white dots make a classic fly agaric."),
            cuts=(
                ("stop", "under each cap where it meets the stem, and between the two mushrooms"),
                ("scoop", "the underside of each cap"),
                ("pull", "rounding the caps"),
            ),
        ),
        Design(
            "whale", "Whale", "Whale", "Classic", "Beginner", LONG, "x",
            "A whale with its tail curled up. Smooth curves all over.",
            "under the tail stock, around the flippers, and the edges of the flukes",
            whale,
            (EYES, "Mouth: one long, shallow V-cut from the snout back toward each eye."),
            (("eyes", (0.62, 0.30, 0.30)),),
            cuts=(
                ("pull", "the long, smooth body"),
                ("stop", "under the tail stock and along the flippers"),
                ("scoop", "the dip of the back up into the tail"),
            ),
        ),
        Design(
            "turtle", "Turtle", "Turtle", "Classic", "Beginner", ("2x2x1",), "xy",
            "A domed turtle with stubby legs. Made for a 2 × 2 × 1 block lying flat.",
            "under the shell rim, around the legs and neck",
            turtle,
            ("Shell: lay out hexagons on the shell with a pencil, then V-cut the lines.", EYES),
            (("eyes", (0.92, 0.10, 0.33)),),
            cuts=(
                ("stop", "under the edge of the shell, around the legs and the neck"),
                ("pull", "doming the shell"),
                ("push", "rounding the head and the stubby legs"),
            ),
        ),
        Design(
            "frog", "Frog", "Frog", "Classic", "Easy", ("2x2x1",), "xy",
            "A squat frog with bulging eyes. Made for a 2 × 2 × 1 block lying flat.",
            "between the legs and the body, under the chin, and around the eye bumps",
            frog,
            ("Mouth: one long V-cut around the front of the head, from cheek to cheek.",
             "Eyes: a pupil in each eye bump with an eye punch or the knife tip."),
            (("eyes", (0.52, 0.32, 0.88)),),
            cuts=(
                ("stop", "where the legs meet the body, and under the chin"),
                ("scoop", "the dips around the eye bumps"),
                ("push", "rounding the eye bumps"),
            ),
        ),
        Design(
            "dachshund", "Dog", "Dachshund", "Classic", "Intermediate", ("4x1x1",), "x",
            "A long, low sausage dog. Made for a 4 × 1 × 1 stick lying on its side.",
            "between the legs, under the chin, the ears, and where the tail meets the body",
            dachshund,
            (EYES, "Ears: undercut the bottom edge of each ear so it hangs free of the head."),
            (("eyes", (1.56, 0.12, 0.86)),),
            cuts=(
                ("stop", "between the legs, under the chin, and along the bottom of each ear"),
                ("lever", "cleaning out between the legs with the knife tip"),
                ("scoop", "under the belly, from both ends toward the middle"),
            ),
        ),
    ]
}


# ---------------------------------------------------------------- measuring a design


@dataclass(frozen=True)
class Shape:
    """A design's surface, sampled once: points on it (design units), and its volume."""

    points: np.ndarray  # (n, 3)
    volume: float  # cubic design units
    lo: np.ndarray
    hi: np.ndarray
    grid: tuple  # (origin, step, values) of the fine sampling, for previews


@lru_cache(maxsize=None)
def shape(key: str) -> Shape:
    """Find a design's surface: a coarse search for where it is, then a fine
    sampling there, with the samples near the surface pulled onto it."""
    sdf = DESIGNS[key].sdf
    lo, hi = np.array([-2.5, -2.5, -0.1]), np.array([2.5, 2.5, 4.2])
    step = 0.08
    axes = [np.arange(lo[i], hi[i] + step, step) for i in range(3)]
    near = sdf(axes[0][:, None, None], axes[1][None, :, None], axes[2][None, None, :]) < step
    idx = [np.flatnonzero(near.any(axis=tuple(a for a in range(3) if a != i))) for i in range(3)]
    lo = np.array([axes[i][idx[i][0]] for i in range(3)]) - 2 * step
    hi = np.array([axes[i][idx[i][-1]] for i in range(3)]) + 2 * step
    lo[2] = max(lo[2], -0.04)

    step = 0.02
    axes = [np.arange(lo[i], hi[i] + step, step) for i in range(3)]
    values = sdf(axes[0][:, None, None], axes[1][None, :, None], axes[2][None, None, :])
    volume = float((values < 0).sum()) * step**3
    band = np.argwhere(np.abs(values) < step)
    p = lo + band * step
    # Newton steps toward the surface along the field's gradient
    for _ in range(2):
        f = sdf(p[:, 0], p[:, 1], p[:, 2])
        e = 1e-3
        g = np.stack([
            (sdf(p[:, 0] + e, p[:, 1], p[:, 2]) - sdf(p[:, 0] - e, p[:, 1], p[:, 2])) / (2 * e),
            (sdf(p[:, 0], p[:, 1] + e, p[:, 2]) - sdf(p[:, 0], p[:, 1] - e, p[:, 2])) / (2 * e),
            (sdf(p[:, 0], p[:, 1], p[:, 2] + e) - sdf(p[:, 0], p[:, 1], p[:, 2] - e)) / (2 * e),
        ], axis=1)
        move = (f / np.maximum((g**2).sum(axis=1), 1e-6))[:, None] * g
        length = np.linalg.norm(move, axis=1, keepdims=True)
        p = p - move * np.minimum(1.0, 1.5 * step / np.maximum(length, 1e-12))  # never jump far
    p = p[np.abs(sdf(p[:, 0], p[:, 1], p[:, 2])) < step / 4]
    p[:, 2] = np.maximum(p[:, 2], 0.0)
    return Shape(p, volume, p.min(axis=0), p.max(axis=0), (lo, step, values.astype(np.float32)))


def bounds(key: str) -> tuple[np.ndarray, np.ndarray]:
    """Tight bounding box (lo, hi) of a design, in design units."""
    s = shape(key)
    return s.lo, s.hi
