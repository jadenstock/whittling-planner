"""Local web app: browse the designs, and view a carving plan stage by stage in 3D."""

import base64
import threading
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path
from typing import Literal

import numpy as np
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from skimage.measure import marching_cubes

from whittling_planner.designs import BLOCKS, DESIGNS, shape
from whittling_planner.placement import describe, fit_design
from whittling_planner.plan import DEFAULT_DETAIL, plan_json
from whittling_planner.units import dims_in

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app):
    # measure every design in the background, so the first page load is quick
    threading.Thread(target=catalog, daemon=True).start()
    yield


app = FastAPI(title="whittling-planner", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.middleware("http")
async def revalidate_static(request, call_next):
    """Make browsers re-check the pages and static files on every load, so
    edits show up without a hard refresh."""
    response = await call_next(request)
    if request.url.path in ("/", "/explore") or request.url.path.startswith("/static"):
        response.headers["Cache-Control"] = "no-cache"
    return response


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/explore")
def explore() -> FileResponse:
    return FileResponse(STATIC_DIR / "explore.html")


def _b64(a: np.ndarray) -> str:
    return base64.b64encode(np.ascontiguousarray(a).tobytes()).decode("ascii")


@lru_cache(maxsize=1)
def catalog() -> list[dict]:
    out = []
    for d in DESIGNS.values():
        fits = {}
        for name, dims in BLOCKS.items():
            fit = fit_design(d.key, tuple(v * 25.4 for v in dims))
            fits[name] = {
                "made_for": name in d.blocks,
                "figure_label": dims_in(fit.figure),
                "figure_mm": fit.figure.tolist(),
                "fill_pct": 100 * shape(d.key).volume * fit.scale**3 / float(np.prod(fit.blank)),
                "yaw": fit.yaw,
                "set_down": describe(fit),
                "blank_mm": fit.blank.tolist(),
                "scale": fit.scale,
                "offset": fit.offset.tolist(),
            }
        out.append({
            "key": d.key, "subject": d.subject, "name": d.name, "style": d.style, "level": d.level,
            "blurb": d.blurb, "blocks": list(d.blocks), "fits": fits,
        })
    return out


@app.get("/api/designs")
def designs() -> dict:
    return {"blocks": {k: list(v) for k, v in BLOCKS.items()}, "designs": catalog()}


@lru_cache(maxsize=None)
def _preview(key: str) -> dict:
    s = shape(key)
    step = float((s.hi - s.lo).max() / 48)
    lo, hi = s.lo - 2 * step, s.hi + 2 * step
    axes = [np.arange(lo[i], hi[i] + step, step) for i in range(3)]
    values = DESIGNS[key].sdf(axes[0][:, None, None], axes[1][None, :, None], axes[2][None, None, :])
    values = np.maximum(values, -axes[2][None, None, :])
    verts, faces, _, _ = marching_cubes(values, 0.0, spacing=(step,) * 3)
    verts = (verts + lo).astype(np.float32)
    return {"positions": _b64(verts), "indices": _b64(faces.astype(np.uint32)),
            "lo": s.lo.tolist(), "hi": s.hi.tolist(), "grain": DESIGNS[key].grain[0]}


@app.get("/api/preview/{key}")
def preview(key: str) -> dict:
    """A light mesh of the design on its own, in design units (inches), for the gallery."""
    if key not in DESIGNS:
        raise HTTPException(404, f"unknown design {key!r}")
    return _preview(key)


@app.get("/api/plan")
def plan(
    design: str,
    block: str | None = Query(None, description="one of the stock blocks, like '2x1x1'"),
    blank_in: str | None = Query(None, description="your own block, 'L,W,H' in inches"),
    grain: Literal["x", "y", "z"] | None = None,
    angle: Literal["auto", "straight"] = "auto",
    detail: int = Query(DEFAULT_DETAIL, ge=30, le=160),
) -> dict:
    if design not in DESIGNS:
        raise HTTPException(404, f"unknown design {design!r}")
    if blank_in:
        try:
            dims = tuple(float(v) for v in blank_in.split(","))
        except ValueError:
            raise HTTPException(422, "blank_in must be three numbers: L,W,H") from None
        if len(dims) != 3 or not all(0.5 <= v <= 24 for v in dims):
            raise HTTPException(422, "blank_in must be three sizes between 0.5 and 24 inches")
    else:
        block = block or DESIGNS[design].blocks[0]
        if block not in BLOCKS:
            raise HTTPException(422, f"unknown block {block!r}; choose one of {', '.join(BLOCKS)}")
        dims = BLOCKS[block]
    block_mm = tuple(round(v * 25.4, 3) for v in dims)
    try:
        return plan_json(design, block_mm, detail, grain, angle == "auto")
    except ValueError as e:
        raise HTTPException(422, str(e)) from None
