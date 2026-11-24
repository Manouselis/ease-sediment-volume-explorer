#!/usr/bin/env python3
"""Fetch a small, genuine RWS multibeam-derived grid and convert to XYZ.

Uses only Python's standard library. The reference is an explicitly assumed
design plane, not a second measurement or an observed sediment underside.
Run ``python scripts/download_demo.py --offline`` to reproduce CSVs from the
checked-in WCS response without any network access.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "https://geo.rijkswaterstaat.nl/services/ogc/gdr/bodemhoogte_1mtr_historie/ows"
COVERAGE = "bodemhoogte_1mtr_historie__bodemhoogte_1mtr_202504"
RECORD = "https://maps.rijkswaterstaat.nl/dataregister-publicatie/srv/api/records/1d23ce9d-a11a-4e56-9538-c6f4c8a0fb77"
SOURCE_PAGE = "https://data.overheid.nl/dataset/b4d3f42b-f9d3-421a-8840-75c71951e475"
DESIGN_Z = -6.5
REQUEST_BOUNDS = [133875, 455250, 133935, 455450]


def wcs_url(request: str, extra: list[tuple[str, str]]) -> str:
    return BASE + "?" + urlencode([
        ("service", "WCS"), ("version", "2.0.1"), ("request", request),
        ("coverageId", COVERAGE), *extra,
    ])


DATA_URL = wcs_url("GetCoverage", [
    ("subset", "X(133875,133935)"), ("subset", "Y(455250,455450)"),
    ("format", "text/plain"),
])
DESCRIPTION_URL = wcs_url("DescribeCoverage", [])


def fetch(url: str, destination: Path) -> None:
    for attempt in range(3):
        try:
            request = Request(url, headers={"User-Agent": "EASE-sediment-volume-demo/1.0"})
            with urlopen(request, timeout=60) as response:
                payload = response.read(10_000_001)
            if len(payload) > 10_000_000:
                raise ValueError("Unexpected source response larger than 10 MB")
            destination.write_bytes(payload)
            return
        except Exception:
            if attempt == 2:
                raise
            time.sleep(attempt + 1)


def parse_grid(text: str) -> tuple[list[tuple[float, float, float]], dict]:
    """Parse GeoServer's text/plain raster response and check its affine map.

    The output is a GeoTools grid dump, not ESRI ASCII. Bounds describe pixel
    edges; Grid-to-world uses global raster indices and maps pixel centres.
    This function checks both representations before emitting coordinates.
    """
    if "Band 0:\n" not in text:
        raise ValueError("Response is not the expected single-band WCS text grid")
    header, contents = text.split("Band 0:\n", 1)
    number = r"[-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?"
    bounds_match = re.search(
        rf"Grid bounds: GeneralBounds\[\(({number}), ({number})\), \(({number}), ({number})\)\]",
        header,
    )
    index_match = re.search(r"GridEnvelope2D\[(\d+)\.\.(\d+), (\d+)\.\.(\d+)\]", header)
    if not bounds_match or not index_match or 'AUTHORITY["EPSG","28992"]' not in header:
        raise ValueError("Missing bounds, grid indices, or expected EPSG:28992 CRS")
    xmin, ymin, xmax, ymax = map(float, bounds_match.groups())
    col0, col1, row0, row1 = map(int, index_match.groups())
    width, height = col1 - col0 + 1, row1 - row0 + 1
    dx, dy = (xmax - xmin) / width, (ymax - ymin) / height
    if not math.isclose(dx, 1, abs_tol=1e-8) or not math.isclose(dy, 1, abs_tol=1e-8):
        raise ValueError("Expected source resolution is 1 m, with no resampling")
    affine_text = header.split('Grid to world: PARAM_MT["Affine",', 1)[1]
    affine = dict(re.findall(rf'PARAMETER\["(elt_\d_\d)", ({number})\]', affine_text))
    x_offset = float(affine.get("elt_0_2", 0))
    y_offset = float(affine.get("elt_1_2", 0))
    x_scale = float(affine.get("elt_0_0", 1))
    y_scale = float(affine.get("elt_1_1", 1))
    if float(affine.get("elt_0_1", 0)) or float(affine.get("elt_1_0", 0)):
        raise ValueError("Rotated/skewed source grid is not supported by this converter")
    expected = (xmin + dx / 2, ymax - dy / 2)
    mapped = (x_offset + x_scale * col0, y_offset + y_scale * row0)
    if any(not math.isclose(a, b, abs_tol=1e-7) for a, b in zip(expected, mapped)):
        raise ValueError("Source bounds and affine pixel-centre coordinates disagree")
    rows = [line.split() for line in contents.strip().splitlines() if line.strip()]
    if len(rows) != height or any(len(row) != width for row in rows):
        raise ValueError("Source raster dimensions and values disagree")
    points = []
    missing = 0
    for r, row in enumerate(rows):
        for c, value in enumerate(row):
            z = float(value)
            # RWS declares 3.3999999521443642e38 NoData; the text serializer
            # prints it as 3.4E38. Exclude this marker and nonfinite values.
            if not math.isfinite(z) or abs(z) > 1e30:
                missing += 1
                continue
            points.append((x_offset + x_scale * (col0 + c),
                           y_offset + y_scale * (row0 + r), z))
    if not points:
        raise ValueError("Selected source area contains no valid bed elevations")
    return points, {
        "bounds_pixel_edges": [xmin, ymin, xmax, ymax],
        "shape_rows_columns": [height, width],
        "cell_size_m": [dx, dy], "valid_cells": len(points), "nodata_cells": missing,
        "z_min_m": min(p[2] for p in points), "z_max_m": max(p[2] for p in points),
    }


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_xyz(path: Path, points: list[tuple[float, float, float]], reference: bool = False) -> None:
    with path.open("w", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["x", "y", "z"])
        for x, y, z in points:
            writer.writerow([f"{x:.9f}", f"{y:.9f}", f"{DESIGN_Z if reference else z:.9f}"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Convert the checked-in WCS response without downloading")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parents[1] / "data")
    args = parser.parse_args()
    directory = args.output_dir
    directory.mkdir(parents=True, exist_ok=True)
    raw = directory / "demo_rws_wcs.txt"
    source_xml = directory / "demo_rws_metadata.xml"
    describe_xml = directory / "demo_rws_coverage.xml"
    old_metadata = directory / "demo_metadata.json"
    retrieval_time = datetime.now(timezone.utc).isoformat()
    if args.offline:
        for source in [raw, source_xml, describe_xml]:
            if not source.is_file():
                parser.error(f"Offline source missing: {source}")
        if old_metadata.is_file():
            retrieval_time = json.loads(old_metadata.read_text())["metadata"]["retrieved_at_utc"]
    else:
        fetch(DATA_URL, raw)
        fetch(RECORD + "/formatters/xml", source_xml)
        fetch(DESCRIPTION_URL, describe_xml)
    points, grid = parse_grid(raw.read_text())
    current = directory / "demo_current.csv"
    reference = directory / "demo_reference.csv"
    write_xyz(current, points)
    write_xyz(reference, points, reference=True)
    xmin, ymin, xmax, ymax = grid["bounds_pixel_edges"]
    boundary = {
        "type": "FeatureCollection",
        "name": "RWS demonstration raster footprint",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::28992"}},
        "features": [{"type": "Feature", "properties": {
            "role": "source_raster_footprint", "crs": "EPSG:28992",
            "note": "Pixel-edge rectangle; not a surveyed canal boundary or statutory design boundary.",
        }, "geometry": {"type": "Polygon", "coordinates": [[
            [xmin, ymin], [xmax, ymin], [xmax, ymax], [xmin, ymax], [xmin, ymin],
        ]]}}],
    }
    (directory / "demo_boundary.geojson").write_text(json.dumps(boundary, indent=2) + "\n")
    info = {
        "name": "RWS Amsterdam–Rhine Canal: measured bed and assumed design",
        "description": "A 60 × 200 m subset near Utrecht of the Dutch national 1 m bathymetry snapshot for April 2025. Current XYZ values are genuine multibeam-derived raster cell means. The flat reference is hypothetical.",
        "publisher": "Rijkswaterstaat / RWS Centrale Informatievoorziening (CIV)",
        "source_url": SOURCE_PAGE,
        "license": "CC0-1.0",
        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "crs": "EPSG:28992",
        "vertical_datum": "NAP height (EPSG:5709), metres, positive upwards",
        "reference_elevation": DESIGN_Z,
        "reference_type": "design",
        "reference_status": "Hypothetical flat design at -6.5 m NAP; not an official maintenance profile, earlier survey, or measured sludge underside.",
        "defaults": {"cell_size": 1.0, "max_edge": 2.5, "filter_mode": "flag", "mad_k": 4.5, "mad_floor": 0.25, "neighbors": 16},
        "metadata": {
            "source_title": "Bathymetrie Nederland - binnenwateren 1 mtr. Nederland - april 2025",
            "source_metadata_record": RECORD,
            "coverage_id": COVERAGE,
            "download_url": DATA_URL,
            "describe_coverage_url": DESCRIPTION_URL,
            "retrieved_at_utc": retrieval_time,
            "snapshot_date": "2025-04-23",
            "survey_date": None,
            "survey_date_note": "April 2025 is the composite snapshot date; individual source sounding dates are not provided by this raster subset.",
            "sensor_basis": "Official lineage states multibeam soundings; sensor model and per-cell survey details are not given.",
            "lineage": "The national product aggregates measured bed heights from Rijkswaterstaat's Landelijk Opslagsysteem Lodingen. Each 1 square metre height is the mean of all measured points in that cell.",
            "point_representation": "Raster pixel centres carrying measured cell means, not original individual soundings. No synthetic perturbations, invented sediment thickness, reprojection, or vertical transformation were applied.",
            "requested_bounds_rd_m": REQUEST_BOUNDS,
            "grid": grid,
            "footprint_area_m2": (xmax - xmin) * (ymax - ymin),
            "valid_source_cell_area_m2": grid["valid_cells"] * grid["cell_size_m"][0] * grid["cell_size_m"][1],
            "horizontal_units": "metre", "vertical_units": "metre", "z_convention": "elevation_positive_up",
            "uncertainty": "No per-cell sounding uncertainty is supplied. The 1 m spacing is not an accuracy claim.",
            "limitations": [
                "This demonstrates volume above an assumed design, not observed sludge thickness or accumulation.",
                "The source has already undergone hydrographic processing and cell averaging; this demo does not validate raw sonar corrections or the ECHO reconstruction.",
                "RWS marks these data as unsuitable for navigation.",
                "A TIN through cell centres covers a slightly smaller area than the original pixel-edge footprint. Compare integrations only over the same accepted support and grid.",
                "WCS range-type unit labels can be generic raster defaults; the official dataset metadata explicitly establishes metres NAP.",
            ],
            "files_sha256": {p.name: sha256(p) for p in [raw, source_xml, describe_xml, current, reference, directory / "demo_boundary.geojson"]},
        },
    }
    old_metadata.write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n")
    print(f"Wrote {len(points):,} genuine source-cell points and the assumed design reference to {directory}")
    print(f"Source bed elevations: {grid['z_min_m']} to {grid['z_max_m']} m NAP")


if __name__ == "__main__":
    main()
