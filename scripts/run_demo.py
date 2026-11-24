#!/usr/bin/env python3
"""Reproduce the real-data calculation without running the web interface."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ease_volume.core import AnalysisConfig, analyze


def main():
    metadata = json.loads((ROOT / "data/demo_metadata.json").read_text())
    metadata["source_kind"] = "raster_cell_centres"
    config = AnalysisConfig.parse(dict(crs="EPSG:28992", vertical_datum="NAP", reference_elevation=-6.5,
                                      reference_note=metadata["reference_status"], cell_size=1.0, max_edge=2.5,
                                      filter_mode="flag", filter_k=4.5, filter_floor=0.25, neighbors=16))
    result = analyze(ROOT / "data/demo_current.csv", None, ROOT / "data/demo_boundary.geojson", config,
                     ROOT / "demo_output", metadata)
    # Independent exported-cell arithmetic checks the pipeline's reported totals.
    import csv
    import math
    with (ROOT / "demo_output/cells.csv").open() as f:
        cells = [r for r in csv.DictReader(f) if r["valid"] == "1"]
    positive = math.fsum(float(r["supported_area_m2"]) * max(0, float(r["difference_m"])) for r in cells)
    negative = math.fsum(float(r["supported_area_m2"]) * max(0, -float(r["difference_m"])) for r in cells)
    assert math.isclose(positive, result["summary"]["positive_volume_m3"], abs_tol=1e-8)
    assert math.isclose(negative, result["summary"]["negative_volume_m3"], abs_tol=1e-8)
    checks = {"exported_cells_positive_m3": positive, "exported_cells_negative_m3": negative,
              "export_integration_passed": True}
    result["verification"] = checks
    (ROOT / "demo_output/verification.json").write_text(json.dumps(checks, indent=2))
    print(json.dumps({"summary": result["summary"], "verification": checks}, indent=2))


if __name__ == "__main__":
    main()
