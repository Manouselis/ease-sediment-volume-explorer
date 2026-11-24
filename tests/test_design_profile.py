import csv
import io
import json
import zipfile

import numpy as np
import pytest
from fastapi.testclient import TestClient

from ease_volume import server


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "RUNS", tmp_path)
    return TestClient(server.app)


def request(client, points, **profile):
    lines = ["x,y,z", *(",".join(str(value) for value in row) for row in points)]
    method = profile.pop("method", "tin")
    config = {
        "reference_mode": "profile", "reference_note": "Synthetic L8 design",
        "surface_method": method, "filter_mode": "off", "cell_size": 0.25,
        "kriging_fit": "manual",
        "design_profile": {"code": "L8", "water_level_m_nap": -5.7,
                           "survey_nap_confirmed": True, **profile},
    }
    return client.post("/api/analyze", data={"config": json.dumps(config)},
                       files={"survey": ("survey.csv", "\n".join(lines), "text/csv")})


def test_collinear_track_returns_comparison_without_volume(client):
    response = request(client, [(177000 + i, 500000, -6.5) for i in range(11)])
    assert response.status_code == 200, response.text
    result = response.json()
    assert "summary" not in result
    assert result["profile"]["metadata"]["provisional"]
    assert result["profile"]["metadata"]["compared_count"] == 11
    assert "geotiff" not in result["exports"]
    assert result["profile"]["points"]["design"] == pytest.approx([-6.9] * 11)
    archive = zipfile.ZipFile(io.BytesIO(client.get(result["exports"]["bundle"]).content))
    assert set(archive.namelist()) == {"comparison.csv", "reference_xyz.csv", "summary.json"}


@pytest.mark.parametrize("method", ["tin", "kriging"])
def test_area_calculation_evaluates_l8_slopes_directly(client, method):
    points = [(177000 + x, 500000 + y, -6.0 + .01*x)
              for x in range(11) for y in range(-4, 5)]
    response = request(client, points, method=method, coverage="area",
                       endpoints=[177000, 500000, 177010, 500000], water_level_confirmed=True)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["provenance"]["surface_generation"]["reference"]["method"] == "design_profile"
    assert not result["profile"]["metadata"]["provisional"]
    assert result["summary"]["requested_area_m2"] == pytest.approx(101)
    assert result["summary"]["valid_area_m2"] == pytest.approx(80)
    assert result["bed_mesh"]
    rows = list(csv.DictReader(io.StringIO(client.get(result["exports"]["cells"]).text)))
    valid = [row for row in rows if row["valid"] == "1"]
    offset = np.abs(np.array([float(row["sample_y"]) for row in valid]) - 500000)
    exact_design = -6.9 + np.maximum(0, offset - 2.65) / 2
    np.testing.assert_allclose([float(row["reference_elevation_m"]) for row in valid], exact_design, atol=1e-6)
    assert all(row["reference_kriging_variance_m2"] == "" for row in valid)
    if method == "tin":
        assert result["summary"]["positive_volume_m3"] == pytest.approx(66.8875, abs=.06)


def test_profile_checks_alignment_and_height_provenance(client):
    points = [(177000 + i, 500000, -6.5) for i in range(11)]
    for settings, error in [
        ({"coverage": "area"}, "profile_endpoints"),
        ({"survey_nap_confirmed": False}, "profile_heights_required"),
        ({"endpoints": [177000, 500000, 177000, 500000]}, "profile_alignment"),
        ({"endpoints": [177000, 500100, 177010, 500100]}, "profile_overlap"),
    ]:
        response = request(client, points, **settings)
        assert response.status_code == 422
        assert response.json()["error"]["code"] == error
