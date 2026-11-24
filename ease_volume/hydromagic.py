"""Diagnostic for a matching Hydromagic 12 SND and PointZ/XYZ export."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path

import numpy as np


SCHEMA_BASIS = ("Diagnostic SND layout observed in a matching Hydromagic 12.0 sounding/export pair. "
                "Not an authoritative general sounding-file specification. Provider confirmation required.")


def review_pair(xyz: np.ndarray, sounding: Path) -> tuple[dict, np.ndarray, list[list]]:
    if sounding.stat().st_size > 25 * 1024 * 1024:
        raise ValueError("Sounding exceeds review size limit")
    lines = [line.split() for line in sounding.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    versions = [row[1] for row in lines if row[0] == "VER" and len(row) == 2]
    nodata = [row[1] for row in lines if row[0] == "NDT" and len(row) == 2]
    records = [row for row in lines if row[0] == "SND"]
    if versions != ["12.0"] or len(nodata) != 1 or any(len(row) != 24 for row in records):
        raise ValueError("This diagnostic only supports the observed 24-token VER 12.0 SND layout")
    if not records or len(records) != len(xyz):
        raise ValueError("Sounding and exported point counts differ. Select the matching processed revision")
    # Numeric relationship inferred from this pair: XY at tokens 2/3, depth at 4,
    # a datum-height correction at 13. Token indices include the SND identifier.
    values = np.array([[float(row[j]) for j in [1, 2, 3, 4, 13]] for row in records])
    if xyz.shape != (len(records), 3) or not np.isfinite(values).all() or not np.isfinite(xyz).all():
        raise ValueError("Non-finite values or incompatible coordinate shape")
    no_data = float(nodata[0])
    if not np.isfinite(no_data):
        raise ValueError("Invalid NDT marker")
    tolerance = .0011  # Two rounded three-decimal operands versus full-precision SHP Z.
    xy_error = float(np.abs(values[:, 1:3] - xyz[:, :2]).max())
    if xy_error > tolerance:
        raise ValueError("Sounding and export are not in matching row/coordinate order")
    correction_present = values[:, 4] != no_data
    expected = np.where(correction_present, values[:, 4] - values[:, 3], values[:, 3])
    z_error = float(np.abs(expected - xyz[:, 2]).max())
    if z_error > tolerance:
        raise ValueError("The observed correction/depth field mapping does not explain this export")
    reasons = np.where(correction_present, "correction_present_candidate_for_review", "missing_correction_export_matches_depth")
    rows = [[i+1, datetime.fromtimestamp(v[0], timezone.utc).isoformat(), *p, v[3],
             v[4] if use else "", str(reason)]
            for i, (v, p, use, reason) in enumerate(zip(values, xyz, correction_present, reasons))]
    report = {
        "schema_basis": SCHEMA_BASIS,
        "point_count": len(xyz), "candidate_count": int(correction_present.sum()),
        "withheld_missing_correction_count": int((~correction_present).sum()),
        "positive_z_count": int((xyz[:, 2] > 0).sum()),
        "positive_z_with_missing_correction": int(((xyz[:, 2] > 0) & ~correction_present).sum()),
        "xy_pair_max_error_m": xy_error, "z_relationship_max_error_m": z_error,
        "comparison_tolerance_m": tolerance,
        "recorded_start_utc": datetime.fromtimestamp(values[:, 0].min(), timezone.utc).isoformat(),
        "recorded_end_utc": datetime.fromtimestamp(values[:, 0].max(), timezone.utc).isoformat(),
        "withholding_rule": "Withhold rows with the observed height-correction field equal to NDT. Not a positive-Z or outlier threshold.",
        "candidate_status": "Review only. Does not establish datum, sonar accuracy, RTK validity, coverage or sludge thickness.",
        "sounding": {"filename": sounding.name, "sha256": hashlib.sha256(sounding.read_bytes()).hexdigest()},
    }
    return report, correction_present, rows
