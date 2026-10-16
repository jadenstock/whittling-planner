import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from whittling_planner.designs import BLOCKS, DESIGNS
from whittling_planner.learn import CUTS, HOW_HARD, PATH, PROFILE_CUTS, ROUND_CUTS, TERMS, cuts_in, design_cuts, learn_json
from whittling_planner.plan import compute, to_json
from whittling_planner.web.app import app

STATIC = Path(__file__).parents[1] / "src/whittling_planner/web/static"


def test_every_cut_is_described_and_drawn():
    sketches = (STATIC / "learn.js").read_text()
    for c in CUTS.values():
        assert c.level in HOW_HARD and c.good_for and c.how and c.watch, c.key
        assert f"  {c.key}: () =>" in sketches, f"no diagram for {c.key}"


def test_designs_only_call_for_known_cuts_and_every_cut_gets_used():
    used = {k for k, _ in PROFILE_CUTS + ROUND_CUTS}
    for d in DESIGNS.values():
        assert d.cuts, d.key
        for key, where in design_cuts(d):
            assert key in CUTS and where, (d.key, key)
            used.add(key)
    assert used == set(CUTS)


def test_finishing_touches_name_their_cuts():
    assert cuts_in(["Wings: a V-cut along each side marks the folded wing."]) == [("vcut", "wings")]
    assert cuts_in(["Eyes: two small triangle chips."]) == [("chip", "eyes")]
    assert ("stop", "gaps, when finishing") in [(k, w.split("; ")[-1]) for k, w in design_cuts(DESIGNS["ducks-row"])]


def test_terms_are_plain_patterns_the_browser_can_use():
    # the planner joins them into one regex and finds which alternative matched by group number
    for pattern, anchor in TERMS:
        assert re.compile(pattern).groups == 0, pattern
        assert anchor in CUTS or anchor == "grain"


def test_practice_path_introduces_the_cuts_in_order():
    data = learn_json()
    assert [p["key"] for p in data["path"]] == [k for k, _ in PATH]
    assert all(c["new"] for c in data["path"][0]["cuts"])
    seen = set()
    for p in data["path"]:
        for c in p["cuts"]:
            assert c["new"] == (c["key"] not in seen)
        seen.update(c["key"] for c in p["cuts"])


def test_plan_stages_say_which_cuts_to_use():
    block = tuple(v * 25.4 for v in BLOCKS["2x1x1"])
    stages = {s["key"]: s for s in to_json(compute("duck-decoy", block, detail=40))["stages"]}
    assert stages["blank"]["cuts"] == []
    assert {"straightaway", "stop"} <= {c["key"] for c in stages["side"]["cuts"]}
    assert [c["key"] for c in stages["detail"]["cuts"]] == [k for k, _ in DESIGNS["duck-decoy"].cuts]
    assert {c["key"] for c in stages["finish"]["cuts"]} == {"chip", "vcut"}  # eyes and wings
    rustic = {s["key"]: s for s in to_json(compute("duck-rustic", block, detail=40))["stages"]}
    assert rustic["round"]["cuts"][0]["key"] == "facet"


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_learn_page_and_data(client):
    assert "Which cut for what" in client.get("/learn").text
    data = client.get("/api/learn").json()
    assert [c["key"] for c in data["cuts"]] == list(CUTS)
    stop = next(c for c in data["cuts"] if c["key"] == "stop")
    assert len(stop["designs"]) == len(DESIGNS)  # every design needs a stop cut somewhere
    assert stop["designs"][0]["level"] == "Beginner"  # easiest designs first
    owl = next(d for d in client.get("/api/designs").json()["designs"] if d["key"] == "owl")
    assert owl["cuts"][0]["key"] == "scoop"
