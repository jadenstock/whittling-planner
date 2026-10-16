"""Marking out: how to draw each outline on the block with a ruler and a
square, instead of gluing on a printed template.

An outline is measured along evenly spaced lines drawn across the face
("stations"). On each station, the measurements say where the wood starts and
stops. Points the stations miss, like the tip of an ear, are listed separately
with both of their measurements.
"""

from dataclasses import dataclass
from string import ascii_uppercase

import numpy as np
from scipy.ndimage import map_coordinates
from skimage.measure import find_contours

from whittling_planner.geometry import Grid
from whittling_planner.units import inches

IN = 25.4
MAX_TIPS = 8


@dataclass(frozen=True)
class View:
    key: str
    title: str
    axis: int  # the outline is the figure seen along this world axis
    right: tuple[int, bool]  # world axis running to the drawing's right, and whether it runs backward
    up: tuple[int, bool]  # world axis running up the drawing
    edges: tuple[tuple[str, str], ...]  # which block face each edge of the drawing is
    where: str


VIEWS = {
    1: View("side", "Side", 1, (0, False), (2, False),
            (("right", "FRONT"), ("left", "BACK"), ("top", "TOP"), ("bottom", "BOTTOM")),
            "Mark the outline on the RIGHT side, then on the LEFT side. It's mirrored there, "
            "but the measurements are the same."),
    0: View("front", "Front", 0, (1, False), (2, False),
            (("right", "LEFT"), ("left", "RIGHT"), ("top", "TOP"), ("bottom", "BOTTOM")),
            "Mark the outline on the FRONT end, then the same on the BACK end."),
    2: View("top", "Top", 2, (1, True), (0, False),
            (("top", "FRONT"), ("bottom", "BACK"), ("right", "RIGHT"), ("left", "LEFT")),
            "Mark the outline on what's left of the top. Redraw the centerline first if earlier cuts took it off."),
}


def station_axis(axes: list[int], blank: np.ndarray) -> int:
    """Stations run along the face's longer side; on a square face, up, else front to back."""
    return max(axes, key=lambda a: (round(blank[a], 1), a == 2, a == 0))


def spacing(length_mm: float) -> float:
    """1/8 in on short sides, 1/4 in on longer ones."""
    return IN / 8 if length_mm <= 1.3 * IN else IN / 4


class Ruler:
    """How a world coordinate along one axis is measured on the block."""

    def __init__(self, axis: int, blank: np.ndarray, symmetric: bool):
        self.axis, self.blank, self.symmetric = axis, blank, symmetric
        self.center = blank[1] / 2

    def __call__(self, v: float) -> float:
        if self.axis == 0:
            return self.blank[0] - v  # from the front
        if self.axis == 1:
            return abs(v - self.center) if self.symmetric else v  # from the centerline, or the right side
        return v  # up from the bottom

    def world(self, m: float) -> float:
        return self.blank[0] - m if self.axis == 0 else m

    @property
    def head(self) -> str:
        return {0: "From the front", 1: "Each side of the centerline" if self.symmetric else "From the RIGHT side",
                2: "Up from the bottom"}[self.axis]

    def words(self, v: float) -> str:
        m = self(v)
        if self.axis == 0:
            return f"{inches(m)} in from the front"
        if self.axis == 2:
            return f"{inches(m)} in up"
        if self.symmetric:
            return "on the centerline" if m < 0.8 else f"{inches(m)} in each side of center"
        return f"{inches(m)} in from the RIGHT side"


def _runs(values: np.ndarray, t: np.ndarray) -> list[tuple[float, float]]:
    """Intervals of t where `values` < 0, with the ends found by linear interpolation."""
    inside = values < 0
    out, start = [], None
    for i in range(len(t)):
        if inside[i] and start is None:
            start = t[0] if i == 0 else t[i - 1] + (t[i] - t[i - 1]) * values[i - 1] / (values[i - 1] - values[i])
        elif not inside[i] and start is not None:
            end = t[i - 1] + (t[i] - t[i - 1]) * values[i - 1] / (values[i - 1] - values[i])
            out.append((float(start), float(end)))
            start = None
    if start is not None:
        out.append((float(start), float(t[-1])))
    return out


def _extrema(v: np.ndarray, w: int, prominence: float) -> list[int]:
    """Indices of local maxima of a closed curve's coordinate `v` that stand at
    least `prominence` above the curve `w` points away on either side."""
    n = len(v)
    if n < 2 * w + 1:
        return []
    idx = (np.arange(n)[:, None] + np.arange(-w, w + 1)[None, :]) % n
    win = v[idx]
    ok = (v >= win.max(axis=1)) & (v - np.maximum(win[:, 0], win[:, -1]) >= prominence)
    out, last = [], -10 * w
    for i in np.flatnonzero(ok):
        if i - last > w:
            out.append(int(i))
            last = i
    return out


@dataclass
class FaceMarks:
    key: str
    title: str
    where: str
    station_head: str
    across_head: str
    rows: list[dict]
    tips: list[dict]
    svg: str
    station_axis: int
    station_step: float  # mm

    def as_json(self) -> dict:
        return {k: getattr(self, k) for k in ("key", "title", "where", "station_head", "across_head", "rows", "tips", "svg")}


def face_marks(sil: np.ndarray, grid: Grid, blank: np.ndarray, view_axis: int) -> FaceMarks:
    view = VIEWS[view_axis]
    kept = [a for a in range(3) if a != view_axis]
    s_axis = station_axis(kept, blank)
    t_axis = kept[1 - kept.index(s_axis)]
    symmetric = 1 in kept and _is_symmetric(sil, kept.index(1))
    s_ruler, t_ruler = Ruler(s_axis, blank, symmetric), Ruler(t_axis, blank, symmetric)
    step = spacing(blank[s_axis])

    def sample(s_world: float, t_world: np.ndarray) -> np.ndarray:
        coords = np.empty((2, len(t_world)))
        coords[kept.index(s_axis)] = (s_world - grid.origin[s_axis]) / grid.h
        coords[kept.index(t_axis)] = (t_world - grid.origin[t_axis]) / grid.h
        return map_coordinates(sil, coords, order=1, mode="nearest")

    # stations, measured from the front or up from the bottom
    marks = [k * step for k in range(1, int((blank[s_axis] - step / 3) / step) + 1)]
    if s_axis == 2:
        marks = [min(0.6, grid.h)] + marks  # just above the bottom edge: where the base is
    t = np.linspace(0, blank[t_axis], int(blank[t_axis] / (grid.h / 4)) + 2)
    rows, stations = [], []
    for m in marks:
        s_world = s_ruler.world(m)
        runs = _runs(sample(s_world, t), t)
        if not runs:
            continue
        intervals = set()
        for a, b in runs:
            if _spans(t_ruler, a, b):  # across the centerline: "out to w" each side
                intervals.add((0.0, max(t_ruler(a), t_ruler(b))))
            elif not t_ruler.symmetric or a >= t_ruler.center - 1e-6:  # skip mirror twins
                intervals.add(tuple(sorted((t_ruler(a), t_ruler(b)))))
        intervals = sorted(intervals)
        text = ", ".join(_interval_words(lo, hi, t_ruler.symmetric) for lo, hi in intervals)
        rows.append({"at": "0 (bottom edge)" if m < 1 else inches(m), "marks": text})
        stations.append((s_world, runs))

    tips = _tips(sil, grid, kept, s_axis, t_axis, s_ruler, t_ruler, step, blank)
    svg = render(view, kept, blank, sil, grid, s_axis, stations, tips, symmetric)
    tip_json = [{"label": label, "text": f"{s_ruler.words(s)}, {t_ruler.words(tv)}"} for label, s, tv in tips]
    return FaceMarks(
        view.key, f"{view.title} outline", view.where, s_ruler.head, f"Wood: {t_ruler.head.lower()}",
        rows, tip_json, svg, s_axis, step,
    )


def _is_symmetric(sil: np.ndarray, y_index: int) -> bool:
    inside = sil < 0
    flipped = np.flip(inside, axis=y_index)
    return bool((inside ^ flipped).sum() <= 0.01 * max(inside.sum(), 1))


def _spans(r: Ruler, a: float, b: float) -> bool:
    return r.symmetric and a < r.center < b


def _interval_words(lo: float, hi: float, symmetric: bool) -> str:
    a, b = inches(lo), inches(hi)
    if symmetric and lo < 0.4:
        return f"out to {b}"
    return a if a == b else f"{a} to {b}"


def _tips(sil, grid, kept, s_axis, t_axis, s_ruler, t_ruler, step, blank):
    """Landmarks: the outline's extremes, and points that stick out between stations."""
    loops = [c for c in find_contours(sil, 0.0) if len(c) >= 8]
    if not loops:
        return []
    found = []  # (priority, s_world, t_world)
    w = max(3, int(round(5.0 / grid.h)))
    for loop in loops:
        pts = np.column_stack([grid.origin[kept[k]] + grid.h * loop[:, k] for k in range(2)])
        s = pts[:, kept.index(s_axis)]
        t = pts[:, kept.index(t_axis)]
        for coord, sign in ((s, 1), (s, -1), (t, 1), (t, -1)):
            for i in _extrema(sign * coord, w, 1.2):
                found.append((1, s[i], t[i]))
        for coord in (s, t):  # the overall extremes always count
            for i in (int(np.argmax(coord)), int(np.argmin(coord))):
                found.append((0, s[i], t[i]))

    keep = []
    station_marks = [s_ruler.world(k * step) for k in range(1, int(blank[s_axis] / step) + 1)]
    for prio, s, tv in sorted(found, key=lambda f: f[0]):
        if s_axis == 2 and s < 2.5 or t_axis == 2 and tv < 2.5:
            continue  # on the base: the bottom-edge station covers it
        if t_ruler.symmetric and tv < t_ruler.center - 0.5:
            continue  # the mirror twin of a point on the other side
        if any(np.hypot(s - ks, tv - kt) < 3.0 for _, ks, kt in keep):
            continue
        if prio and any(abs(s - m) < 0.8 for m in station_marks):
            continue  # a station already passes through it
        keep.append((prio, s, tv))
        if len(keep) == MAX_TIPS:
            break
    # label top to bottom, then front to back
    keep.sort(key=lambda k: (-_paper_y_rank(k, s_axis, t_axis), _paper_x_rank(k, s_axis, t_axis)))
    return [(ascii_uppercase[i], s, tv) for i, (_, s, tv) in enumerate(keep)]


def _paper_y_rank(k, s_axis, t_axis):
    _, s, t = k
    return s if s_axis in (0, 2) else t


def _paper_x_rank(k, s_axis, t_axis):
    _, s, t = k
    return -(t if s_axis in (0, 2) else s)


# ---------------------------------------------------------------- drawing


def render(view: View, kept, blank, sil, grid: Grid, s_axis, stations, tips, symmetric) -> str:
    """An on-screen diagram of the face: the outline, the waste hatched, the
    stations with a dot where each one meets the outline, and the landmarks."""
    ra, rrev = view.right
    ua, urev = view.up
    fw, fh = blank[ra], blank[ua]
    fs = 0.06 * max(fw, fh)  # font size, so labels look the same size on any block
    sw = fs * 0.07
    ml = fs * (3.4 if s_axis == ua else 1.6)
    mb = fs * (3.0 if s_axis == ra else 1.8)
    mt, mr = fs * 1.8, fs * 1.8
    W, H = ml + fw + mr, mt + fh + mb

    def to_paper(world: dict) -> tuple[float, float]:
        x = world[ra]
        x = fw - x if rrev else x
        y = world[ua]
        y = fh - y if urev else y
        return ml + x, mt + fh - y

    def pt(a: float, b: float) -> tuple[float, float]:  # values on kept[0], kept[1]
        return to_paper({kept[0]: a, kept[1]: b})

    def st(s: float, t: float) -> tuple[float, float]:
        return to_paper({s_axis: s, (kept[1] if kept[0] == s_axis else kept[0]): t})

    loops = []
    for c in find_contours(sil, 0.0):
        if len(c) < 8:
            continue
        world = [grid.origin[kept[k]] + grid.h * c[:, k] for k in range(2)]
        loops.append([pt(a, b) for a, b in zip(*world)])
    outline = " ".join("M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in loop) + " Z" for loop in loops)
    rect = f"M{ml:.2f},{mt:.2f} h{fw:.2f} v{fh:.2f} h{-fw:.2f} Z"

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.2f} {H:.2f}" class="marks-svg" '
        f'style="--fs:{fs:.2f}px">',
        f'<defs><pattern id="hatch-{view.key}" width="{fs * 0.7:.2f}" height="{fs * 0.7:.2f}" '
        f'patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
        f'<line x1="0" y1="0" x2="0" y2="{fs * 0.7:.2f}" class="hatch-line" stroke-width="{sw:.2f}"/></pattern></defs>',
        f'<path d="{rect}" class="face"/>',
        f'<path d="{rect} {outline}" fill="url(#hatch-{view.key})" fill-rule="evenodd"/>',
    ]
    t_len = blank[kept[1] if kept[0] == s_axis else kept[0]]
    for i, (s, runs) in enumerate(stations):
        (x1, y1), (x2, y2) = st(s, 0.0), st(s, t_len)
        parts.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" class="station" '
                     f'data-row="{i}" stroke-width="{sw:.2f}"/>')
    if symmetric:
        c = blank[1] / 2
        if ra == 1:
            x, _ = to_paper({1: c, ua: 0})
            parts.append(f'<line x1="{x:.2f}" y1="{mt - fs * 0.4:.2f}" x2="{x:.2f}" y2="{mt + fh + fs * 0.4:.2f}" '
                         f'class="center" stroke-width="{sw:.2f}"/>')
    parts.append(f'<path d="{outline}" class="outline" stroke-width="{sw * 2.4:.2f}"/>')
    parts.append(f'<path d="{rect}" class="edge-line" stroke-width="{sw * 1.6:.2f}"/>')
    for i, (s, runs) in enumerate(stations):
        for a, b in runs:
            for tv in (a, b):
                x, y = st(s, tv)
                parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{fs * 0.2:.2f}" class="dot" data-row="{i}"/>')
    for label, s, tv in tips:
        x, y = st(s, tv)
        parts.append(f'<g class="tip" data-tip="{label}"><circle cx="{x:.2f}" cy="{y:.2f}" r="{fs * 0.3:.2f}"/>'
                     f'<text x="{x + fs * 0.45:.2f}" y="{y - fs * 0.35:.2f}" font-size="{fs * 0.85:.2f}">{label}</text></g>')

    # station labels along the ruler edge, thinned out if they'd crowd
    ruler = Ruler(s_axis, blank, symmetric)
    labelled = [(i, s, "0" if ruler(s) < 1 else inches(ruler(s))) for i, (s, _) in enumerate(stations)]
    gap = min((abs(a[1] - b[1]) for a, b in zip(labelled, labelled[1:])), default=fs * 9)
    rfs = fs * 0.75
    need = rfs * 1.25 if s_axis == ua else max((len(t) for *_, t in labelled), default=1) * rfs * 0.56 + rfs * 0.6
    every = max(1, int(np.ceil(need / gap)))
    for n, (i, s, text) in enumerate(labelled):
        if n % every:
            continue
        if s_axis == ua:
            _, y = to_paper({ua: s, ra: 0})
            parts.append(f'<text x="{ml - fs * 0.35:.2f}" y="{y + fs * 0.3:.2f}" class="ruler" text-anchor="end" '
                         f'font-size="{fs * 0.75:.2f}" data-row="{i}">{text}</text>')
        else:
            x, _ = to_paper({ra: s, ua: 0})
            parts.append(f'<text x="{x:.2f}" y="{mt + fh + fs * 1.0:.2f}" class="ruler" text-anchor="middle" '
                         f'font-size="{fs * 0.75:.2f}" data-row="{i}">{text}</text>')

    edge_fs = fs * 0.7
    for where, name in view.edges:
        if where == "top":
            parts.append(f'<text x="{ml + fw / 2:.2f}" y="{mt - fs * 0.5:.2f}" class="edge" text-anchor="middle" '
                         f'font-size="{edge_fs:.2f}">{name}</text>')
        elif where == "bottom":
            y = H - fs * 0.35
            parts.append(f'<text x="{ml + fw / 2:.2f}" y="{y:.2f}" class="edge" text-anchor="middle" '
                         f'font-size="{edge_fs:.2f}">{name}</text>')
        else:
            x = ml + fw + fs * 0.75 if where == "right" else fs * 0.75
            if where == "left" and s_axis == ua:
                x = ml - fs * 2.9
            rot = 90 if where == "right" else -90
            parts.append(f'<text x="{x:.2f}" y="{mt + fh / 2:.2f}" class="edge" text-anchor="middle" '
                         f'font-size="{edge_fs:.2f}" transform="rotate({rot} {x:.2f} {mt + fh / 2:.2f})">{name}</text>')
    parts.append("</svg>")
    return "".join(parts)


# ---------------------------------------------------------------- the block itself


def station_lines(blank: np.ndarray, axis: int, step: float, inset: float = 0.15) -> list:
    """Pencil lines all the way around the block at every station along `axis`,
    as 3D segments, drawn just outside the faces."""
    others = [a for a in range(3) if a != axis]
    ruler = Ruler(axis, blank, symmetric=False)
    segs = []
    for k in range(1, int((blank[axis] - step / 3) / step) + 1):
        v = ruler.world(k * step)
        lo = [-inset, -inset]
        hi = [blank[others[0]] + inset, blank[others[1]] + inset]
        corners = [(lo[0], lo[1]), (hi[0], lo[1]), (hi[0], hi[1]), (lo[0], hi[1])]
        for (a0, b0), (a1, b1) in zip(corners, corners[1:] + corners[:1]):
            p, q = np.zeros(3), np.zeros(3)
            p[axis] = q[axis] = v
            p[others[0]], p[others[1]] = a0, b0
            q[others[0]], q[others[1]] = a1, b1
            segs.append((p, q))
    return segs


def centerline(blank: np.ndarray, origin_xy, yaw: float, inset: float = 0.15):
    """The figure's centerline: on the top, and down the front and back when the
    figure sits square. Returns (segments, words)."""
    L, W, H = blank
    if yaw == 0:
        c = origin_xy[1]
        segs = [
            (np.array([0, c, H + inset]), np.array([L, c, H + inset])),
            (np.array([L + inset, c, 0]), np.array([L + inset, c, H])),
            (np.array([-inset, c, 0]), np.array([-inset, c, H])),
        ]
        words = (f"Draw a centerline down the middle of the top, the front and the back: "
                 f"{inches(c)} in from each side.")
        if abs(c - W / 2) > 0.8:
            words = (f"Draw the figure's centerline along the top, the front and the back, "
                     f"{inches(c)} in from the RIGHT side (the figure isn't centered).")
        return segs, words
    # turned: one line across the top, along the figure's own center
    d = np.array([np.cos(np.radians(yaw)), np.sin(np.radians(yaw))])
    o = np.asarray(origin_xy, dtype=float)
    hits = []
    for axis, value in ((0, 0.0), (0, L), (1, 0.0), (1, W)):
        if abs(d[axis]) < 1e-9:
            continue
        tt = (value - o[axis]) / d[axis]
        p = o + tt * d
        if -1e-6 <= p[0] <= L + 1e-6 and -1e-6 <= p[1] <= W + 1e-6:
            hits.append((tt, p))
    hits.sort(key=lambda h: h[0])
    (_, p0), (_, p1) = hits[0], hits[-1]

    def where(p):
        if abs(p[0] - L) < 0.5:
            return f"{inches(p[1])} in from the RIGHT side on the front edge"
        if abs(p[0]) < 0.5:
            return f"{inches(p[1])} in from the RIGHT side on the back edge"
        side = "RIGHT" if abs(p[1]) < 0.5 else "LEFT"
        return f"{inches(L - p[0])} in from the front on the {side} edge"

    segs = [(np.array([p0[0], p0[1], H + inset]), np.array([p1[0], p1[1], H + inset]))]
    words = f"Draw the figure's centerline across the top, at an angle: from {where(p1)} to {where(p0)}."
    return segs, words
