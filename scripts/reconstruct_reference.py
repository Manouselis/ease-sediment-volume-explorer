#!/usr/bin/env python3
"""Build a standard wetted design for one straight reach and compare survey elevations."""
from __future__ import annotations

import argparse
from html import escape
import json
import math
from pathlib import Path
import sys

import numpy as np
import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ease_volume.core import deduplicate, load_points, make_surface
from ease_volume.hydromagic import review_pair
from ease_volume.design_profiles import CRS, DATUM, PROFILES, compare_points, reference_grid, straight_reach


def make_report(profile, water_level, reach, xyz, distance, offset, design, mesh, summary):
    fig = go.Figure()
    edge = profile.water_edge
    lateral = np.array([-edge, -profile.bed_edge, profile.bed_edge, edge])
    t, o = np.meshgrid([0, reach.length], lateral)
    fig.add_trace(go.Surface(
        x=t, y=o, z=profile.elevations(o, water_level), opacity=.54,
        name="Wetted design surface",
        colorscale=[[0, "#82b7b1"], [1, "#82b7b1"]], showscale=False, showlegend=True,
        hovertemplate="Design %{z:.2f} m NAP<extra></extra>",
    ))
    if mesh is not None:
        bed, triangles = mesh
        bed_station, bed_offset = reach.project(bed[:, :2])
        fig.add_trace(go.Mesh3d(
            x=bed_station, y=bed_offset, z=bed[:, 2], i=triangles[:, 0], j=triangles[:, 1],
            k=triangles[:, 2], name="Measured bed · bounded TIN", showlegend=True,
            color="#273d53", opacity=.8, hovertemplate="Bed %{z:.2f} m NAP<extra></extra>",
        ))
    fig.add_trace(go.Scatter3d(
        x=distance, y=offset, z=xyz[:, 2], mode="markers", name="Silt-top soundings",
        marker=dict(size=3, color="#23384d"), customdata=xyz[:, :2],
        hovertemplate="Elevation %{z:.2f} m NAP<br>RD %{customdata[0]:.2f}, %{customdata[1]:.2f}<extra></extra>",
    ))
    width = max(edge, float(np.abs(offset).max())) * 1.1
    z_min = min(water_level - profile.depth, float(xyz[:, 2].min())) - .1
    z_max = max(water_level, float(xyz[:, 2].max())) + .1
    x_min, x_max = min(0, float(distance.min())), max(reach.length, float(distance.max()))
    # Preserve coordinates and disclose display exaggeration relative to the along-reach axis.
    lateral_scale = max(1, .30 * (x_max - x_min) / (2 * width))
    vertical_scale = max(1, .30 * (x_max - x_min) / (z_max - z_min))
    fig.update_layout(
        height=485, margin=dict(l=0, r=0, t=12, b=0), legend=dict(orientation="h"),
        scene=dict(
            xaxis=dict(title="Along reach (m)", range=[x_min, x_max]),
            yaxis=dict(title="Offset (m)", range=[-width, width]),
            zaxis=dict(title="Elevation (m NAP)", range=[z_min, z_max]),
            aspectmode="manual",
            aspectratio=dict(x=1, y=lateral_scale * 2 * width / (x_max - x_min),
                             z=vertical_scale * (z_max - z_min) / (x_max - x_min)),
            camera=dict(eye=dict(x=.43, y=-1.02, z=.54)),
        ),
    )

    line = go.Figure()
    if summary["alignment"]["source"] == "fitted survey track":
        line.add_scatter(x=[0, reach.length], y=[water_level - profile.depth] * 2,
                         mode="lines", name="Design bed", line=dict(color="#367d76", dash="dash"))
    else:
        line.add_scatter(x=distance, y=design, mode="markers", name="Design at soundings",
                         marker=dict(size=4, color="#367d76"))
    line.add_scatter(x=distance, y=xyz[:, 2], mode="markers", name="Silt-top soundings",
                     marker=dict(size=4, color="#23384d"),
                     customdata=xyz[:, 2] - design,
                     hovertemplate="%{y:.2f} m NAP<br>Above design %{customdata:+.2f} m<extra></extra>")
    line.update_layout(height=325, margin=dict(l=75, r=25, t=8, b=55),
                       xaxis_title="Distance along reach (m)", yaxis_title="Elevation (m NAP)",
                       legend=dict(orientation="h", y=1.12))

    for chart in (fig, line):
        chart.update_layout(template="plotly_white", font=dict(color="#23384d", family="system-ui"))
    status = "Provisional comparison" if summary["provisional"] else "Declared design and survey"
    level_status = "" if summary["design_level_confirmed_by_operator"] else " (assumed)"
    if mesh is None:
        coverage = "Soundings are shown as points. A measured surface requires coverage across the canal."
    else:
        coverage = f"Measured bed mesh covers {summary['measured_mesh_area_m2']:.1f} m² of bounded survey area."
    return f"""<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>EASE · Canal design comparison</title>
<style>
body{{font:16px system-ui,sans-serif;color:#23384d;background:#f3f7f6;margin:0}}
main{{max-width:1150px;margin:auto;padding:28px 20px}} h1{{margin:.2rem 0}}
p{{max-width:78ch;line-height:1.5}} .chart{{background:white;border-radius:12px;padding:8px}}
</style>
<main><strong>EASE · {status}</strong><h1>{escape(summary['profile_code'])} canal design and survey</h1>
<p>Design water level {water_level:+.2f} m NAP{level_status} · Flat design bed {water_level - profile.depth:+.2f} m NAP ·
{len(xyz):,} soundings shown · {summary['survey']['withheld']:,} withheld by review</p>
<p>Alignment from {escape(summary['alignment']['source'])}. {coverage}</p>
<p>3D display scales relative to the along-reach axis are {lateral_scale:.1f}× across the canal and
{vertical_scale:.1f}× vertically. Hover for elevations and original RD coordinates.</p>
<div class="chart">{fig.to_html(full_html=False, include_plotlyjs=True, config={'displaylogo': False})}</div>
<h2>Elevation along the reach</h2>
<div class="chart">{line.to_html(full_html=False, include_plotlyjs=False, config={'displaylogo': False})}</div>
</main></html>"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("survey", type=Path, help="Processed PointZ ZIP or XYZ in RD New/NAP")
    parser.add_argument("--profile", required=True, type=str.upper, choices=PROFILES)
    parser.add_argument("--water-level-nap", required=True, type=float, help="Signed design water elevation in metres")
    parser.add_argument("--design-level-confirmed", action="store_true", help="Declare provider-confirmed design water level")
    heights = parser.add_mutually_exclusive_group(required=True)
    heights.add_argument("--verified-nap", action="store_true", help="Declare a provider-verified corrected elevation export")
    heights.add_argument("--sounding", type=Path, help="Matching processed Hydromagic SND file for diagnostic review")
    alignment = parser.add_mutually_exclusive_group(required=True)
    alignment.add_argument("--track-is-centreline", action="store_true", help="Fit a provisional straight line to centreline soundings")
    alignment.add_argument("--centreline", type=float, nargs=4, metavar=("X1", "Y1", "X2", "Y2"),
                           help="Design reach endpoints in RD New metres")
    parser.add_argument("--spacing", type=float, default=1.0, help="Maximum reference XYZ spacing in metres")
    parser.add_argument("--measured-max-edge", type=float, help="Generate a bounded bed TIN for a verified area survey")
    parser.add_argument("--output", type=Path, required=True, help="New output directory")
    args = parser.parse_args()

    try:
        if not math.isfinite(args.water_level_nap) or not math.isfinite(args.spacing) or args.spacing < .05:
            raise ValueError("Use a finite signed NAP water level and a reference spacing of at least 0.05 m.")
        if args.measured_max_edge is not None and (
            not .05 <= args.measured_max_edge <= 10_000 or not args.verified_nap or args.centreline is None
        ):
            raise ValueError("A measured mesh requires a max edge from 0.05 to 10,000 m, "
                             "verified NAP elevations, design endpoints and coverage across the canal.")
        if args.output.exists():
            raise ValueError("Choose a new output directory to avoid mixing runs.")
        profile = PROFILES[args.profile]
        source = load_points(args.survey, CRS, "elevation", DATUM)
        if source.native_raster is not None:
            raise ValueError("Use a PointZ ZIP or XYZ point export for this workflow.")
        diagnostic = None
        xyz = source.xyz
        if args.sounding:
            diagnostic, use, _ = review_pair(xyz, args.sounding)
            xyz = xyz[use]
        if len(xyz) == 0:
            raise ValueError("The matched survey contains no soundings with a height correction.")
        reach = straight_reach(source.xyz[:, :2], args.centreline, profile)
        reference = reference_grid(reach, profile, args.water_level_nap, args.spacing)
        station, offset, design = compare_points(
            reach, profile, args.water_level_nap, xyz, args.track_is_centreline,
        )
        valid = np.isfinite(design)
        if not valid.any():
            raise ValueError("The accepted soundings do not overlap the supplied design reach.")
        mesh, mesh_area = None, None
        if args.measured_max_edge is not None:
            bed, _ = deduplicate(xyz[valid])
            surface = make_surface(source, bed, args.measured_max_edge)
            mesh = (bed, surface.triangulation.simplices[surface.allowed])
            mesh_area = surface.footprint.area
        summary = {
            "profile_code": args.profile, "profile_source": "Zuiderzeeland W-A-AL-001 rev C, sheet 1",
            "bed_width_m": profile.bed_width, "depth_m": profile.depth,
            "slope_horizontal_per_vertical": profile.run_per_rise, "waterline_width_m": 2 * profile.water_edge,
            "design_water_level_m_nap": args.water_level_nap,
            "design_bed_m_nap": args.water_level_nap - profile.depth,
            "design_level_confirmed_by_operator": args.design_level_confirmed,
            "crs": CRS, "vertical_datum": DATUM, "reference_xyz_points": len(reference),
            "max_reference_spacing_m": args.spacing,
            "alignment": {
                "source": "fitted survey track" if args.track_is_centreline else "operator-supplied design endpoints",
                "start_xy": reach.start.tolist(), "end_xy": (reach.start + reach.length * reach.direction).tolist(),
                "length_m": reach.length, "max_survey_offset_m": float(np.abs(offset).max()),
                "comparison": "flat bed" if args.track_is_centreline else "design at each sounding offset",
            },
            "survey": {"file": source.name, "sha256": source.sha256, "points": len(source.xyz),
                       "compared": int(valid.sum()), "outside_design": int((~valid).sum()),
                       "withheld": len(source.xyz) - len(xyz), "operator_verified_nap": args.verified_nap,
                       "height_review": diagnostic},
            "provisional": bool(args.track_is_centreline or not args.verified_nap or not args.design_level_confirmed),
            "measured_mesh_max_edge_m": args.measured_max_edge, "measured_mesh_area_m2": mesh_area,
        }
        report = make_report(profile, args.water_level_nap, reach, xyz, station, offset, design, mesh, summary)
        args.output.mkdir(parents=True)
        np.savetxt(args.output / "reference_xyz.csv", reference, delimiter=",", header="x,y,z", comments="", fmt="%.17g")
        np.savetxt(args.output / "comparison.csv", np.column_stack((xyz, station, offset, design, xyz[:, 2] - design)),
                   delimiter=",", comments="", fmt="%.17g",
                   header="x,y,silt_top_m_nap,distance_m,offset_m,design_m_nap,above_design_m")
        (args.output / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
        (args.output / "comparison.html").write_text(report, encoding="utf-8")
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Error: {exc}\n")
    print(f"{int(valid.sum()):,} soundings compared with {args.profile}. Open {args.output / 'comparison.html'}.")


if __name__ == "__main__":
    main()
