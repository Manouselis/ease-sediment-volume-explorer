"""Synthetic geometry checks for import, inspection and spatial selection.

The tests generate their own PointZ fixtures.
"""
import io
import json
import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pytest
from fastapi.testclient import TestClient
from pyproj import CRS
from shapely.geometry import Point, LineString

from ease_volume import server
from ease_volume.core import AnalysisConfig, AnalysisError, analyze, inspect_survey, load_points
from ease_volume.vector import pointz_crs_matches


def package(tmp_path, xyz=None, *, geometry=None, crs="EPSG:28992", omit=(), nested=False):
    folder = tmp_path / "source"
    folder.mkdir(exist_ok=True)
    if xyz is None:
        xyz = np.array([(x, y, -2.5) for y in range(3) for x in range(3)])
    points = geometry if geometry is not None else [Point(*p) for p in xyz]
    gpd.GeoDataFrame({"name": ["SNDG00001"] * len(points), "transducer": [1]*len(points)}, geometry=points, crs=crs).to_file(folder / "soundings.shp")
    target = tmp_path / "survey.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for p in folder.glob("soundings.*"):
            if p.suffix not in omit:
                archive.write(p, arcname=("nested/" if nested else "")+p.name.upper())
    return target


def config(**changes):
    values = {"reference_elevation": -3.5, "reference_note": "Synthetic analytical target", "filter_mode": "off", "max_edge": 2}
    return AnalysisConfig.parse(values | changes)


def test_pointz_is_geometry_not_attribute_or_negated_depth(tmp_path):
    p = package(tmp_path, nested=True)
    source = load_points(p, "EPSG:28992", "elevation", "NAP")
    assert source.source_kind == "shapefile_pointz"
    assert np.array_equal(source.xyz, [(x, y, -2.5) for y in range(3) for x in range(3)])
    assert source.metadata["height_source"].startswith("geometry Z")
    assert source.metadata["name_counts"] == {"SNDG00001": 9}
    assert np.array_equal(load_points(p, "EPSG:28992", "depth").xyz[:, 2], np.full(9, 2.5))


def test_inspection_needs_no_reference_and_preserves_extreme_heights(tmp_path):
    p = package(tmp_path, [(0, 0, -9), (1, 0, 4), (0, 1, -8)])
    result = inspect_survey(p, "EPSG:28992", "elevation", "NAP")
    assert result["point_count"] == 3
    assert result["z_min_m"] == -9 and result["z_max_m"] == 4
    assert result["positive_z_count"] == 1
    assert "volume" not in json.dumps(result)
    assert "user_declared" in result["vertical_datum_status"]


def test_repeated_single_location_has_json_safe_inspection(tmp_path):
    p = package(tmp_path, [(0,0,-2)]*3)
    result = inspect_survey(p, "EPSG:28992", "elevation", "NAP")
    assert result["unique_xy_count"] == 1
    assert result["nearest_neighbour_m"]["p50"] is None
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("omit", [(".prj",), (".shx",), (".dbf",)])
def test_missing_shapefile_components_are_rejected(tmp_path, omit):
    p = package(tmp_path, omit=omit)
    with pytest.raises(AnalysisError, match="invalid_shapefile"):
        load_points(p, "EPSG:28992")


@pytest.mark.parametrize("geometry", [[Point(0,0), Point(1,0), Point(0,1)], [LineString([(0,0,1),(1,1,2)])]])
def test_2d_or_non_point_geometry_is_not_invented_as_bathymetry(tmp_path, geometry):
    p = package(tmp_path, geometry=geometry)
    with pytest.raises(AnalysisError, match="shapefile_requires_pointz"):
        load_points(p, "EPSG:28992")


def test_embedded_crs_must_match(tmp_path):
    p = package(tmp_path)
    with pytest.raises(AnalysisError, match="crs_mismatch"):
        load_points(p, "EPSG:32631")


def test_rounded_hydromagic_rd_new_checks_projection_and_coordinates():
    rd_new = CRS("EPSG:28992")
    legacy = (rd_new.to_wkt(version="WKT1_GDAL")
              .replace("52.1561605555556", "52.15616056")
              .replace("5.38763888888889", "5.38763889")
              .replace("0.9999079", "0.999908"))
    assert not CRS(legacy).equals(rd_new)
    assert pointz_crs_matches(CRS(legacy), rd_new)
    assert not pointz_crs_matches(CRS(legacy), CRS("EPSG:32631"))
    for wrong in (legacy.replace("155000", "155001"),
                  legacy.replace("0.999908", "1.000001"),
                  legacy.replace("6377397.155", "6377398.155")):
        assert not pointz_crs_matches(CRS(wrong), rd_new)


@pytest.mark.parametrize("kind", ["corrupt", "multiple", "traversal"])
def test_invalid_or_ambiguous_archives_are_rejected(tmp_path, kind):
    p = package(tmp_path)
    if kind == "corrupt":
        p.write_bytes(b"not a ZIP")
    else:
        with zipfile.ZipFile(p, "a") as archive:
            archive.writestr("other.shp" if kind == "multiple" else "../escape.txt", b"invalid")
    with pytest.raises(AnalysisError, match="invalid_shapefile"):
        load_points(p, "EPSG:28992")
    assert not (tmp_path.parent / "escape.txt").exists()


def test_feature_limit_is_checked_before_loading_all_features(tmp_path, monkeypatch):
    p = package(tmp_path)
    from ease_volume import core
    monkeypatch.setattr(core, "MAX_POINTS", 3)
    with pytest.raises(AnalysisError, match="too_many_points"):
        load_points(p, "EPSG:28992")


def test_zip_analysis_matches_the_analytical_volume_and_records_provenance(tmp_path):
    p = package(tmp_path)
    result = analyze(p, None, None, config(), tmp_path / "output")
    assert result["summary"]["positive_volume_m3"] == pytest.approx(4)
    assert result["summary"]["negative_volume_m3"] == 0
    assert result["provenance"]["survey"]["metadata"]["geometry"] == "PointZ"
    assert "shapefile_source" in {w["code"] for w in result["warnings"]}


def test_crop_limits_points_before_tin_and_grid_and_is_exported(tmp_path):
    p = package(tmp_path, [(x, y, -2.5) for y in range(5) for x in range(5)])
    result = analyze(p, None, None, config(analysis_bounds=[1, 1, 3, 3]), tmp_path / "output")
    s = result["summary"]
    assert s["input_points"] == 25 and s["selected_points"] == 9
    assert s["outside_analysis_area_points"] == 16
    assert s["valid_area_m2"] == pytest.approx(4)
    assert s["positive_volume_m3"] == pytest.approx(4)
    assert result["provenance"]["configuration"]["analysis_bounds"] == (1.,1.,3.,3.)
    rows = np.genfromtxt(tmp_path / "output/points.csv", delimiter=",", names=True)
    assert len(rows) == 9 and rows["x"].min() >= 1 and rows["x"].max() <= 3


@pytest.mark.parametrize("bounds", [[2,0,1,2], [0,2,1,1], [0,0,float("nan"),1], [0,1,2]])
def test_bad_selection_bounds_are_rejected(bounds):
    with pytest.raises(AnalysisError, match="invalid_config"):
        config(analysis_bounds=bounds)


def test_disjoint_area_or_too_few_selected_points_cannot_give_a_volume(tmp_path):
    p = package(tmp_path)
    with pytest.raises(AnalysisError, match="too_few_points"):
        analyze(p, None, None, config(analysis_bounds=[100,100,110,110]), tmp_path / "out")


def test_selected_shapefile_can_be_compared_with_itself_as_a_file_reference(tmp_path):
    p = package(tmp_path, [(x,y,-2.5 + .1*x) for y in range(5) for x in range(5)])
    result = analyze(p, p, None, config(reference_mode="file", reference_type="previous", analysis_bounds=[1,1,3,3]), tmp_path / "out")
    assert result["summary"]["positive_volume_m3"] == pytest.approx(0, abs=1e-12)
    assert result["summary"]["negative_volume_m3"] == pytest.approx(0, abs=1e-12)
    assert result["provenance"]["reference"]["metadata"]["geometry"] == "PointZ"


def test_analysis_selection_intersects_the_uploaded_boundary(tmp_path):
    p = package(tmp_path, [(x,y,-2.5) for y in range(5) for x in range(5)])
    boundary = tmp_path / "boundary.geojson"
    boundary.write_text(json.dumps({"type":"Polygon", "coordinates":[[[0,0],[2,0],[2,4],[0,4],[0,0]]], "crs":{"type":"name","properties":{"name":"EPSG:28992"}}}))
    result = analyze(p, None, boundary, config(analysis_bounds=[1,1,3,3]), tmp_path / "out")
    assert result["summary"]["requested_area_m2"] == pytest.approx(2)
    assert result["summary"]["valid_area_m2"] == pytest.approx(2)
    assert result["summary"]["positive_volume_m3"] == pytest.approx(2)


def test_inspection_and_analysis_http_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "RUNS", tmp_path / "runs")
    p = package(tmp_path)
    client = TestClient(server.app)
    files = {"survey": ("survey.zip", p.read_bytes(), "application/zip")}
    response = client.post("/api/inspect", data={"crs":"EPSG:28992", "vertical_datum":"NAP"}, files=files)
    assert response.status_code == 200, response.text
    assert response.json()["source_kind"] == "shapefile_pointz"
    assert not list(server.RUNS.iterdir()), "Temporary inspection uploads must be cleaned up"
    response = client.post("/api/analyze", data={"config":config().model_dump_json()}, files=files)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["summary"]["positive_volume_m3"] == pytest.approx(4)
    with zipfile.ZipFile(io.BytesIO(client.get(result["exports"]["bundle"]).content)) as archive:
        summary = json.loads(archive.read("summary.json"))
        assert summary["provenance"]["survey"]["metadata"]["geometry"] == "PointZ"
