"""Independent numerical verification, not a field-accuracy benchmark.

Known geometry tests the externally visible calculation and support rules.
The downloaded RWS example is covered separately by the real-data demo.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pytest
import rasterio
from affine import Affine
from shapely import union_all
from shapely.geometry import MultiPolygon, Polygon, box, mapping

from ease_volume.core import (
    AnalysisConfig,
    AnalysisError,
    Points,
    analyze,
    load_points,
    make_surface,
)


def config(**changes):
    values = dict(reference_elevation=0.0, reference_note="Analytical test reference",
                  cell_size=1.0, max_edge=1.5, filter_mode="off")
    values.update(changes)
    return AnalysisConfig.parse(values)


def points_file(path: Path, xs, ys, elevation):
    x, y = np.meshgrid(np.asarray(xs, float), np.asarray(ys, float))
    z = np.broadcast_to(elevation(x, y), x.shape)
    np.savetxt(path, np.column_stack((x.ravel(), y.ravel(), z.ravel())),
               delimiter=",", header="x,y,z", comments="", fmt="%.12g")
    return path


def boundary_file(path: Path, geometry):
    obj = {"type": "Feature", "geometry": mapping(geometry), "properties": {},
           "crs": {"type": "name", "properties": {"name": "EPSG:28992"}}}
    path.write_text(json.dumps(obj))
    return path


def raster_file(path: Path, values, **tags):
    values = np.asarray(values, dtype="float64")
    with rasterio.open(path, "w", driver="GTiff", width=values.shape[1],
                       height=values.shape[0], count=1, dtype="float64",
                       crs="EPSG:28992", transform=Affine(1, 0, 0, 0, -1, values.shape[0]),
                       nodata=-9999.0) as dst:
        dst.write(values, 1)
        dst.update_tags(**tags)
    return path


@pytest.mark.parametrize("height,expected", [(0.0, 0.0), (0.2, 20.0), (-0.2, -20.0)])
def test_flat_surfaces_have_analytic_signed_volumes(tmp_path, height, expected):
    survey = points_file(tmp_path / "survey.csv", range(11), range(11), lambda x, y: height)
    result = analyze(survey, None, None, config(), tmp_path / "out")
    s = result["summary"]
    assert s["valid_area_m2"] == pytest.approx(100.0)
    assert s["net_volume_m3"] == pytest.approx(expected)
    assert s["positive_volume_m3"] == pytest.approx(max(expected, 0))
    assert s["negative_volume_m3"] == pytest.approx(max(-expected, 0))


def test_linear_tin_reproduces_sloping_plane_integral(tmp_path):
    # Integral of 0.1*x + 0.2*y over [0,10]^2 is 150 m3.
    survey = points_file(tmp_path / "survey.csv", range(11), range(11), lambda x, y: 0.1*x + 0.2*y)
    result = analyze(survey, None, None, config(), tmp_path / "out")
    assert result["summary"]["positive_volume_m3"] == pytest.approx(150.0)
    assert result["summary"]["negative_volume_m3"] == pytest.approx(0.0)
    values = np.asarray(result["grid"]["bed"], float)
    x, y = np.meshgrid(result["grid"]["x"], result["grid"]["y"])
    assert np.allclose(values, 0.1*x + 0.2*y)


def test_positive_and_negative_changes_do_not_cancel_cut_volume(tmp_path):
    # The zero crossing x=5 aligns with a cell edge: each signed half is 125 m3.
    survey = points_file(tmp_path / "survey.csv", range(11), range(11), lambda x, y: x-5)
    result = analyze(survey, None, None, config(), tmp_path / "out")
    s = result["summary"]
    assert s["positive_volume_m3"] == pytest.approx(125.0)
    assert s["negative_volume_m3"] == pytest.approx(125.0)
    assert s["net_volume_m3"] == pytest.approx(0.0)
    assert s["positive_area_m2"] == pytest.approx(50.0)
    assert s["negative_area_m2"] == pytest.approx(50.0)


def test_grid_refinement_resolves_unaligned_zero_crossing(tmp_path):
    # Exact cut is 10 * (10-5.2)^2 / 2 = 115.2 m3. Coarse positive clipping
    # has quadrature error, despite the underlying TIN reproducing the plane.
    survey = points_file(tmp_path / "survey.csv", range(11), range(11), lambda x, y: x-5.2)
    coarse = analyze(survey, None, None, config(), tmp_path / "coarse")
    fine = analyze(survey, None, None, config(cell_size=0.2), tmp_path / "fine")
    exact = 115.2
    coarse_error = abs(coarse["summary"]["positive_volume_m3"] - exact)
    fine_error = abs(fine["summary"]["positive_volume_m3"] - exact)
    assert fine_error < coarse_error
    assert fine["summary"]["positive_volume_m3"] == pytest.approx(exact)
    assert fine["summary"]["negative_volume_m3"] == pytest.approx(135.2)


def test_reference_file_uses_only_common_survey_support(tmp_path):
    survey = points_file(tmp_path / "survey.csv", range(11), range(11), lambda x, y: -2.)
    reference = points_file(tmp_path / "reference.csv", range(2, 9), range(11), lambda x, y: -3.)
    result = analyze(survey, reference, None, config(reference_mode="file"), tmp_path / "out")
    assert result["summary"]["valid_area_m2"] == pytest.approx(60.0)
    assert result["summary"]["positive_volume_m3"] == pytest.approx(60.0)
    assert result["summary"]["excluded_area_m2"] == pytest.approx(40.0)


def test_polygon_hole_excluded_from_area_and_volume(tmp_path):
    survey = points_file(tmp_path / "survey.csv", range(11), range(11), lambda x, y: 1.)
    outer = box(0, 0, 10, 10)
    boundary = boundary_file(tmp_path / "boundary.geojson", Polygon(outer.exterior.coords, [box(4, 4, 6, 6).exterior.coords]))
    result = analyze(survey, None, boundary, config(), tmp_path / "out")
    assert result["summary"]["valid_area_m2"] == pytest.approx(96.0)
    assert result["summary"]["positive_volume_m3"] == pytest.approx(96.0)
    bed = np.asarray(result["grid"]["bed"], float)
    x, y = np.meshgrid(result["grid"]["x"], result["grid"]["y"])
    assert np.isnan(bed[(x > 4) & (x < 6) & (y > 4) & (y < 6)]).all()


def test_long_triangles_do_not_bridge_unsurveyed_gap(tmp_path):
    survey = points_file(tmp_path / "survey.csv", [0, 1, 2, 8, 9, 10], range(5), lambda x, y: 1.)
    result = analyze(survey, None, None, config(), tmp_path / "out")
    assert result["summary"]["valid_area_m2"] == pytest.approx(16.0)
    assert result["summary"]["positive_volume_m3"] == pytest.approx(16.0)
    assert result["summary"]["coverage_percent"] == pytest.approx(40.0)
    bed = np.asarray(result["grid"]["bed"], float)
    x, _ = np.meshgrid(result["grid"]["x"], result["grid"]["y"])
    assert np.isnan(bed[(x > 2) & (x < 8)]).all()


def test_surface_does_not_extrapolate_outside_hull():
    xyz = np.array([[0., 0., 1.], [1., 0., 2.], [0., 1., 3.]])
    source = Points(xyz, "xyz_points", "test", "test.csv")
    surface = make_surface(source, xyz, 2.)
    values = surface.sample(np.array([[0.2, 0.2], [-0.1, 0.2], [0.8, 0.8]]))
    assert values[0] == pytest.approx(1.6)
    assert np.isnan(values[1:]).all()


def test_partial_cell_areas_used_instead_of_whole_cells(tmp_path):
    survey = points_file(tmp_path / "survey.csv", range(3), range(3), lambda x, y: 1.)
    boundary = boundary_file(tmp_path / "boundary.geojson", box(0.25, 0, 1.75, 2))
    result = analyze(survey, None, boundary, config(), tmp_path / "out")
    assert result["summary"]["requested_area_m2"] == pytest.approx(3.0)
    assert result["summary"]["valid_area_m2"] == pytest.approx(3.0)
    assert result["summary"]["positive_volume_m3"] == pytest.approx(3.0)


def test_partial_cells_with_centres_outside_boundary_are_accounted_for(tmp_path):
    # Supported area includes x=1..1.25 even though the x=1.5 cell centre is outside.
    survey = points_file(tmp_path / "survey.csv", range(3), range(3), lambda x, y: 1.)
    boundary = boundary_file(tmp_path / "boundary.geojson", box(0.25, 0, 1.25, 2))
    result = analyze(survey, None, boundary, config(), tmp_path / "out")
    assert result["summary"]["requested_area_m2"] == pytest.approx(2.0)
    assert result["summary"]["valid_area_m2"] == pytest.approx(2.0)
    assert result["summary"]["positive_volume_m3"] == pytest.approx(2.0)


def test_partial_cell_centroids_reproduce_clipped_plane_integral(tmp_path):
    # Integral of x over x=.25..1.5, y=0..2 is 2.1875; nominal centres give 2.25.
    survey = points_file(tmp_path / "survey.csv", range(3), range(3), lambda x, y: x)
    boundary = boundary_file(tmp_path / "boundary.geojson", box(0.25, 0, 1.5, 2))
    result = analyze(survey, None, boundary, config(), tmp_path / "out")
    assert result["summary"]["positive_volume_m3"] == pytest.approx(2.1875)


def test_narrow_surface_patches_preserve_coverage_and_cell_height(tmp_path):
    survey = points_file(tmp_path / "survey.csv", range(3), range(3), lambda x, y: x)
    covered = MultiPolygon([box(0.25, 0, 0.5, 0.75), box(0.25, 1.25, 0.5, 2)])
    boundary = boundary_file(tmp_path / "boundary.geojson", covered)
    result = analyze(survey, None, boundary, config(), tmp_path / "out")
    assert result["grid"]["valid"] == [[True], [True]]
    mesh = result["bed_mesh"]
    assert mesh["cell_count"] == 2
    triangles = np.column_stack((mesh["x"], mesh["y"])).reshape(-1, 3, 2)
    assert union_all([Polygon(triangle) for triangle in triangles]).equals(covered)
    assert mesh["bed"] == pytest.approx([0.375] * len(mesh["x"]))
    assert mesh["reference"] == [0] * len(mesh["x"])
    assert result["summary"]["positive_volume_m3"] == pytest.approx(0.140625)


def test_geotiff_nodata_hole_stays_unknown_in_export(tmp_path):
    values = np.full((5, 5), -2.)
    values[2, 2] = -9999.
    survey = raster_file(tmp_path / "survey.tif", values)
    result = analyze(survey, None, None, config(reference_elevation=-3., max_edge=3.), tmp_path / "out")
    with rasterio.open(tmp_path / "out" / "difference.tif") as raster:
        row, col = raster.index(2.5, 2.5)
        data = raster.read(1, masked=True)
        assert data.mask[row, col]
        assert np.allclose(data.compressed(), 1.)
        assert raster.crs.to_epsg() == 28992
        assert raster.tags()["vertical_datum"] == "NAP"
    assert result["summary"]["source_kind"] == "raster_cell_centres"


@pytest.mark.parametrize("changes,code", [
    ({"crs": "EPSG:4326"}, "geographic_crs"),
    ({"crs": "EPSG:2263"}, "units_not_meters"),
    ({"units": "ft"}, "units_not_meters"),
    ({"reference_mode": "file", "reference_crs": "EPSG:32631"}, "crs_mismatch"),
    ({"reference_mode": "file", "reference_vertical_datum": "ODN"}, "datum_mismatch"),
    ({"vertical_datum": ""}, "missing_vertical_datum"),
    ({"reference_note": ""}, "invalid_reference"),
    ({"sigma_current": 0.1}, "invalid_config"),
])
def test_incompatible_or_missing_metadata_rejected(changes, code):
    with pytest.raises(AnalysisError) as error:
        config(**changes)
    assert error.value.code == code


def test_explicit_nap_identifier_alias_accepted():
    value = config(reference_mode="file", reference_vertical_datum="EPSG:5709")
    assert value.vertical_datum == "NAP"


def test_geotiff_horizontal_crs_does_not_get_silently_relabelled(tmp_path):
    path = raster_file(tmp_path / "survey.tif", np.zeros((3, 3)))
    with pytest.raises(AnalysisError) as error:
        load_points(path, "EPSG:32631")
    assert error.value.code == "crs_mismatch"


@pytest.mark.parametrize("tags", [
    {"vertical_datum": "ODN", "units": "m"},
    {"vertical_datum": "NAP", "units": "ft"},
    {"vertical_datum": "NAP", "z_convention": "depth_positive_down"},
])
def test_contradictory_geotiff_metadata_must_not_be_silently_overridden(tmp_path, tags):
    path = raster_file(tmp_path / "survey.tif", np.zeros((3, 3)), **tags)
    with pytest.raises(AnalysisError):
        analyze(path, None, None, config(), tmp_path / "out")


def test_duplicate_xy_median_not_arbitrary_return(tmp_path):
    survey = points_file(tmp_path / "survey.csv", range(4), range(4), lambda x, y: 1.)
    with survey.open("a") as stream:
        stream.write("1,1,1\n1,1,100\n")
    result = analyze(survey, None, None, config(), tmp_path / "out")
    assert result["summary"]["duplicate_points"] == 2
    assert result["summary"]["positive_volume_m3"] == pytest.approx(9.0)
    with (tmp_path / "out" / "points.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    duplicate_location = [r for r in rows if float(r["x"]) == 1. and float(r["y"]) == 1.]
    assert len(duplicate_location) == 1
    assert float(duplicate_location[0]["z_elevation_m"]) == 1.


def test_fixed_datum_depth_and_elevation_produce_equivalent_result(tmp_path):
    elevation = points_file(tmp_path / "elevation.csv", range(4), range(4), lambda x, y: -2.)
    depth = points_file(tmp_path / "depth.csv", range(4), range(4), lambda x, y: 2.)
    first = analyze(elevation, None, None, config(reference_elevation=-3.), tmp_path / "elevation_out")
    second = analyze(depth, None, None, config(reference_elevation=-3., z_convention="depth"), tmp_path / "depth_out")
    assert first["summary"]["positive_volume_m3"] == pytest.approx(9.0)
    assert second["summary"]["positive_volume_m3"] == pytest.approx(9.0)


def test_outlier_flags_preserve_original_measurement_and_explicit_exclusion(tmp_path):
    survey = points_file(tmp_path / "survey.csv", range(7), range(7),
                         lambda x, y: np.where((x == 3) & (y == 3), 100., 0.))
    flagged = analyze(survey, None, None, config(filter_mode="flag"), tmp_path / "flagged")
    with (tmp_path / "flagged" / "points.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    centre = next(row for row in rows if float(row["x"]) == 3. and float(row["y"]) == 3.)
    assert float(centre["z_elevation_m"]) == 100.
    assert centre["flagged"] == "1"
    assert centre["used"] == "1"
    assert flagged["summary"]["accepted_points"] == 49
    excluded = analyze(survey, None, None, config(filter_mode="exclude"), tmp_path / "excluded")
    assert excluded["summary"]["accepted_points"] < 49
    assert excluded["summary"]["positive_volume_m3"] == pytest.approx(0.)
    assert excluded["summary"]["valid_area_m2"] <= flagged["summary"]["valid_area_m2"]
