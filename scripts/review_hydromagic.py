#!/usr/bin/env python3
"""Diagnostic review of an explicitly paired Hydromagic 12 export and sounding.

This is not a native-sonar importer. The observed SND field mapping is checked
against every supplied XYZ row before a candidate subset is written. It needs
provider confirmation and never invents missing vertical corrections.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ease_volume.core import load_points

from ease_volume.hydromagic import review_pair


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("survey", type=Path, help="The matching processed PointZ ZIP or XYZ CSV")
    parser.add_argument("--sounding", type=Path, required=True)
    parser.add_argument("--crs", required=True)
    parser.add_argument("--vertical-datum", required=True, help="Provisional declaration, not independently verified")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = load_points(args.survey, args.crs, "elevation", args.vertical_datum)
    report, candidate, rows = review_pair(source.xyz, args.sounding)
    report["survey"] = {"filename": source.name, "sha256": source.sha256, "crs": args.crs,
                        "vertical_datum_declared": args.vertical_datum, "original_z_values_preserved": True}
    args.output.mkdir(parents=True, exist_ok=True)
    for name, points in [("original_export_xyz.csv", source.xyz), ("candidate_elevation_points.csv", source.xyz[candidate])]:
        np.savetxt(args.output / name, points, delimiter=",", header="x,y,z", comments="", fmt="%.17g")
    with (args.output / "row_review.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["source_row_1based", "recorded_utc", "x", "y", "export_z_unchanged", "observed_depth_field", "observed_correction_field", "review_status"])
        writer.writerows(rows)
    (args.output / "review.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
