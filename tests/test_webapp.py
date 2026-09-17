from fastapi.testclient import TestClient

from app.main import ROOT, app


client = TestClient(app)


def test_multipage_webapp_routes_are_served():
    expected_titles = {
        "/": "Spatial intelligence",
        "/reconstruct": "Reconstruct",
        "/jobs": "Jobs",
        "/outputs": "Deliverables",
        "/system": "System",
        "/studio": "Studio · AeroSynth",
    }
    for path, title in expected_titles.items():
        response = client.get(path)
        assert response.status_code == 200
        assert title in response.text


def test_jobs_endpoint_returns_only_public_summaries():
    response = client.get("/api/v1/jobs")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == len(payload["jobs"])
    for job in payload["jobs"]:
        assert "file_path" not in job
        assert "output_dir" not in job


def test_shared_frontend_assets_are_available():
    assert client.get("/frontend/app.css").status_code == 200
    assert client.get("/frontend/app.js").status_code == 200
    assert client.get("/frontend/reconstruct.js").status_code == 200
    assert client.get("/frontend/studio.js").status_code == 200


def test_every_project_wallpaper_has_full_and_thumbnail_assets():
    for wallpaper_id in (1, 2, 3, 5, 6, 7, 8):
        asset_dir = ROOT / "frontend" / "assets" / "wallpapers"
        assert (asset_dir / f"wallpaper-{wallpaper_id}.webp").stat().st_size > 0
        assert (asset_dir / f"wallpaper-{wallpaper_id}-thumb.webp").stat().st_size > 0

    response = client.get("/frontend/assets/wallpapers/wallpaper-1-thumb.webp")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/webp"
