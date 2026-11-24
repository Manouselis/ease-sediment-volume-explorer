"""Synthetic tests of the conservative, explicitly observed export-pair audit."""
import json

import numpy as np
import pytest
from fastapi.testclient import TestClient

from ease_volume import server
from scripts.review_hydromagic import review_pair


def sounding(tmp_path, *, corrections=(-5., -9999., 5.), depth=1., version="12.0"):
    xyz, records = [], []
    for i, correction in enumerate(corrections):
        fields = ["0"] * 24
        fields[0:5] = ["SND", str(1758097977+i), str(100+i), str(200+i), str(depth)]
        fields[13] = str(correction)
        xyz.append([100+i, 200+i, correction-depth if correction != -9999 else depth])
        records.append(" ".join(fields))
    path = tmp_path / "SNDG00001"
    path.write_text(f"VER {version}\nNDT -9999\n" + "\n".join(records))
    return path, np.array(xyz, dtype=float)


def test_missing_correction_is_withheld_but_valid_positive_elevation_is_retained(tmp_path):
    path, xyz = sounding(tmp_path)
    original = xyz.copy()
    report, candidate, rows = review_pair(xyz, path)
    assert candidate.tolist() == [True, False, True]
    assert report["withheld_missing_correction_count"] == 1
    assert report["positive_z_count"] == 2
    assert report["positive_z_with_missing_correction"] == 1
    assert xyz[candidate][-1, 2] == 4
    assert np.array_equal(xyz, original), "The diagnostic must not rewrite heights"
    assert rows[1][-1] == "missing_correction_export_matches_depth"
    assert "Not an authoritative" in report["schema_basis"]


def test_rounded_processed_values_match_full_precision_exports(tmp_path):
    path, xyz = sounding(tmp_path)
    xyz[0, :2] += .00049
    xyz[0, 2] += .00098
    report, _, _ = review_pair(xyz, path)
    assert report["z_relationship_max_error_m"] < .0011


@pytest.mark.parametrize("change", ["version", "count", "row_order", "z", "nonfinite", "layout"])
def test_unverified_pair_cannot_produce_an_automatic_subset(tmp_path, change):
    path, xyz = sounding(tmp_path, version="11.0" if change == "version" else "12.0")
    if change == "count": xyz = xyz[:-1]
    if change == "row_order": xyz = xyz[::-1]
    if change == "z": xyz[0, 2] += .1
    if change == "nonfinite": xyz[0, 2] = np.nan
    if change == "layout": path.write_text(path.read_text().replace("SND ", "SND 0 "))
    with pytest.raises(ValueError):
        review_pair(xyz, path)


def test_all_missing_corrections_do_not_invent_elevations(tmp_path):
    path, xyz = sounding(tmp_path, corrections=(-9999.,)*3)
    report, mask, _ = review_pair(xyz, path)
    assert mask.sum() == 0 and report["candidate_count"] == 0


def test_web_preprocessing_uses_same_subset_for_inspection_and_volume(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "RUNS", tmp_path)
    client = TestClient(server.app)
    xy = [(177000, 500000), (177001, 500000), (177000, 500001), (177001, 500001),
          (177000.5, 500000.5)]
    csv_rows = ["x,y,z"]
    records = ["VER 12.0", "NDT -9999"]
    for i, (x, y) in enumerate(xy):
        missing = i == 4
        csv_rows.append(f"{x},{y},{1 if missing else -6}")
        fields = ["0"] * 24
        fields[:5] = ["SND", str(1758097977 + i), str(x), str(y), "1"]
        fields[13] = "-9999" if missing else "-5"
        records.append(" ".join(fields))
    files = {"survey": ("survey.csv", "\n".join(csv_rows)), "sounding": ("SNDG00001", "\n".join(records))}

    inspected = client.post("/api/inspect", files=files)
    assert inspected.status_code == 200, inspected.text
    assert inspected.json()["point_count"] == 4
    assert inspected.json()["height_review"]["withheld_missing_correction_count"] == 1
    assert inspected.json()["points"]["z"] == [-6] * 4

    config = {"reference_note": "Synthetic design", "filter_mode": "off"}
    unconfirmed = client.post("/api/analyze", files=files, data={"config": json.dumps(config)})
    assert unconfirmed.status_code == 422
    assert unconfirmed.json()["error"]["code"] == "preprocess_volume_heights"

    config["survey_nap_confirmed"] = True
    analyzed = client.post("/api/analyze", files=files, data={"config": json.dumps(config)})
    assert analyzed.status_code == 200, analyzed.text
    result = analyzed.json()
    assert result["summary"]["input_points"] == 5
    assert result["summary"]["accepted_points"] == 4
    assert result["summary"]["withheld_height_correction_points"] == 1
    assert result["summary"]["positive_volume_m3"] == pytest.approx(.5)
