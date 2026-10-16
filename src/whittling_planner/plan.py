"""Build a staged carving plan: blank → profile cuts (biggest first) → rounded
corners → details → finishing touches."""

import base64
from dataclasses import dataclass, field
from functools import lru_cache

import numpy as np
from scipy.ndimage import binary_dilation
from skimage.measure import marching_cubes

from whittling_planner import grain as grain_check
from whittling_planner.designs import DESIGNS, shape
from whittling_planner.geometry import Grid, box_field, diagonal_extrusion, extrude, make_grid, sample, silhouette
from whittling_planner.marks import FaceMarks, centerline, face_marks, spacing, station_axis, station_lines
from whittling_planner.placement import Fit, describe, fit_design, turn_words
from whittling_planner.units import dims_in, dims_mm, inches

DEFAULT_DETAIL = 100  # about this many grid cells along each side of a cube with the blank's volume
PROFILE_MIN = 0.02  # skip a profile cut that removes less than this share of the blank
SIDE_FIRST = 1.25  # the side profile goes first unless another removes this much more wood

PROFILES = {
    1: ("side", "Cut the side profile",
        "Remove everything outside the side outline, straight through from side to side.",
        "Carve away the hatched waste, cutting straight across from the RIGHT side to the LEFT. Keep the cut "
        "walls square to the faces so the outlines on the two sides stay lined up."),
    0: ("front", "Cut the front profile",
        "Remove everything outside the front outline, straight through from front to back.",
        "Carve away the hatched waste, cutting straight through from the FRONT to the BACK."),
    2: ("top", "Cut the top outline",
        "Remove everything outside the outline seen from above, straight down to the base.",
        "Carve away the waste, cutting straight down from the top toward the base."),
}


@dataclass
class Stage:
    key: str
    title: str
    summary: str
    steps: list[str]
    field: np.ndarray
    marks: list[FaceMarks] = field(default_factory=list)
    lines: list = field(default_factory=list)  # pencil lines to draw on the block, as 3D segments
    spots: list = field(default_factory=list)  # points to mark for the finishing touches, world mm
    same_as: int | None = None  # the shape doesn't change in this stage


@dataclass
class Plan:
    fit: Fit
    grid: Grid
    stages: list[Stage]
    grain: dict
    block_mm: tuple


def _on_surface(fit: Fit, p: np.ndarray) -> np.ndarray:
    """Pull points onto the figure's surface (a few Newton steps)."""
    for _ in range(4):
        f = fit.target(p[:, 0], p[:, 1], p[:, 2])
        e = 0.05
        g = np.stack([(fit.target(*(p + d).T) - fit.target(*(p - d).T)) / (2 * e) for d in np.eye(3) * e], axis=1)
        p = p - (f / np.maximum((g**2).sum(axis=1), 1e-6))[:, None] * g
    return p


def _spot_steps(fit: Fit) -> tuple[list[str], list]:
    steps, points = [], []
    for name, q in DESIGNS[fit.key].spots:
        q = np.array(q, dtype=float)
        if q[1] > 0:
            p = _on_surface(fit, fit.to_world([q, q * [1, -1, 1]]))
            apart = float(np.linalg.norm(p[0] - p[1]))
            height = float(p[:, 2].mean())
            steps.append(f"Mark the {name}: {inches(height)} in up from the base, {inches(apart)} in apart.")
        else:
            p = _on_surface(fit, fit.to_world([q]))
            steps.append(f"Mark the {name}: {inches(float(p[0, 2]))} in up from the base, on the centerline.")
        points.extend(p.tolist())
    return steps, points


def compute(key: str, block_mm, detail: int = DEFAULT_DETAIL, grain: str | None = None, angled: bool = True) -> Plan:
    design = DESIGNS[key]
    fit = fit_design(key, block_mm, angled)
    grid = make_grid(fit.blank, detail)
    blank = box_field(grid, fit.blank).astype(np.float32)
    # the base lies on the blank's bottom face; clip so rounding error can't put it outside
    target = np.maximum(fit.target(*grid.broadcast_axes()).astype(np.float32), blank)

    sil = {axis: silhouette(target, axis) for axis in range(3)}
    alone = {axis: np.maximum(blank, extrude(sil[axis], axis, grid.shape)) for axis in range(3)}
    cells = (blank < 0).sum()
    # cut the outline that removes the most wood first, favoring the side profile, which is the
    # easiest to read and to cut; skip one that would barely remove anything
    order = sorted(range(3), key=lambda a: -(cells - (alone[a] < 0).sum()) * (SIDE_FIRST if a == 1 else 1.0))
    profiles, current = [], blank
    for axis in order:
        after = np.maximum(current, alone[axis])
        if profiles and ((current < 0).sum() - (after < 0).sum()) / cells < PROFILE_MIN:
            continue
        profiles.append((axis, after))
        current = after
    rounded = current
    for a, b in ((0, 1), (0, 2), (1, 2)):
        for flip in (False, True):
            rounded = np.maximum(rounded, diagonal_extrusion(target, a, b, flip))

    checked = grain_check.analyse(target < 0, grid.h, fit.blank)
    # the block's grain runs along its longest side; if that's more than one way, take the safest
    vols = checked["volumes"]
    best = min(vols[a] for a in fit.grain_axes)
    near = [a for a in fit.grain_axes if vols[a] <= best * 1.1 + 5.0]
    selected = grain or (checked["recommended"] if checked["recommended"] in near else near[0])
    words = grain_check.AXIS_WORDS[selected]

    # step 1: set the block down and mark it out
    lines_axis = station_axis([0, 1, 2], fit.blank)
    step = spacing(fit.blank[lines_axis])
    n_lines = int((fit.blank[lines_axis] - step / 3) / step)
    where_lines = "up from the bottom" if lines_axis == 2 else "back from the front" if lines_axis == 0 else "from the RIGHT side"
    shown = ", ".join(inches(k * step) for k in range(1, min(n_lines, 4) + 1)) + (", …" if n_lines > 4 else "")
    center_segs, center_words = centerline(fit.blank, fit.to_world([[0, 0, 0]])[0][:2], fit.yaw)
    blank_steps = [
        f"{describe(fit)} The grain should run {words}.",
        "Label the faces with a pencil: FRONT (where the figure faces), BACK, LEFT, RIGHT and TOP. "
        "The bottom becomes the base, so keep it flat.",
    ]
    if fit.yaw:
        blank_steps.append(turn_words(fit))
    blank_steps += [
        center_words,
        f"Measure {where_lines} and draw a line all the way around the block every {inches(step)} in "
        f"({shown} in). Use a square so the lines meet at the corners. Each outline is measured along these lines.",
    ]
    stages = [
        Stage(
            "blank", "Prepare the block",
            f"A {dims_in(sorted(block_mm, reverse=True))} block of basswood, marked out with a pencil, ruler and square.",
            blank_steps, blank,
            lines=station_lines(fit.blank, lines_axis, step) + center_segs,
        )
    ]

    for i, (axis, f) in enumerate(profiles):
        key_, title, summary, cut = PROFILES[axis]
        marks = face_marks(sil[axis], grid, fit.blank, axis)
        steps = [
            f"{marks.where} On each station line, put a dot at each measurement in the table, "
            "mark the lettered points, then join them following the drawing.",
        ]
        if i:
            steps.append("Where earlier cuts took away the station lines, redraw them first, measuring the same way.")
        steps += [
            cut,
            "At inside corners, make a stop cut straight in on the line first, then slice toward it, "
            "so the waste pops out without splitting past the line.",
        ]
        stages.append(Stage(key_, title, summary, steps, f, marks=[marks]))

    rustic = design.style == "Rustic"
    stages += [
        Stage(
            "round", "Round off the corners" if not rustic else "Take off the corners",
            "Take down the square edges left by the profile cuts.",
            [
                "The profile cuts leave square edges everywhere. Take them down until the piece matches the "
                "model: this is the shape the figure has when seen from every 45° angle.",
                "Work in thin slices and keep turning the piece to compare it with the model. The color shows "
                "how much to remove: yellow is a shaving, red is the deepest cut in this step.",
                "Cut downhill with the grain: on each curve, slice from the high point toward the low point, "
                "so the knife doesn't dig in and split the wood.",
            ] + (["Make each cut one flat plane. On a rustic carving the corners become facets, not curves."] if rustic else []),
            rounded,
        ),
        Stage(
            "detail", "Carve the details",
            "Carve what no outline can show.",
            [
                f"Carve the parts that no outline can show: {design.details}.",
                "Go slowly here. These are small cuts in tight spots, so use the tip of the knife "
                "and take off very little at a time.",
                "Keep every cut flat and crisp." if rustic else "Blend the surfaces with light, smoothing cuts.",
            ],
            target,
        ),
    ]
    spot_steps, spots = _spot_steps(fit)
    finish = "Finish: oil or wax only. It darkens the facets a little, so the knife cuts show." if rustic else (
        "Finish: rub on boiled linseed oil, Danish oil or beeswax, wipe off the extra, and let it dry overnight. "
        "If you paint, use thinned acrylics first, then oil or wax over them.")
    stages.append(Stage(
        "finish", "Finishing touches",
        "Clean up, mark the features, add texture, then a finish.",
        ["Clean up: shave off fuzzy fibers and torn grain with light slicing cuts, especially in the hollows."]
        + spot_steps + list(design.touches)
        + ["Sign and date the base.", finish],
        target, spots=spots, same_as=len(stages) - 1,
    ))
    return Plan(fit, grid, stages, {**checked, "selected": selected}, tuple(block_mm))


def _b64(a: np.ndarray) -> str:
    return base64.b64encode(np.ascontiguousarray(a).tobytes()).decode("ascii")


def _mesh(f: np.ndarray, grid: Grid) -> tuple[np.ndarray, np.ndarray]:
    verts, faces, _, _ = marching_cubes(f, 0.0, spacing=(grid.h,) * 3)
    return (verts + grid.origin).astype(np.float32), faces.astype(np.uint32)


def to_json(plan: Plan) -> dict:
    """Everything the web viewer needs. Meshes and per-vertex values are
    base64-encoded little-endian float32 / uint32 arrays."""
    fit, grid = plan.fit, plan.grid
    blank_volume = float((plan.stages[0].field < 0).sum()) * grid.h**3
    meshes = [None if s.same_as is not None else _mesh(s.field, grid) for s in plan.stages]

    stages = []
    prev = None
    for i, s in enumerate(plan.stages):
        out = {"key": s.key, "title": s.title, "summary": s.summary, "steps": s.steps,
               "marks": [m.as_json() for m in s.marks]}
        if s.lines:
            out["lines"] = _b64(np.array(s.lines, dtype=np.float32).reshape(-1))
        if s.spots:
            out["spots"] = s.spots
        if s.same_as is not None:
            out["same_as"] = s.same_as
            stages.append(out)
            continue
        verts, faces = meshes[i]
        out["mesh"] = {"positions": _b64(verts), "indices": _b64(faces)}
        if prev is not None:
            # how much wood to take off, at each point of the previous shape
            heat = np.maximum(sample(s.field, grid, meshes[prev][0]), 0.0).astype(np.float32)
            removed = float(((plan.stages[prev].field < 0) & (s.field >= 0)).sum()) * grid.h**3
            out |= {
                "heat": _b64(heat),
                "heat_max": float(np.percentile(heat, 99.5)) if heat.size else 0.0,
                "removed_cm3": removed / 1000,
                "removed_pct": 100 * removed / blank_volume,
            }
        prev = i
        stages.append(out)

    final_verts = meshes[[i for i, m in enumerate(meshes) if m is not None][-1]][0]
    fragile = {
        axis: _b64(np.clip(sample(binary_dilation(mask).astype(np.float32), grid, final_verts) * 2, 0, 1).astype(np.float32))
        for axis, mask in plan.grain["masks"].items()
    }
    design = DESIGNS[fit.key]
    angled = fit_design(fit.key, plan.block_mm, angled=True)
    figure_volume = shape(fit.key).volume * fit.scale**3
    return {
        "design": {"key": design.key, "name": design.name, "subject": design.subject, "style": design.style,
                   "level": design.level},
        "block_label": dims_in(sorted(plan.block_mm, reverse=True)),
        "blank_mm": fit.blank.tolist(),
        "blank_label": dims_in(fit.blank),
        "blank_label_mm": dims_mm(fit.blank),
        "figure_mm": fit.figure.tolist(),
        "figure_label": dims_in(fit.figure),
        "placement": {
            "set_down": describe(fit),
            "yaw": fit.yaw,
            "turn": turn_words(fit),
            "fill_pct": 100 * figure_volume / float(np.prod(fit.blank)),
            # turning the figure in the block would make it this much bigger
            "angle_gain_pct": 100 * (angled.scale / angled.straight_scale - 1) if angled.yaw else 0.0,
            "angle_yaw": angled.yaw,
        },
        "cell_mm": grid.h,
        "grain": {
            "selected": plan.grain["selected"],
            "recommended": plan.grain["recommended"],
            "block_axes": fit.grain_axes,
            "fragile_mm3": plan.grain["volumes"],
            "weak_parts": plan.grain["parts"],
            "words": grain_check.AXIS_WORDS,
            "fragile": fragile,
        },
        "stages": stages,
    }


@lru_cache(maxsize=16)
def plan_json(key: str, block_mm: tuple, detail: int, grain: str | None, angled: bool) -> dict:
    return to_json(compute(key, block_mm, detail, grain, angled))
