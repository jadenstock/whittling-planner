"""Voxel-grid geometry: sampling shapes on a grid and carving silhouettes.

Shapes are stored as fields sampled on a regular grid, in millimetres:
negative inside, positive outside, and roughly the distance to the surface.
Intersecting two shapes is the elementwise max of their fields.
"""

from dataclasses import dataclass

import numpy as np

PAD = 3  # grid cells outside the blank, so every surface closes


@dataclass
class Grid:
    origin: np.ndarray  # world position (mm) of cell (0, 0, 0)
    h: float  # cell size, mm
    shape: tuple[int, int, int]

    def axes(self):
        return [self.origin[i] + self.h * np.arange(self.shape[i]) for i in range(3)]

    def broadcast_axes(self):
        x, y, z = self.axes()
        return x[:, None, None], y[None, :, None], z[None, None, :]


def make_grid(blank: np.ndarray, detail: int) -> Grid:
    """A grid of cubic cells over the blank, about `detail`³ cells in all,
    whatever the blank's proportions."""
    h = float(np.cbrt(np.prod(blank)) / detail)
    n = np.ceil(blank / h).astype(int) + 1 + 2 * PAD
    origin = (blank - (n - 1) * h) / 2  # center the blank in the grid
    return Grid(origin, h, tuple(int(v) for v in n))


def box_field(grid: Grid, size: np.ndarray) -> np.ndarray:
    """Signed distance to the box [0, size]."""
    x, y, z = grid.broadcast_axes()
    q = [np.abs(c - s / 2) - s / 2 for c, s in zip((x, y, z), size)]
    outside = np.sqrt(sum(np.maximum(c, 0) ** 2 for c in q))
    inside = np.minimum(np.maximum(np.maximum(q[0], q[1]), q[2]), 0)
    return outside + inside


def silhouette(field: np.ndarray, axis: int) -> np.ndarray:
    """2D outline of a shape seen along an axis: min over that axis.

    Outside the outline this is the exact distance to it in the viewing plane.
    """
    return field.min(axis=axis)


def extrude(sil: np.ndarray, axis: int, shape) -> np.ndarray:
    """Push a 2D outline straight through the grid along `axis`."""
    return np.broadcast_to(np.expand_dims(sil, axis), shape)


def diagonal_extrusion(field: np.ndarray, a: int, b: int, flip: bool) -> np.ndarray:
    """Outline seen along a 45° direction in the (a, b) plane, pushed back through the grid.

    The view direction is +a+b, or +a-b when `flip`. Grid points line up exactly
    along those diagonals, so this needs no resampling.
    """
    arr = np.moveaxis(field, (a, b), (0, 1))
    if flip:
        arr = arr[:, ::-1]
    na, nb = arr.shape[:2]
    offsets = range(-(na - 1), nb)
    lines = np.stack([np.diagonal(arr, offset=o, axis1=0, axis2=1).min(axis=-1) for o in offsets])
    i = np.arange(na)[:, None]
    j = np.arange(nb)[None, :]
    out = lines[j - i + (na - 1)]  # (na, nb, rest)
    if flip:
        out = out[:, ::-1]
    return np.moveaxis(out, (0, 1), (a, b))


def sample(field: np.ndarray, grid: Grid, points: np.ndarray) -> np.ndarray:
    """Trilinear lookup of a field at world points (n, 3)."""
    from scipy.ndimage import map_coordinates

    idx = ((points - grid.origin) / grid.h).T
    return map_coordinates(field, idx, order=1, mode="nearest")
