"""Signed distance primitives for building designs.

Every function takes broadcastable coordinate arrays `x, y, z` and returns
the signed distance to the shape: negative inside, positive outside. Most are
exact; the ellipsoid, the tapered capsule and the flat-faced solids are close
approximations, which is plenty for carving.
"""

import numpy as np
from scipy.spatial import ConvexHull

Vec = tuple[float, float, float]


def sphere(x, y, z, c: Vec, r: float):
    return np.sqrt((x - c[0]) ** 2 + (y - c[1]) ** 2 + (z - c[2]) ** 2) - r


def ellipsoid(x, y, z, c: Vec, radii: Vec):
    px, py, pz = x - c[0], y - c[1], z - c[2]
    rx, ry, rz = radii
    k0 = np.sqrt((px / rx) ** 2 + (py / ry) ** 2 + (pz / rz) ** 2)
    k1 = np.sqrt((px / rx**2) ** 2 + (py / ry**2) ** 2 + (pz / rz**2) ** 2)
    return k0 * (k0 - 1.0) / (k1 + 1e-12)


def capsule(x, y, z, a: Vec, b: Vec, r1: float, r2: float | None = None):
    """Segment a→b thickened by a radius that runs linearly from r1 to r2."""
    r2 = r1 if r2 is None else r2
    bax, bay, baz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    pax, pay, paz = x - a[0], y - a[1], z - a[2]
    t = np.clip((pax * bax + pay * bay + paz * baz) / (bax**2 + bay**2 + baz**2), 0.0, 1.0)
    dist = np.sqrt((pax - bax * t) ** 2 + (pay - bay * t) ** 2 + (paz - baz * t) ** 2)
    return dist - (r1 + (r2 - r1) * t)


def chain(x, y, z, points: list[Vec], r1: float, r2: float | None = None, k: float = 0.0):
    """A bent tube through `points`, tapering from r1 to r2 along its length."""
    r2 = r1 if r2 is None else r2
    lengths = [float(np.linalg.norm(np.subtract(b, a))) for a, b in zip(points, points[1:])]
    total = sum(lengths)
    d, run = None, 0.0
    for (a, b), seg in zip(zip(points, points[1:]), lengths):
        ra = r1 + (r2 - r1) * run / total
        run += seg
        rb = r1 + (r2 - r1) * run / total
        part = capsule(x, y, z, a, b, ra, rb)
        d = part if d is None else smin(d, part, k)
    return d


def tube(x, y, z, points: list[Vec], radii: list[float], k: float = 0.0):
    """A bent tube through `points`, with its own radius at each point."""
    d = None
    for a, b, ra, rb in zip(points, points[1:], radii, radii[1:]):
        part = capsule(x, y, z, a, b, ra, rb)
        d = part if d is None else smin(d, part, k)
    return d


def box(x, y, z, c: Vec, half: Vec, r: float = 0.0):
    """Box centered on c with half-sizes `half`, its edges rounded by r."""
    q = [np.abs(p - ci) - hi + r for p, ci, hi in zip((x, y, z), c, half)]
    outside = np.sqrt(sum(np.maximum(v, 0.0) ** 2 for v in q))
    inside = np.minimum(np.maximum(np.maximum(q[0], q[1]), q[2]), 0.0)
    return outside + inside - r


def facet_box(x, y, z, c: Vec, half: Vec, chamfer: float):
    """Box with its edges and corners cut off flat, like a knife-squared block."""
    qx, qy, qz = (np.abs(p - ci) for p, ci in zip((x, y, z), c))
    bx, by, bz = half
    s2, s3 = 1 / np.sqrt(2), 1 / np.sqrt(3)
    d = np.maximum(np.maximum(qx - bx, qy - by), qz - bz)
    d = np.maximum(d, (qx + qy - bx - by + chamfer) * s2)
    d = np.maximum(d, (qx + qz - bx - bz + chamfer) * s2)
    d = np.maximum(d, (qy + qz - by - bz + chamfer) * s2)
    return np.maximum(d, (qx + qy + qz - bx - by - bz + 1.7 * chamfer) * s3)


def hull(points: list[Vec], mirror: bool = False):
    """A flat-faced solid: the convex hull of `points`. With `mirror`, each point
    also gets its twin across y = 0. Returns a distance function."""
    pts = np.asarray(points, dtype=float)
    if mirror:
        pts = np.vstack([pts, pts * [1, -1, 1]])
    planes = np.unique(np.round(ConvexHull(pts).equations, 9), axis=0)

    def d(x, y, z):
        out = None
        for nx, ny, nz, off in planes:
            v = nx * x + ny * y + nz * z + off
            out = v if out is None else np.maximum(out, v)
        return out

    return d


def smin(a, b, k: float):
    """Union of two shapes, blended over distance k."""
    if k <= 0:
        return np.minimum(a, b)
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b + (a - b) * h - k * h * (1.0 - h)


def smax(a, b, k: float):
    """Intersection of two shapes, blended over distance k."""
    return -smin(-a, -b, k)


def union(*ds, k: float = 0.0):
    out = ds[0]
    for d in ds[1:]:
        out = smin(out, d, k)
    return out


def subtract(d, cutter, k: float = 0.0):
    """Remove `cutter` from `d`."""
    return smax(d, -cutter, k)


def mirror_y(fn):
    """Mirror a one-sided part across the y = 0 plane (left/right symmetry)."""
    return lambda x, y, z: fn(x, np.abs(y), z)
