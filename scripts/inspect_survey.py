#!/usr/bin/env python3
"""Inspect private processed survey data and export lossless, app-ready XYZ."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ease_volume.core import AnalysisConfig, inspect_survey, load_points, points_in_bounds


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("survey", type=Path)
    parser.add_argument("--crs", required=True)
    parser.add_argument("--vertical-datum", required=True, help="A declaration to confirm from the survey record, not inferred from .prj")
    parser.add_argument("--z-convention", choices=["elevation", "depth"], default="elevation")
    parser.add_argument("--bounds", type=float, nargs=4, metavar=("XMIN", "YMIN", "XMAX", "YMAX"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.bounds:
        AnalysisConfig.parse({"analysis_bounds": args.bounds, "reference_note": "Input validation only, no volume calculation"})
    report = inspect_survey(args.survey, args.crs, args.z_convention, args.vertical_datum)
    source = load_points(args.survey, args.crs, args.z_convention, args.vertical_datum)
    selected = points_in_bounds(source.xyz, args.bounds)
    report["source_filename"] = args.survey.name
    report["export"] = {"filename": "survey_xyz.csv", "point_count": len(selected), "analysis_bounds": args.bounds,
                        "z_convention": "elevation_positive_up", "precision": "17 significant digits, float64 round trip"}
    # Coordinates are already included in the XYZ. Keep the report small and human-readable.
    del report["points"]
    args.output.mkdir(parents=True, exist_ok=True)
    np.savetxt(args.output / "survey_xyz.csv", selected, delimiter=",", header="x,y,z", comments="", fmt="%.17g")
    (args.output / "inspection.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"points": len(selected), "source_kind": source.source_kind, "output": str(args.output)}))


if __name__ == "__main__":
    main()
