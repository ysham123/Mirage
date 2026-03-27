from fastapi.testclient import TestClient

from demo_ui.server import create_demo_app


def test_demo_ui_root_serves_html(tmp_path):
    with TestClient(create_demo_app(artifact_root=tmp_path / "artifacts" / "traces")) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<title>Mirage</title>" in response.text


def test_demo_ui_safe_scenario_uses_procurement_flow(tmp_path):
    with TestClient(create_demo_app(artifact_root=tmp_path / "artifacts" / "traces")) as client:
        response = client.get("/api/scenario/safe")

    body = response.json()
    assert response.status_code == 200
    assert body["scenario"] == "safe"
    assert [step["mirage"]["outcome"] for step in body["steps"]] == ["allowed", "allowed"]
    assert body["steps"][1]["request"]["path"] == "/v1/submit_bid"
    assert body["trace"]
