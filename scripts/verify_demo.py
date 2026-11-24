#!/usr/bin/env python3
"""Independently check numerical consistency of the bundled real-data demo.

No ease_volume.core, LinearNDInterpolator, GeoUtils, Rasterio, or Shapely is
imported here. Qhull Delaunay connectivity is shared through SciPy; elevations,
convex polygon clipping, cell areas/centroids and volume sums are computed
separately. This is not a field accuracy or sludge-thickness validation.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

import numpy as np
from scipy.spatial import ConvexHull, Delaunay

ROOT = Path(__file__).resolve().parents[1]
POINT_TOLERANCE_M = 1e-8
VOLUME_TOLERANCE_M3 = 1e-6
AREA_TOLERANCE_M2 = 1e-7


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def oriented_cross(a: tuple, b: tuple, p: tuple) -> float:
    return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])


def polygon_measure(vertices: list[tuple[float, float]]) -> tuple[float, tuple[float, float]]:
    """Shoelace area and centroid after shifting origin for numerical stability."""
    if len(vertices) < 3:
        return 0.0, (math.nan, math.nan)
    ox, oy = vertices[0]
    local = [(x - ox, y - oy) for x, y in vertices]
    crosses = [a[0] * b[1] - b[0] * a[1]
               for a, b in zip(local, local[1:] + local[:1])]
    twice_area = math.fsum(crosses)
    if abs(twice_area) < 1e-14:
        return 0.0, (math.nan, math.nan)
    cx = math.fsum((a[0] + b[0]) * c for a, b, c in
                   zip(local, local[1:] + local[:1], crosses)) / (3 * twice_area)
    cy = math.fsum((a[1] + b[1]) * c for a, b, c in
                   zip(local, local[1:] + local[:1], crosses)) / (3 * twice_area)
    return abs(twice_area) / 2, (ox + cx, oy + cy)


def ccw(vertices: list[tuple[float, float]]) -> list[tuple[float, float]]:
    vertices = list(vertices)
    if vertices[0] == vertices[-1]:
        vertices.pop()
    x0, y0 = vertices[0]
    signed = math.fsum((a[0] - x0) * (b[1] - y0) - (b[0] - x0) * (a[1] - y0)
                       for a, b in zip(vertices, vertices[1:] + vertices[:1]))
    return vertices if signed > 0 else vertices[::-1]


def clip_convex(subject: list[tuple], clipper: list[tuple]) -> list[tuple]:
    """Sutherland–Hodgman clipping against an anticlockwise convex polygon."""
    output = list(subject)
    for a, b in zip(clipper, clipper[1:] + clipper[:1]):
        incoming, output = output, []
        if not incoming:
            break
        previous = incoming[-1]
        previous_distance = oriented_cross(a, b, previous)
        for current in incoming:
            current_distance = oriented_cross(a, b, current)
            previous_inside = previous_distance >= -1e-12
            current_inside = current_distance >= -1e-12
            if previous_inside != current_inside:
                t = previous_distance / (previous_distance - current_distance)
                output.append((previous[0] + t * (current[0] - previous[0]),
                               previous[1] + t * (current[1] - previous[1])))
            if current_inside:
                output.append(current)
            previous, previous_distance = current, current_distance
    return output


def read_demo_boundary() -> list[tuple]:
    obj = json.loads((ROOT / "data/demo_boundary.geojson").read_text())
    geometry = obj["features"][0]["geometry"]
    check(len(obj["features"]) == 1 and geometry["type"] == "Polygon"
          and len(geometry["coordinates"]) == 1,
          "This checker is scoped to the bundled single convex polygon without holes")
    vertices = ccw([tuple(p) for p in geometry["coordinates"][0]])
    check(all(oriented_cross(a, b, p) >= -1e-9 for a, b in
              zip(vertices, vertices[1:] + vertices[:1]) for p in vertices),
          "Demo boundary must be convex for this independent clipper")
    return vertices


def barycentric_elevations(triangulation: Delaunay, xyz: np.ndarray,
                           samples: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Evaluate a planar triangle using explicit area-coordinate formulas."""
    elevations = np.full(len(samples), np.nan)
    indices = np.flatnonzero(valid)
    simplex = triangulation.find_simplex(samples[indices], tol=1e-10)
    check(np.all(simplex >= 0), "An independently clipped sample is outside the source TIN")
    triangles = xyz[triangulation.simplices[simplex]]
    a, b, c = triangles[:, 0], triangles[:, 1], triangles[:, 2]
    px, py = samples[indices, 0] - c[:, 0], samples[indices, 1] - c[:, 1]
    ax, ay = a[:, 0] - c[:, 0], a[:, 1] - c[:, 1]
    bx, by = b[:, 0] - c[:, 0], b[:, 1] - c[:, 1]
    determinant = ax * by - ay * bx
    check(np.all(np.abs(determinant) > 1e-12), "Degenerate Delaunay triangle")
    wa = (px * by - py * bx) / determinant
    wb = (ax * py - ay * px) / determinant
    wc = 1.0 - wa - wb
    check(min(wa.min(), wb.min(), wc.min()) >= -1e-8,
          "Barycentric sample lies outside its selected triangle")
    elevations[indices] = wa * a[:, 2] + wb * b[:, 2] + wc * c[:, 2]
    return elevations


def verify(run_directory: Path) -> dict:
    metadata = json.loads((ROOT / "data/demo_metadata.json").read_text())
    for name, expected in metadata["metadata"]["files_sha256"].items():
        actual = hashlib.sha256((ROOT / "data" / name).read_bytes()).hexdigest()
        check(actual == expected, f"Source checksum mismatch: {name}")
    with (ROOT / "data/demo_current.csv").open(newline="") as stream:
        xyz = np.asarray([[float(row[k]) for k in ("x", "y", "z")]
                          for row in csv.DictReader(stream)])
    result = json.loads((run_directory / "summary.json").read_text())
    summary, provenance = result["summary"], result["provenance"]
    config = provenance["configuration"]
    check(provenance["survey"]["sha256"] == metadata["metadata"]["files_sha256"]["demo_current.csv"],
          "The exported run does not use the bundled source CSV")
    check(config["reference_mode"] == "constant" and config["z_convention"] == "elevation"
          and config["filter_mode"] in ("off", "flag"),
          "Checker requires the demo's constant reference and unchanged elevation points")
    check(summary["accepted_points"] == len(xyz) and summary["duplicate_points"] == 0,
          "Checker assumes all original unique demo points are retained")
    check(config["crs"] == "EPSG:28992" and config["vertical_datum"] == "NAP",
          "Demo datum declarations do not match")
    triangulation = Delaunay(xyz[:, :2])
    vertices = xyz[triangulation.simplices, :2]
    edge_lengths = np.sqrt(np.sum((vertices - np.roll(vertices, 1, axis=1)) ** 2, axis=2))
    check(np.all(edge_lengths <= config["max_edge"] + 1e-10),
          "Some triangles are rejected: convex-hull support is insufficient for this checker")
    hull = ccw([tuple(p) for p in xyz[ConvexHull(xyz[:, :2]).vertices, :2]])
    boundary = read_demo_boundary()
    footprint = clip_convex(hull, boundary)
    footprint_area, _ = polygon_measure(footprint)
    requested_area, _ = polygon_measure(boundary)
    cell = float(config["cell_size"])
    xmin, xmax = min(p[0] for p in boundary), max(p[0] for p in boundary)
    ymin, ymax = min(p[1] for p in boundary), max(p[1] for p in boundary)
    left, right = math.floor(xmin / cell) * cell, math.ceil(xmax / cell) * cell
    bottom, top = math.floor(ymin / cell) * cell, math.ceil(ymax / cell) * cell
    nx, ny = round((right - left) / cell), round((top - bottom) / cell)
    centres, samples, areas = [], [], []
    for row in range(ny):
        y = top - (row + 0.5) * cell
        for col in range(nx):
            x = left + (col + 0.5) * cell
            square = [(x - cell / 2, y - cell / 2), (x + cell / 2, y - cell / 2),
                      (x + cell / 2, y + cell / 2), (x - cell / 2, y + cell / 2)]
            clipped = clip_convex(clip_convex(square, hull), boundary)
            area, centroid = polygon_measure(clipped)
            sample = centroid if 1e-12 < area < cell * cell - 1e-9 else (x, y)
            centres.append((x, y))
            samples.append(sample)
            areas.append(area if area > 1e-12 else 0.0)
    centres, samples, areas = np.asarray(centres), np.asarray(samples), np.asarray(areas)
    valid = areas > 0
    elevations = barycentric_elevations(triangulation, xyz, samples, valid)
    difference = elevations - config["reference_elevation"]
    positive = math.fsum(float(a) * max(0.0, float(d)) for a, d in zip(areas[valid], difference[valid]))
    negative = math.fsum(float(a) * max(0.0, -float(d)) for a, d in zip(areas[valid], difference[valid]))
    area_total = math.fsum(float(a) for a in areas)
    with (run_directory / "cells.csv").open(newline="") as stream:
        exported = list(csv.DictReader(stream))
    check(len(exported) == len(centres), "Exported grid dimensions differ from the independent grid")
    exported_centres = np.asarray([[float(r["x"]), float(r["y"])] for r in exported])
    exported_samples = np.asarray([[float(r["sample_x"]), float(r["sample_y"])] for r in exported])
    exported_areas = np.asarray([float(r["supported_area_m2"]) for r in exported])
    exported_valid = np.asarray([r["valid"] == "1" for r in exported])
    check(np.array_equal(exported_valid, valid), "Independent and exported support masks differ")
    centre_error = float(np.max(np.abs(exported_centres - centres)))
    sample_error = float(np.max(np.abs(exported_samples[valid] - samples[valid])))
    area_error = float(np.max(np.abs(exported_areas - areas)))
    exported_elevations = np.asarray([float(r["bed_elevation_m"]) for r in exported if r["valid"] == "1"])
    exported_difference = np.asarray([float(r["difference_m"]) for r in exported if r["valid"] == "1"])
    elevation_error = float(np.max(np.abs(exported_elevations - elevations[valid])))
    difference_error = float(np.max(np.abs(exported_difference - difference[valid])))
    check(max(centre_error, sample_error, elevation_error, difference_error) < POINT_TOLERANCE_M,
          "Exported positions, sample locations or elevations differ from independent computation")
    check(area_error < AREA_TOLERANCE_M2, "Per-cell supported areas differ")
    check(abs(area_total - footprint_area) < AREA_TOLERANCE_M2,
          "Clipped cells do not sum to the independently computed source footprint")
    check(abs(area_total - summary["valid_area_m2"]) < AREA_TOLERANCE_M2,
          "Reported valid area differs from independent clipping")
    check(abs(requested_area - summary["requested_area_m2"]) < AREA_TOLERANCE_M2,
          "Reported requested area differs from independent polygon area")
    check(abs(positive - summary["positive_volume_m3"]) < VOLUME_TOLERANCE_M3
          and abs(negative - summary["negative_volume_m3"]) < VOLUME_TOLERANCE_M3,
          "Reported volume differs from independent barycentric/clipped-area integration")
    source_area = metadata["metadata"]["grid"]["cell_size_m"]
    source_area = source_area[0] * source_area[1]
    original_difference = xyz[:, 2] - config["reference_elevation"]
    source_positive = math.fsum(source_area * max(0.0, float(d)) for d in original_difference)
    source_negative = math.fsum(source_area * max(0.0, -float(d)) for d in original_difference)
    checks = {
        "passed": True, "scope": "Numerical consistency only; no independent field ground truth",
        "independence": "Separate CSV parser, barycentric formulas, convex polygon clipping, shoelace areas/centroids, and math.fsum integration. SciPy/Qhull Delaunay connectivity and point location are shared dependencies.",
        "source_sha256": provenance["survey"]["sha256"],
        "source_points": len(xyz), "triangles": len(triangulation.simplices),
        "grid_cells": len(centres), "valid_cells": int(valid.sum()),
        "partial_cells": int(np.sum(valid & (areas < cell * cell - 1e-9))),
        "independent_positive_volume_m3": positive, "independent_negative_volume_m3": negative,
        "independent_net_volume_m3": positive - negative,
        "independent_valid_area_m2": area_total, "independent_requested_area_m2": requested_area,
        "independent_footprint_area_m2": footprint_area,
        "maximum_coordinate_error_m": centre_error, "maximum_sample_position_error_m": sample_error,
        "maximum_bed_elevation_error_m": elevation_error, "maximum_difference_error_m": difference_error,
        "maximum_supported_cell_area_error_m2": area_error,
        "positive_volume_error_m3": positive - summary["positive_volume_m3"],
        "negative_volume_error_m3": negative - summary["negative_volume_m3"],
        "full_original_source_grid": {"area_m2": len(xyz) * source_area,
            "positive_volume_m3": source_positive, "negative_volume_m3": source_negative,
            "note": "Different footprint and representation from the application TIN/common-grid result; not an accuracy benchmark."},
        "tolerances": {"position_and_elevation_m": POINT_TOLERANCE_M,
                       "area_m2": AREA_TOLERANCE_M2, "volume_m3": VOLUME_TOLERANCE_M3},
    }
    (run_directory / "independent_verification.json").write_text(json.dumps(checks, indent=2) + "\n")
    return checks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-directory", type=Path, default=ROOT / "demo_output")
    parser.add_argument("--rerun", action="store_true", help="Regenerate default demo output first")
    args = parser.parse_args()
    if args.rerun or not (args.run_directory / "cells.csv").is_file():
        check(args.run_directory.resolve() == (ROOT / "demo_output").resolve(),
              "Only the default demo output can be generated automatically")
        subprocess.run([sys.executable, str(ROOT / "scripts/run_demo.py")],
                       check=True, capture_output=True, text=True)
    print(json.dumps(verify(args.run_directory), indent=2))


if __name__ == "__main__":
    main()
