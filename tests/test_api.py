"""HTTP contract tests, using an analytical upload and the real RWS example."""
import io
import json
import zipfile

import pytest
import rasterio
from fastapi.testclient import TestClient

from ease_volume import server


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "RUNS", tmp_path / "runs")
    return TestClient(server.app)


def configuration(**changes):
    value = {"reference_elevation": 0, "reference_note": "Analytical 0 m test design",
             "filter_mode": "off", "max_edge": 2, "cell_size": 1}
    value.update(changes)
    return json.dumps(value)


CSV = b"x,y,z\n0,0,1\n1,0,1\n2,0,1\n0,1,1\n1,1,1\n2,1,1\n0,2,1\n1,2,1\n2,2,1\n"


def test_uploaded_survey_roundtrip_and_exports(client):
    response = client.post("/api/analyze", data={"config": configuration()},
                           files={"survey": ("../../../survey.csv", CSV, "text/csv")})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["summary"]["positive_volume_m3"] == pytest.approx(4)
    assert result["summary"]["negative_volume_m3"] == 0
    archive = client.get(result["exports"]["bundle"])
    assert archive.status_code == 200
    with zipfile.ZipFile(io.BytesIO(archive.content)) as bundle:
        assert set(bundle.namelist()) == {"summary.json", "cells.csv", "points.csv", "bed.tif", "reference.tif", "difference.tif"}
        summary = json.loads(bundle.read("summary.json"))
        assert summary["provenance"]["survey"]["filename"] == "input_survey.csv"
        with rasterio.MemoryFile(bundle.read("difference.tif")) as memory:
            with memory.open() as raster:
                assert raster.crs.to_epsg() == 28992
                assert raster.tags()["vertical_datum"] == "NAP"
                assert (raster.read(1, masked=True).compressed() == 1).all()
    assert client.get(result["exports"]["summary"]).json() == summary


def test_previous_survey_upload_has_correct_interpretation(client):
    reference = CSV.replace(b",1\n", b",0\n")
    response = client.post("/api/analyze", data={"config": configuration(reference_mode="file", reference_type="previous")},
                           files={"survey": ("current.csv", CSV), "reference": ("previous.csv", reference)})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["summary"]["positive_volume_m3"] == pytest.approx(4)
    assert "previous_not_sludge" in {w["code"] for w in result["warnings"]}


@pytest.mark.parametrize("config,expected", [
    ("not JSON", "invalid_config"), ("[]", "invalid_config"),
    (configuration(crs="EPSG:4326"), "geographic_crs"),
    (configuration(vertical_datum=""), "missing_vertical_datum"),
    (configuration(reference_mode="file", reference_vertical_datum="ODN"), "datum_mismatch"),
    (configuration(reference_type="underside"), "invalid_reference"),
])
def test_bad_metadata_returns_structured_errors(client, config, expected):
    response = client.post("/api/analyze", data={"config": config}, files={"survey": ("survey.csv", CSV)})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == expected


def test_invalid_csv_and_unsupported_upload(client):
    for filename, contents, expected in [("survey.csv", b"x,y,z\n1,2,nonsense", "invalid_csv"),
                                         ("survey.exe", CSV, "unsupported_format")]:
        response = client.post("/api/analyze", data={"config": configuration()}, files={"survey": (filename, contents)})
        assert response.status_code == 422
        assert response.json()["error"]["code"] == expected


def test_demo_types_are_validated_before_metadata_checks(client):
    response = client.post("/api/analyze", data={"demo": "true", "config": json.dumps({"vertical_datum": None})})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_config"


def test_generated_demo_reference_cannot_be_a_previous_survey(client):
    response = client.post("/api/analyze", data={"demo": "true", "config": configuration(reference_mode="file", reference_type="previous")})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_reference"


def test_real_rws_example_end_to_end(client):
    assert client.get("/").status_code == 200
    assert client.get("/api/health").json()["foundation"] == "GeoUtils"
    demo = client.get("/api/demo").json()
    assert demo["license"] == "CC0-1.0"
    assert client.get(demo["files"]["survey"]).content.startswith(b"x,y,z")
    response = client.post("/api/analyze", data={"demo": "true"})
    assert response.status_code == 200, response.text
    result = response.json()
    s = result["summary"]
    assert s["input_points"] == 12000
    assert s["valid_area_m2"] == pytest.approx(11741, abs=1e-7)
    assert s["positive_volume_m3"] == pytest.approx(2616.6737851464727, abs=1e-7)
    assert s["negative_volume_m3"] == pytest.approx(829.9073631364955, abs=1e-7)
    assert result["provenance"]["survey"]["sha256"] == "eea7681101ec2c714d0883911d345ac66942ff9f7face0b89ac3113891c352ba"
    assert "design_not_sludge" in {w["code"] for w in result["warnings"]}


def test_exports_do_not_allow_unlisted_files(client):
    assert client.get("/api/results/" + "a" * 32 + "/input_survey.csv").status_code == 404
    assert client.get("/api/results/not-an-id/summary.json").status_code == 404
    assert client.get("/api/demo/no-such-file").status_code == 404
