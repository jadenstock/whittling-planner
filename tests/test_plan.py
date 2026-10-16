import numpy as np
import pytest

from whittling_planner.designs import BLOCKS, DESIGNS, shape
from whittling_planner.geometry import box_field, diagonal_extrusion, make_grid, silhouette
from whittling_planner.marks import _runs, face_marks
from whittling_planner.placement import MARGIN_MM, fit_design
from whittling_planner.plan import compute, to_json
from whittling_planner.units import inches

DETAIL = 45  # coarse grid: fast, and enough to check the structure
IN = 25.4


def block_mm(name: str) -> tuple:
    return tuple(v * IN for v in BLOCKS[name])


@pytest.fixture(scope="module", params=list(DESIGNS))
def plan(request):
    d = DESIGNS[request.param]
    return compute(d.key, block_mm(d.blocks[0]), detail=DETAIL)


def test_each_stage_only_removes_wood(plan):
    inside = [s.field < 0 for s in plan.stages]
    for before, after in zip(inside, inside[1:]):
        assert not (after & ~before).any()


def test_every_stage_still_contains_the_figure(plan):
    figure = plan.stages[-1].field < 0
    for s in plan.stages:
        assert not (figure & ~(s.field < 0)).any(), s.key


def test_stages_run_from_the_block_to_the_finishing_touches(plan):
    keys = [s.key for s in plan.stages]
    assert keys[0] == "blank"
    assert keys[-3:] == ["round", "detail", "finish"]
    assert 1 <= len(keys) - 4 <= 3  # one to three profile cuts
    assert all(s.marks for s in plan.stages[1:-3])  # each profile cut says how to mark it out


@pytest.mark.parametrize("key", list(DESIGNS))
def test_figure_fits_every_block_standing_on_its_base(key):
    pts = shape(key).points
    for name in BLOCKS:
        fit = fit_design(key, block_mm(name))
        world = fit.to_world(pts)
        assert (world[:, :2] >= MARGIN_MM - 0.05).all() and (world[:, :2] <= fit.blank[:2] - MARGIN_MM + 0.05).all()
        assert world[:, 2].min() == pytest.approx(0, abs=0.05)  # the base on the block's bottom face
        assert world[:, 2].max() <= fit.blank[2] - MARGIN_MM + 0.05


@pytest.mark.parametrize("key", list(DESIGNS))
def test_designs_fill_the_blocks_they_were_made_for(key):
    """Tailored to the block: the figure comes close to the wood on every side."""
    pts = shape(key).points
    for name in DESIGNS[key].blocks:
        fit = fit_design(key, block_mm(name))
        assert fit.grain_ok, name  # the block's grain runs a way the design can take
        room = fit.blank - np.array([2, 2, 1]) * MARGIN_MM
        fill = np.ptp(fit.to_world(pts), axis=0) / room
        assert fill.max() == pytest.approx(1, abs=0.01)
        assert fill.min() > 0.7, (name, fill)


def test_turning_a_long_figure_in_a_square_block_makes_it_bigger():
    turned = fit_design("dachshund", block_mm("2x2x1"))
    assert turned.yaw != 0
    assert turned.scale > turned.straight_scale * 1.08
    assert fit_design("dachshund", block_mm("2x2x1"), angled=False).yaw == 0
    # a design in the block it was made for sits square on
    assert fit_design("dachshund", block_mm("4x1x1")).yaw == 0


def test_block_is_set_down_the_way_the_design_needs():
    assert list(fit_design("gnome", block_mm("4x1x1")).blank) == pytest.approx([IN, IN, 4 * IN])  # on end
    assert list(fit_design("cat-loaf", block_mm("2x1x1")).blank) == pytest.approx([2 * IN, IN, IN])  # on its side
    assert fit_design("duck-sitting", block_mm("2x2x1")).blank[2] == pytest.approx(2 * IN)  # on edge


def test_beginner_designs_have_no_weak_spots_with_the_blocks_grain():
    for d in DESIGNS.values():
        if d.level != "Beginner":
            continue
        for name in d.blocks:
            p = compute(d.key, block_mm(name), detail=80)
            assert p.grain["parts"][p.grain["selected"]] == 0, (d.key, name)


def test_grain_runs_the_way_carvers_would_choose():
    # the duck's bill sticks out forward, so its grain should run front to back;
    # upright figures want the grain running up and down
    assert compute("duck-sitting", block_mm("2x2x1"), detail=70).grain["selected"] == "x"
    assert compute("cat-sitting", block_mm("4x2x2"), detail=70).grain["selected"] == "z"


def test_diagonal_extrusion_matches_a_brute_force_projection():
    rng = np.random.default_rng(0)
    field = rng.normal(size=(5, 4, 3))
    out = diagonal_extrusion(field, 0, 1, flip=False)
    for i in range(5):
        for j in range(4):
            line = [field[a, a - i + j] for a in range(5) if 0 <= a - i + j < 4]
            assert np.allclose(out[i, j], np.min(line, axis=0))


def test_runs_find_where_the_wood_is():
    t = np.linspace(0, 10, 11)
    values = np.array([1, 1, -1, -1, -1, 1, 1, -1, -1, 1, 1], dtype=float)
    assert _runs(values, t) == [pytest.approx((1.5, 4.5)), pytest.approx((6.5, 8.5))]


def test_marks_measure_a_disc():
    """A ball seen from the front is a disc: each station reads 'out to' its half-width."""
    blank = np.array([40.0, 40.0, 40.0])
    grid = make_grid(blank, 80)
    x, y, z = grid.broadcast_axes()
    ball = np.sqrt((x - 20) ** 2 + (y - 20) ** 2 + (z - 20) ** 2) - 10
    field = np.maximum(ball, box_field(grid, blank))
    marks = face_marks(silhouette(field, 0), grid, blank, 0)
    assert marks.station_head == "Up from the bottom"
    rows = {r["at"]: r["marks"] for r in marks.rows}
    assert rows["3/4"] == f"out to {inches(np.sqrt(100 - (19.05 - 20) ** 2))}"
    assert rows["1/2"] == f"out to {inches(np.sqrt(100 - (12.7 - 20) ** 2))}"
    assert any(t["text"] == f"{inches(30)} in up, on the centerline" for t in marks.tips)  # top of the disc


def test_json_has_meshes_heat_marks_and_finishing():
    data = to_json(compute("duck-decoy", block_mm("2x1x1"), detail=DETAIL))
    stages = data["stages"]
    assert stages[0]["key"] == "blank" and "lines" in stages[0]
    assert all("heat" in s for s in stages[1:-1])
    assert stages[1]["marks"] and "<svg" in stages[1]["marks"][0]["svg"]
    finish = stages[-1]
    assert finish["key"] == "finish" and finish["same_as"] == len(stages) - 2 and "mesh" not in finish
    assert len(finish["spots"]) == 2  # the eyes
    assert any(step.startswith("Mark the eyes") for step in finish["steps"])
    assert data["placement"]["set_down"].startswith("Lay the block")


def test_inches_are_written_in_sixteenths():
    assert inches(25.4) == "1"
    assert inches(25.4 * 2.1875) == "2 3/16"
    assert inches(25.4 * 0.5) == "1/2"
