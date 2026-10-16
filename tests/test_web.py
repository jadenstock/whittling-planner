from fastapi.testclient import TestClient

from whittling_planner.designs import DESIGNS
from whittling_planner.web.app import app

client = TestClient(app)


def test_pages_serve():
    assert "Whittling Planner" in client.get("/").text
    assert "Explore" in client.get("/explore").text


def test_designs_list_how_each_fits_every_block():
    data = client.get("/api/designs").json()
    assert set(data["blocks"]) == {"2x1x1", "4x1x1", "4x2x2", "2x2x1"}
    assert len(data["designs"]) == len(DESIGNS)
    for d in data["designs"]:
        assert set(d["fits"]) == set(data["blocks"])
        assert any(f["made_for"] for f in d["fits"].values())


def test_preview_mesh():
    data = client.get("/api/preview/owl").json()
    assert data["positions"] and data["indices"]
    assert client.get("/api/preview/bat").status_code == 404


def test_plan_endpoint():
    data = client.get("/api/plan", params={"design": "cat-sitting", "block": "4x2x2", "detail": 40}).json()
    assert data["design"]["key"] == "cat-sitting"
    assert 0.95 * 4 * 25.4 < max(data["figure_mm"]) <= 4 * 25.4 - 1 + 0.05  # nearly fills the 4 in height
    custom = client.get("/api/plan", params={"design": "gnome", "blank_in": "1,1,3", "detail": 40}).json()
    assert custom["block_label"] == "3 × 1 × 1 in"
    assert client.get("/api/plan", params={"design": "bat"}).status_code == 404
    assert client.get("/api/plan", params={"design": "owl", "block": "9x9x9"}).status_code == 422
    assert client.get("/api/plan", params={"design": "owl", "blank_in": "1,1"}).status_code == 422
