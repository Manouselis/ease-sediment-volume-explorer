"""Numerical pipeline. Inputs must already be corrected bathymetric elevations.

GeoUtils supplies georeferenced masked rasters, alignment, arithmetic and exports.
SciPy supplies Qhull Delaunay triangulation and indexed neighbourhood searches.
This module never interprets raw sonar or silently transforms vertical datums.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import geoutils as gu
import numpy as np
import rasterio
import shapely
from affine import Affine
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pyproj import CRS, Transformer
from scipy.interpolate import LinearNDInterpolator
from scipy.spatial import Delaunay, QhullError, cKDTree
from shapely.geometry import box, shape
from shapely.ops import transform as geometry_transform

from .design_profiles import (CRS as DESIGN_CRS, DATUM as DESIGN_DATUM, DesignReference, DesignSettings,
                              PROFILES, reference_grid, straight_reach)
from .hydromagic import review_pair
from .vector import VectorInputError, read_pointz_zip

MAX_POINTS = 100_000
MAX_CELLS = 500_000
MIB = 1024 * 1024
MAX_SURVEY_MB = 100
MAX_UPLOAD_MB = 25


class AnalysisError(ValueError):
    def __init__(self, code: str, **params):
        self.code, self.params = code, params
        super().__init__(code)


class AnalysisConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    crs: str = "EPSG:28992"
    vertical_datum: str = "NAP"
    units: str = "m"
    z_convention: Literal["elevation", "depth"] = "elevation"
    survey_nap_confirmed: bool = False
    reference_type: Literal["design", "previous", "underside"] = "design"
    reference_mode: Literal["constant", "file", "profile"] = "constant"
    design_profile: DesignSettings | None = None
    reference_elevation: float = -6.5
    reference_crs: str = "EPSG:28992"
    reference_vertical_datum: str = "NAP"
    reference_units: str = "m"
    reference_z_convention: Literal["elevation", "depth"] = "elevation"
    reference_note: str = Field(default="", max_length=1000)
    cell_size: float = Field(default=1.0, ge=0.05, le=1000)
    max_edge: float = Field(default=3.0, ge=0.05, le=10_000)
    surface_method: Literal["tin", "kriging"] = "tin"
    kriging_model: Literal["spherical", "exponential", "gaussian"] = "spherical"
    kriging_fit: Literal["auto", "manual"] = "auto"
    kriging_nugget: float = Field(default=0.005, ge=0, le=10000)
    kriging_partial_sill: float = Field(default=0.2, gt=0, le=10000)
    kriging_range: float = Field(default=20, gt=0, le=100000)
    kriging_neighbors: int = Field(default=16, ge=3, le=64)
    kriging_radius: float = Field(default=20, gt=0, le=10000)
    kriging_max_se: float | None = Field(default=None, ge=0, le=100)
    filter_mode: Literal["off", "flag", "exclude"] = "flag"
    filter_k: float = Field(default=4.5, ge=2, le=20)
    filter_floor: float = Field(default=0.25, ge=0.001, le=100)
    neighbors: int = Field(default=16, ge=6, le=64)
    sigma_current: float | None = Field(default=None, ge=0, le=100)
    sigma_reference: float | None = Field(default=None, ge=0, le=100)
    analysis_bounds: tuple[float, float, float, float] | None = None

    @classmethod
    def parse(cls, value: dict) -> "AnalysisConfig":
        try:
            config = cls.model_validate(value)
        except ValidationError as exc:
            raise AnalysisError("invalid_config", fields=[".".join(map(str, e["loc"])) for e in exc.errors()]) from exc
        validate_crs(config.crs)
        if config.units != "m" or config.reference_units != "m":
            raise AnalysisError("units_not_meters")
        if canonical_datum(config.vertical_datum) in {"", "UNKNOWN", "UNSPECIFIED"} or canonical_datum(config.reference_vertical_datum) in {"", "UNKNOWN", "UNSPECIFIED"}:
            raise AnalysisError("missing_vertical_datum")
        if not config.reference_note.strip():
            raise AnalysisError("invalid_reference", field="reference_note")
        if config.reference_mode in {"constant", "profile"} and config.reference_type != "design":
            raise AnalysisError("invalid_reference", field="reference_mode")
        if config.reference_mode == "profile":
            if config.design_profile is None:
                raise AnalysisError("invalid_config", fields=["design_profile"])
            if (not validate_crs(config.crs).equals(validate_crs(DESIGN_CRS)) or
                    canonical_datum(config.vertical_datum) != DESIGN_DATUM or config.z_convention != "elevation"):
                raise AnalysisError("profile_coordinates")
            if config.design_profile.coverage == "area" and config.design_profile.endpoints is None:
                raise AnalysisError("profile_endpoints")
        if config.reference_mode == "file":
            if not validate_crs(config.crs).equals(validate_crs(config.reference_crs)):
                raise AnalysisError("crs_mismatch")
            if canonical_datum(config.vertical_datum) != canonical_datum(config.reference_vertical_datum):
                raise AnalysisError("datum_mismatch")
        if (config.sigma_current is None) != (config.sigma_reference is None):
            raise AnalysisError("invalid_config", fields=["sigma_current", "sigma_reference"])
        if config.analysis_bounds is not None:
            left, bottom, right, top = config.analysis_bounds
            if not (left < right and bottom < top):
                raise AnalysisError("invalid_config", fields=["analysis_bounds"])
        return config


def canonical_datum(value: str) -> str:
    normalized = value.strip().upper().replace(" ", "")
    return "NAP" if normalized in {"NAP", "EPSG:5709", "5709"} else normalized


def validate_crs(value: str) -> CRS:
    try:
        crs = CRS.from_user_input(value)
    except Exception as exc:
        raise AnalysisError("invalid_crs") from exc
    if not crs.is_projected:
        raise AnalysisError("geographic_crs")
    if len(crs.axis_info) < 2 or any(abs(a.unit_conversion_factor - 1.0) > 1e-10 for a in crs.axis_info[:2]):
        raise AnalysisError("units_not_meters")
    return crs


@dataclass
class Points:
    xyz: np.ndarray
    source_kind: str
    sha256: str
    name: str
    native_raster: gu.Raster | None = None
    metadata: dict | None = None


def load_points(path: Path, crs: str, z_convention: str = "elevation", vertical_datum: str | None = None,
                *, limit_mb: int = MAX_SURVEY_MB) -> Points:
    if path.stat().st_size > limit_mb * MIB:
        raise AnalysisError("file_too_large", limit_mb=limit_mb)
    suffix = path.suffix.lower()
    raster = None
    metadata = None
    if suffix in {".tif", ".tiff"}:
        try:
            with rasterio.open(path) as dataset:
                tags = dataset.tags()
                declared_vertical = tags.get("vertical_datum")
                if declared_vertical and vertical_datum and canonical_datum(declared_vertical) != canonical_datum(vertical_datum):
                    raise AnalysisError("datum_mismatch")
                if any(unit and unit.lower() not in {"m", "meter", "meters", "metre", "metres"} for unit in dataset.units):
                    raise AnalysisError("units_not_meters")
                if tags.get("units", "m").lower() not in {"m", "meter", "meters", "metre", "metres"}:
                    raise AnalysisError("units_not_meters")
                declared_sign = tags.get("z_convention", "").strip().lower()
                expected_signs = ({"elevation", "elevation_positive_up"} if z_convention == "elevation"
                                  else {"depth", "depth_positive_down"})
                if declared_sign and declared_sign not in expected_signs:
                    raise AnalysisError("raster_metadata", field="z_convention")
                # Inspect dimensions before loading a potentially compressed huge file.
                if dataset.height * dataset.width > MAX_CELLS:
                    raise AnalysisError("grid_too_large", limit=MAX_CELLS)
            raster = gu.Raster(str(path))
            if raster.crs is None or not CRS(raster.crs).equals(validate_crs(crs)):
                raise AnalysisError("crs_mismatch")
            if raster.count != 1:
                raise AnalysisError("raster_metadata", field="single_band")
            if raster.height * raster.width > MAX_CELLS:
                raise AnalysisError("grid_too_large", limit=MAX_CELLS)
            data = np.ma.masked_invalid(raster.data).squeeze()
            rows, cols = np.where(~np.ma.getmaskarray(data))
            x, y = rasterio.transform.xy(raster.transform, rows, cols)
            xyz = np.column_stack((x, y, np.asarray(data)[rows, cols]))
        except AnalysisError:
            raise
        except Exception as exc:
            raise AnalysisError("raster_metadata") from exc
        kind = "raster_cell_centres"
    elif suffix == ".zip":
        try:
            xyz, metadata = read_pointz_zip(path, validate_crs(crs), MAX_POINTS)
        except VectorInputError as exc:
            raise AnalysisError(exc.code, **exc.params) from exc
        kind = "shapefile_pointz"
    elif suffix in {".csv", ".txt", ".xyz"}:
        try:
            with path.open(encoding="utf-8-sig", newline="") as stream:
                lines = (line for line in stream if line.strip() and not line.lstrip().startswith("#"))
                first = next(lines, None)
                if first is None:
                    raise AnalysisError("invalid_csv")
                delimiter = "," if "," in first else (";" if ";" in first else ("\t" if "\t" in first else None))
                fields = next(csv.reader([first], delimiter=delimiter)) if delimiter else first.split()
                rows = csv.reader(lines, delimiter=delimiter) if delimiter else (line.split() for line in lines)
                aliases = {"x": {"x", "easting", "east"}, "y": {"y", "northing", "north"}, "z": {"z", "elevation", "height", "depth"}}
                header = [v.strip().lower() for v in fields]
                indices = []
                for key in ("x", "y", "z"):
                    matches = [i for i, v in enumerate(header) if v in aliases[key]]
                    if len(matches) != 1:
                        raise AnalysisError("missing_columns", columns="x, y, z")
                    indices.append(matches[0])
                points = []
                for row in rows:
                    if len(points) == MAX_POINTS:
                        raise AnalysisError("too_many_points", limit=MAX_POINTS)
                    points.append([float(row[i]) for i in indices])
                xyz = np.asarray(points, dtype=float)
        except AnalysisError:
            raise
        except (UnicodeError, ValueError, IndexError, csv.Error) as exc:
            raise AnalysisError("invalid_csv") from exc
        kind = "xyz_points"
    else:
        raise AnalysisError("unsupported_format")
    if len(xyz) > MAX_POINTS:
        raise AnalysisError("too_many_points", limit=MAX_POINTS)
    if xyz.ndim != 2 or xyz.shape[1] != 3 or len(xyz) < 3:
        raise AnalysisError("too_few_points")
    if not np.isfinite(xyz).all():
        raise AnalysisError("invalid_values")
    if z_convention == "depth":
        xyz[:, 2] *= -1
        if raster is not None:
            raster = raster.copy(new_array=-raster.data)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(MIB), b""):
            digest.update(chunk)
    return Points(xyz, kind, digest.hexdigest(), path.name, raster, metadata)


def screen_survey_heights(source: Points, sounding_path: Path | None, crs: str,
                          z_convention: str, vertical_datum: str) -> tuple[np.ndarray, dict | None]:
    if sounding_path is None:
        return np.ones(len(source.xyz), dtype=bool), None
    if (source.native_raster is not None or not validate_crs(crs).equals(validate_crs(DESIGN_CRS))
            or z_convention != "elevation" or canonical_datum(vertical_datum) != DESIGN_DATUM):
        raise AnalysisError("preprocess_coordinates")
    try:
        review, use, _ = review_pair(source.xyz, sounding_path)
    except (ValueError, OSError, OverflowError) as exc:
        raise AnalysisError("profile_sounding_mismatch") from exc
    if not use.any():
        raise AnalysisError("preprocess_no_points")
    return use, review


def inspect_survey(path: Path, crs: str, z_convention: str, vertical_datum: str,
                   sounding_path: Path | None = None) -> dict:
    """Inspect observations without constructing a surface or assuming a reference."""
    validate_crs(crs)
    if canonical_datum(vertical_datum) in {"", "UNKNOWN", "UNSPECIFIED"}:
        raise AnalysisError("missing_vertical_datum")
    if z_convention not in {"elevation", "depth"}:
        raise AnalysisError("invalid_config", fields=["z_convention"])
    source = load_points(path, crs, z_convention, vertical_datum)
    use, review = screen_survey_heights(source, sounding_path, crs, z_convention, vertical_datum)
    xyz = source.xyz[use] if review is not None else source.xyz
    unique, duplicates = deduplicate(xyz)
    distances = cKDTree(unique[:, :2]).query(unique[:, :2], k=2)[0][:, 1] if len(unique) > 1 else None
    bounds = [float(v) for v in [xyz[:, 0].min(), xyz[:, 1].min(), xyz[:, 0].max(), xyz[:, 1].max()]]
    stride = max(1, math.ceil(len(xyz) / 8000))
    # Retain extrema as well as a documented deterministic display sample.
    inds = np.unique(np.r_[np.arange(0, len(xyz), stride), np.argmin(xyz, axis=0), np.argmax(xyz, axis=0)])
    return {
        "filename": source.name, "sha256": source.sha256, "source_kind": source.source_kind,
        "point_count": len(xyz), "unique_xy_count": len(unique), "duplicate_xy_count": duplicates,
        "crs": validate_crs(crs).to_string(), "vertical_datum": vertical_datum,
        "vertical_datum_status": "user_declared; no independent verification",
        "bounds": bounds, "max_grid_cells": MAX_CELLS,
        "z_min_m": float(xyz[:, 2].min()), "z_max_m": float(xyz[:, 2].max()),
        "z_quantiles_m": dict(zip(["p01", "p50", "p99"], np.quantile(xyz[:, 2], [.01, .5, .99]).tolist())),
        "positive_z_count": int((xyz[:, 2] > 0).sum()),
        "nearest_neighbour_m": dict(zip(["p50", "p90", "p99", "max"], np.quantile(distances, [.5, .9, .99, 1]).tolist() if distances is not None else [None]*4)),
        "metadata": source.metadata, "height_review": review,
        "points": {"x": xyz[inds, 0].tolist(), "y": xyz[inds, 1].tolist(), "z": xyz[inds, 2].tolist(), "display_stride": stride},
    }


def points_in_bounds(xyz: np.ndarray, bounds: tuple | None) -> np.ndarray:
    if bounds is None:
        return xyz
    left, bottom, right, top = bounds
    return xyz[(xyz[:, 0] >= left) & (xyz[:, 0] <= right) & (xyz[:, 1] >= bottom) & (xyz[:, 1] <= top)]


def deduplicate(xyz: np.ndarray) -> tuple[np.ndarray, int]:
    xy, reverse, counts = np.unique(xyz[:, :2], axis=0, return_inverse=True, return_counts=True)
    if len(xy) == len(xyz):
        return xyz.copy(), 0
    # Sort once; use the median for each exact XY group without quadratic scans.
    order = np.argsort(reverse, kind="stable")
    values = np.split(xyz[order, 2], np.cumsum(counts)[:-1])
    return np.column_stack((xy, [np.median(v) for v in values])), int(len(xyz) - len(xy))


def robust_flags(xyz: np.ndarray, config: AnalysisConfig) -> np.ndarray:
    """Local slope-aware MAD flags, without changing any observed elevation.

    Leave-one-out neighbourhoods; bounded physical radius prevents distant
    opposite banks becoming neighbours. Iteratively trimmed local plane is
    a diagnostic trend, not a smoothed replacement bed.
    """
    flags = np.zeros(len(xyz), dtype=bool)
    if config.filter_mode == "off" or len(xyz) < 7:
        return flags
    tree = cKDTree(xyz[:, :2])
    k = min(config.neighbors + 1, len(xyz))
    distances, neighbours = tree.query(xyz[:, :2], k=k)
    for i in range(len(xyz)):
        inds = neighbours[i][(neighbours[i] != i) & (distances[i] <= config.max_edge * 2)]
        if len(inds) < 6:
            continue
        local = xyz[inds]
        design = np.column_stack((local[:, :2] - xyz[i, :2], np.ones(len(local))))
        if np.linalg.matrix_rank(design) < 3:
            continue
        keep = np.ones(len(local), dtype=bool)
        for _ in range(3):
            fit = np.linalg.lstsq(design[keep], local[keep, 2], rcond=None)[0]
            residuals = local[:, 2] - design @ fit
            median = np.median(residuals[keep])
            scale = 1.4826 * np.median(np.abs(residuals[keep] - median))
            new_keep = np.abs(residuals - median) <= max(config.filter_k * scale, config.filter_floor)
            if new_keep.sum() < 6 or np.array_equal(keep, new_keep) or np.linalg.matrix_rank(design[new_keep]) < 3:
                break
            keep = new_keep
        flags[i] = abs(xyz[i, 2] - fit[2] - median) > max(config.filter_k * scale, config.filter_floor)
    return flags


@dataclass
class Surface:
    triangulation: Delaunay
    interpolator: LinearNDInterpolator
    allowed: np.ndarray
    footprint: object
    source: Points

    def support(self, xy: np.ndarray) -> np.ndarray:
        simplex = self.triangulation.find_simplex(xy, tol=1e-10)
        valid = simplex >= 0
        valid[valid] &= self.allowed[simplex[valid]]
        if self.source.native_raster is not None:
            raster = self.source.native_raster
            cols, rows = (~raster.transform) * (xy[:, 0], xy[:, 1])
            rr, cc = np.floor(rows).astype(int), np.floor(cols).astype(int)
            inside = (rr >= 0) & (rr < raster.height) & (cc >= 0) & (cc < raster.width)
            original = np.zeros(len(xy), bool)
            mask = np.ma.getmaskarray(np.ma.masked_invalid(raster.data)).squeeze()
            original[inside] = ~mask[rr[inside], cc[inside]]
            valid &= original
        return valid

    def sample(self, xy: np.ndarray) -> np.ndarray:
        valid = self.support(xy)
        result = np.full(len(xy), np.nan)
        result[valid] = self.interpolator(xy[valid])
        return result


def make_surface(points: Points, xyz: np.ndarray, max_edge: float) -> Surface:
    try:
        triangulation = Delaunay(xyz[:, :2])
    except (QhullError, ValueError) as exc:
        raise AnalysisError("degenerate_points") from exc
    vertices = xyz[triangulation.simplices, :2]
    lengths = np.linalg.norm(vertices - np.roll(vertices, 1, axis=1), axis=2)
    allowed = np.max(lengths, axis=1) <= max_edge + 1e-10
    if not allowed.any():
        raise AnalysisError("insufficient_coverage")
    footprint = shapely.union_all(shapely.polygons(vertices[allowed]))
    if points.native_raster is not None:
        # Preserve explicit raster NoData holes as geometry as well as samples.
        from rasterio.features import shapes
        raster = points.native_raster
        native_valid = ~np.ma.getmaskarray(np.ma.masked_invalid(raster.data)).squeeze()
        if not native_valid.all():
            polygons = [shape(geometry) for geometry, value in shapes(native_valid.astype("uint8"), mask=native_valid, transform=raster.transform) if value == 1]
            footprint = footprint.intersection(shapely.union_all(polygons))
    return Surface(triangulation, LinearNDInterpolator(triangulation, xyz[:, 2]), allowed, footprint, points)


def load_boundary(path: Path | None, target_crs: str):
    if path is None:
        return None
    try:
        obj = json.loads(path.read_text())
        if obj.get("type") == "FeatureCollection":
            geometry = shapely.union_all([shape(f["geometry"]) for f in obj["features"]])
        elif obj.get("type") == "Feature":
            geometry = shape(obj["geometry"])
        else:
            geometry = shape(obj)
        if geometry.geom_type not in {"Polygon", "MultiPolygon"} or geometry.is_empty or not geometry.is_valid:
            raise ValueError("polygon")
        source_crs = obj.get("crs", {}).get("properties", {}).get("name", "EPSG:4326")
        source = CRS.from_user_input(source_crs)
        if not source.equals(CRS(target_crs)):
            transformer = Transformer.from_crs(source, target_crs, always_xy=True)
            geometry = geometry_transform(transformer.transform, geometry)
        if geometry.is_empty or not np.isfinite(geometry.bounds).all():
            raise ValueError("bounds")
        return geometry
    except Exception as exc:
        raise AnalysisError("invalid_boundary") from exc


def raster_from_values(values: np.ndarray, transform: Affine, crs: str) -> gu.Raster:
    return gu.Raster.from_array(np.ma.masked_invalid(values.astype(np.float64)), transform=transform,
                               crs=CRS(crs), nodata=-9999.0, area_or_point="Area")


def compare_design_profile(source: Points, config: AnalysisConfig, boundary_path: Path | None,
                           use: np.ndarray, review: dict | None, output_dir: Path) -> tuple[DesignReference, dict]:
    settings = config.design_profile
    if settings is None:
        raise AnalysisError("invalid_config", fields=["design_profile"])
    if source.native_raster is not None:
        raise AnalysisError("profile_points_required")
    if settings.coverage == "area" and settings.endpoints is None:
        raise AnalysisError("profile_area_requirements")
    if not settings.survey_nap_confirmed and review is None:
        raise AnalysisError("profile_heights_required")

    withheld = int((~use).sum())

    selected = np.ones(len(source.xyz), dtype=bool)
    if config.analysis_bounds is not None:
        left, bottom, right, top = config.analysis_bounds
        selected &= ((source.xyz[:, 0] >= left) & (source.xyz[:, 0] <= right)
                     & (source.xyz[:, 1] >= bottom) & (source.xyz[:, 1] <= top))
    boundary = load_boundary(boundary_path, config.crs) if settings.coverage == "track" else None
    if boundary is not None:
        selected &= shapely.intersects_xy(boundary, source.xyz[:, 0], source.xyz[:, 1])
    if not (selected & use).any() or (settings.endpoints is None and selected.sum() < 3):
        raise AnalysisError("too_few_points")
    xyz = source.xyz[selected & use]
    profile = PROFILES[settings.code]
    try:
        reach = straight_reach(source.xyz[selected, :2], settings.endpoints, profile)
    except (ValueError, np.linalg.LinAlgError) as exc:
        raise AnalysisError("profile_alignment") from exc
    design = DesignReference(settings, reach)
    distance, offset, design_z = design.compare(xyz)
    inside = np.isfinite(design_z)
    if not inside.any():
        raise AnalysisError("profile_overlap")
    try:
        reference = reference_grid(reach, profile, design.water_level, 1, max_points=MAX_POINTS)
    except (ValueError, OverflowError) as exc:
        raise AnalysisError("profile_export_limit") from exc

    output_dir.mkdir(parents=True, exist_ok=True)
    np.savetxt(output_dir / "reference_xyz.csv", reference, delimiter=",", header="x,y,z",
               comments="", fmt="%.17g")
    with (output_dir / "comparison.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["x", "y", "z_nap_m", "station_m", "offset_m", "design_nap_m", "above_design_m"])
        for point, t, o, z in zip(xyz, distance, offset, design_z):
            writer.writerow([*point, t, o, z, point[2] - z] if np.isfinite(z) else [*point, t, o, "", ""])

    metadata = design.metadata()
    metadata["provisional"] |= review is not None
    metadata.update(
        input_count=len(source.xyz), compared_count=int(inside.sum()), withheld_count=withheld,
        outside_design_count=int((~inside).sum()), outside_selection_count=int((~selected & use).sum()),
        survey_sha256=source.sha256, survey_source=source.name, height_review=review,
    )
    stride = max(1, math.ceil(inside.sum() / 8000))
    displayed = np.flatnonzero(inside)[::stride]
    edges = np.array([-profile.water_edge, -profile.bed_edge, profile.bed_edge, profile.water_edge])
    return design, {
        "metadata": metadata,
        "geometry": {"station": [0, reach.length], "offset": edges.tolist(),
                     "elevation": profile.elevations(edges, design.water_level).tolist()},
        "points": dict(zip(("x", "y", "z", "station", "offset", "design"),
                           np.column_stack((xyz, distance, offset, design_z))[displayed].T.tolist())),
    }


def analyze(survey_path: Path, reference_path: Path | None, boundary_path: Path | None,
            config: AnalysisConfig, output_dir: Path, source_metadata: dict | None = None,
            sounding_path: Path | None = None) -> dict:
    if config.reference_mode == "profile" and survey_path.suffix.lower() not in {".zip", ".csv", ".txt", ".xyz"}:
        raise AnalysisError("profile_points_required")
    source = load_points(survey_path, config.crs, config.z_convention, config.vertical_datum)
    use, review = screen_survey_heights(source, sounding_path, config.crs, config.z_convention, config.vertical_datum)
    profile = config.design_profile if config.reference_mode == "profile" else None
    track = profile is not None and profile.coverage == "track"
    confirmed = profile.survey_nap_confirmed if profile is not None else config.survey_nap_confirmed
    if review is not None and not track and not confirmed:
        raise AnalysisError("preprocess_volume_heights")
    design = profile_comparison = None
    if config.reference_mode == "profile":
        design, profile_comparison = compare_design_profile(source, config, boundary_path, use, review, output_dir)
        if design.settings.coverage == "track":
            (output_dir / "summary.json").write_text(json.dumps({
                "design_profile": profile_comparison["metadata"], "configuration": config.model_dump(),
            }, indent=2) + "\n")
            return {"profile": profile_comparison}
    retained = source.xyz[use] if review is not None else source.xyz
    selected = points_in_bounds(retained, config.analysis_bounds)
    if len(selected) < 3:
        raise AnalysisError("too_few_points")
    unique, duplicate_count = deduplicate(selected)
    flags = robust_flags(unique, config)
    accepted = unique[~flags] if config.filter_mode == "exclude" else unique
    if len(accepted) < 3:
        raise AnalysisError("too_few_points")
    bed_surface = make_surface(source, accepted, config.max_edge)
    requested_boundary = load_boundary(boundary_path, config.crs)
    if config.analysis_bounds is not None:
        selection_box = box(*config.analysis_bounds)
        requested_boundary = (selection_box if requested_boundary is None else requested_boundary.intersection(selection_box))
        if requested_boundary.is_empty or requested_boundary.area <= 0:
            raise AnalysisError("insufficient_coverage")
    footprint = bed_surface.footprint
    reference_source = None
    reference_surface = None
    if config.reference_mode == "file":
        if reference_path is None:
            raise AnalysisError("invalid_reference")
        reference_source = load_points(reference_path, config.reference_crs, config.reference_z_convention,
                                       config.reference_vertical_datum, limit_mb=MAX_UPLOAD_MB)
        ref_xyz, _ = deduplicate(points_in_bounds(reference_source.xyz, config.analysis_bounds))
        if len(ref_xyz) < 3:
            raise AnalysisError("too_few_points")
        reference_surface = make_surface(reference_source, ref_xyz, config.max_edge)
        footprint = footprint.intersection(reference_surface.footprint)
    if design is not None:
        design_boundary = design.footprint
        requested_boundary = (design_boundary if requested_boundary is None
                              else design_boundary.intersection(requested_boundary))
    if requested_boundary is not None:
        footprint = footprint.intersection(requested_boundary)
    if footprint.is_empty or footprint.area <= 0:
        raise AnalysisError("insufficient_coverage")
    # One common grid, snapped to the declared metric CRS origin.
    cell = config.cell_size
    bounds = requested_boundary.bounds if requested_boundary is not None else bed_surface.footprint.bounds
    left, bottom = math.floor(bounds[0] / cell) * cell, math.floor(bounds[1] / cell) * cell
    right, top = math.ceil(bounds[2] / cell) * cell, math.ceil(bounds[3] / cell) * cell
    width, height = max(1, round((right-left)/cell)), max(1, round((top-bottom)/cell))
    if width * height > MAX_CELLS:
        raise AnalysisError("grid_too_large", limit=MAX_CELLS)
    x = left + (np.arange(width) + 0.5) * cell
    y = top - (np.arange(height) + 0.5) * cell
    xx, yy = np.meshgrid(x, y)
    xy = np.column_stack((xx.ravel(), yy.ravel()))
    cells = shapely.box(xy[:, 0]-cell/2, xy[:, 1]-cell/2, xy[:, 0]+cell/2, xy[:, 1]+cell/2)
    clipped_cells = shapely.intersection(cells, footprint)
    areas = shapely.area(clipped_cells)
    supported = areas > 1e-12
    # Include partial cells even when their nominal centre is outside coverage.
    # The area centroid makes this quadrature exact for an affine surface on a
    # connected clipped cell. For a concave/disconnected fragment whose centroid
    # is unsupported, use an interior representative point and retain a warning.
    sample_xy = xy.copy()
    partial = supported & (areas < cell*cell - 1e-9)
    centres = shapely.centroid(clipped_cells[partial])
    inside = shapely.covers(clipped_cells[partial], centres)
    centres[~inside] = shapely.point_on_surface(clipped_cells[partial][~inside])
    sample_xy[partial] = shapely.get_coordinates(centres)
    method_details = {"bed": {"method": "linear_tin"}, "reference": {"method": "linear_tin" if reference_surface else "constant"}}
    if design is not None:
        method_details["reference"] = design.metadata()
    bed_variance = reference_variance = np.full(len(xy), np.nan)
    reasons = np.where(supported, "accepted", "outside_support").astype(object)
    if config.surface_method == "kriging":
        from .kriging import KrigingSurface
        predictor = KrigingSurface(bed_surface, accepted, config)
        # Sample only common geometrically supported locations, including partial-cell centroids.
        query = sample_xy[supported]
        values, errors, bed_reasons = predictor.sample(query)
        bed, bed_variance = np.full(len(xy), np.nan), np.full(len(xy), np.nan)
        bed[supported], bed_variance[supported], reasons[supported] = values, errors, bed_reasons
        method_details["bed"] = predictor.metadata
        reference = np.full(len(xy), config.reference_elevation)
        if reference_surface:
            predictor = KrigingSurface(reference_surface, ref_xyz, config)
            values, errors, ref_reasons = predictor.sample(query)
            reference, reference_variance = np.full(len(xy), np.nan), np.full(len(xy), np.nan)
            reference[supported], reference_variance[supported] = values, errors
            missing = supported.copy()
            missing[supported] = (ref_reasons != "accepted") & (reasons[supported] == "accepted")
            reasons[missing] = "reference_insufficient_neighbors"
            method_details["reference"] = predictor.metadata
        if config.kriging_max_se is not None:
            high = supported & ((bed_variance > config.kriging_max_se**2) |
                                (reference_variance > config.kriging_max_se**2))
            reasons[high] = "uncertainty_threshold"
    else:
        bed = bed_surface.sample(sample_xy)
        reference = (reference_surface.sample(sample_xy) if reference_surface else np.full(len(xy), config.reference_elevation))
    if design is not None:
        reference[supported] = design.sample(sample_xy[supported])
    valid = supported & np.isfinite(bed) & np.isfinite(reference) & (reasons == "accepted")
    exclusion_areas = {reason: float(areas[reasons == reason].sum())
                       for reason in np.unique(reasons) if reason not in {"accepted", "outside_support"}}
    geometric_area = float(areas.sum())
    geometric_areas = areas.copy()
    areas[~valid] = 0
    if not valid.any():
        raise AnalysisError("kriging_no_predictions" if config.surface_method == "kriging" else "insufficient_coverage", excluded_area_m2=geometric_area, reasons=exclusion_areas)
    bed[~valid] = reference[~valid] = np.nan
    bed, reference, areas, valid = [v.reshape(height, width) for v in (bed, reference, areas, valid)]
    transform = Affine(cell, 0, left, 0, -cell, top)
    bed_raster = raster_from_values(bed, transform, config.crs)
    reference_raster = raster_from_values(reference, transform, config.crs)
    # Use the cloned GeoUtils code for explicit common-grid alignment and
    # georeference-checked masked subtraction. No vertical transformation.
    aligned_reference = reference_raster.reproject(ref=bed_raster, resampling="bilinear", silent=True,
                                                 n_threads=1, apply_vertical=False)
    difference_raster = bed_raster - aligned_reference
    # Retain both grid dimensions for narrow selections with one row/column.
    difference = np.ma.filled(difference_raster.data, np.nan).reshape(height, width)
    positive = np.maximum(difference, 0)
    negative = np.maximum(-difference, 0)
    positive_volume = float(np.nansum(positive * areas))
    negative_volume = float(np.nansum(negative * areas))
    valid_area = float(areas[valid].sum())
    requested_area = float(requested_boundary.area if requested_boundary is not None else box(*bounds).area)
    coverage = min(100.0, 100 * valid_area / requested_area) if requested_area > 0 else 0
    warnings = [{"code": "grid_approximation", "params": {}}, {"code": "edge_limit", "params": {"max_edge": config.max_edge}}]
    warnings.append({"code": {"design": "design_not_sludge", "previous": "previous_not_sludge", "underside": "underside_unverified"}[config.reference_type], "params": {}})
    if duplicate_count:
        warnings.append({"code": "duplicates_aggregated", "params": {"count": duplicate_count}})
    if flags.any():
        warnings.append({"code": "filter_excluded" if config.filter_mode == "exclude" else "filter_flagged", "params": {"count": int(flags.sum())}})
    if coverage < 99.9:
        warnings.append({"code": "limited_coverage", "params": {"percent": round(coverage, 2)}})
    if source.native_raster is not None or (source_metadata or {}).get("source_kind") == "raster_cell_centres":
        warnings.append({"code": "raster_source", "params": {}})
    if source.source_kind == "shapefile_pointz" or (reference_source and reference_source.source_kind == "shapefile_pointz"):
        warnings.append({"code": "shapefile_source", "params": {}})
    lod = None
    detectable_positive = detectable_negative = None
    if config.sigma_current is not None and config.sigma_reference is not None:
        lod = float(1.96 * math.hypot(config.sigma_current, config.sigma_reference))
        detectable_positive = float(np.nansum(np.where(difference > lod, difference * areas, 0)))
        detectable_negative = float(np.nansum(np.where(difference < -lod, -difference * areas, 0)))
    else:
        warnings.append({"code": "no_uncertainty", "params": {}})
    if config.surface_method == "kriging":
        warnings.append({"code": "kriging_experimental", "params": {}})
    if design is not None and profile_comparison["metadata"]["provisional"]:
        warnings.append({"code": "profile_provisional", "params": {}})
    if review is not None:
        warnings.append({"code": "survey_heights_screened", "params": {"count": int((~use).sum())}})
    summary = dict(surface_method=config.surface_method, geometric_area_m2=geometric_area,
                   prediction_excluded_area_m2=sum(exclusion_areas.values()), exclusion_areas_m2=exclusion_areas,
                   positive_volume_m3=positive_volume, negative_volume_m3=negative_volume,
                   net_volume_m3=positive_volume-negative_volume,
                   positive_area_m2=float(areas[(difference > 0) & valid].sum()),
                   negative_area_m2=float(areas[(difference < 0) & valid].sum()), valid_area_m2=valid_area,
                   requested_area_m2=requested_area, excluded_area_m2=max(0, requested_area-valid_area),
                   coverage_percent=coverage, input_points=len(source.xyz), accepted_points=len(accepted),
                   selected_points=len(selected), outside_analysis_area_points=len(retained)-len(selected),
                   withheld_height_correction_points=len(source.xyz)-len(retained),
                   flagged_points=int(flags.sum()), duplicate_points=duplicate_count,
                   grid_cells=width*height, valid_cells=int(valid.sum()),
                   min_difference_m=float(np.nanmin(difference)), max_difference_m=float(np.nanmax(difference)),
                   mean_difference_m=float(np.nansum(difference * areas)/valid_area),
                   cell_size_m=cell, reference_type=config.reference_type, reference_note=config.reference_note,
                   crs=config.crs, vertical_datum=config.vertical_datum, filter_mode=config.filter_mode,
                   lod95_m=lod, detectable_positive_volume_m3=detectable_positive,
                   detectable_negative_volume_m3=detectable_negative, source_kind=(source_metadata or {}).get("source_kind", source.source_kind))
    provenance = dict(application_version="0.2.0", surface_generation=method_details, algorithm=f"{config.surface_method} elevations; bounded observed triangle support; common-grid quadrature with clipped plan areas and area-centroid/interior samples for partial cells",
                      survey={"filename": source.name, "sha256": source.sha256, "source_kind": summary["source_kind"], "metadata": source.metadata},
                      reference={"filename": reference_source.name, "sha256": reference_source.sha256, "source_kind": reference_source.source_kind, "metadata": reference_source.metadata} if reference_source else {"assumed_constant_elevation_m": config.reference_elevation},
                      configuration=config.model_dump(), source_metadata=source_metadata,
                      foundation={"repository": "https://github.com/GlacioHack/geoutils", "commit": "fda51a598f81f8cdd5f96855ae59edb23738ac45"},
                      vertical_datum_status="user_declared; no vertical transformation or independent verification",
                      uncertainty_model="optional independent unbiased Gaussian per-surface sigma; excludes correlation and systematic bias; not a volume confidence interval")
    provenance["kriging_uncertainty"] = "Point prediction variance conditional on fitted isotropic variogram and exact observations. Excludes variogram parameter uncertainty, unmodelled trends, datum bias and separately calibrated acquisition error. Not combined with user sigma or a volume confidence interval." if config.surface_method == "kriging" else None
    if design is not None:
        provenance["reference"] = profile_comparison["metadata"]
    if review is not None:
        provenance["survey"]["height_review"] = review
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.json").write_text(json.dumps({"summary": summary, "warnings": warnings, "provenance": provenance}, indent=2))
    with (output_dir / "cells.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["x", "y", "sample_x", "sample_y", "bed_elevation_m", "reference_elevation_m", "difference_m", "supported_area_m2", "valid", "bed_kriging_variance_m2", "bed_kriging_standard_error_m", "reference_kriging_variance_m2", "reference_kriging_standard_error_m", "exclusion_reason", "geometric_area_m2"])
        for i, ((a, b), (sx, sy), c, d, e, area, ok) in enumerate(zip(xy, sample_xy, bed.ravel(), reference.ravel(), difference.ravel(), areas.ravel(), valid.ravel())):
            writer.writerow([a, b, sx, sy, c if ok else "", d if ok else "", e if ok else "", area if ok else 0, int(ok), *[float(v) if np.isfinite(v) else "" for v in [bed_variance[i], np.sqrt(bed_variance[i]), reference_variance[i], np.sqrt(reference_variance[i])]], str(reasons[i]), float(geometric_areas[i])])
    with (output_dir / "points.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["x", "y", "z_elevation_m", "flagged", "used"])
        for point, flag in zip(unique, flags):
            writer.writerow([*point, int(flag), int(not flag or config.filter_mode != "exclude")])
    for name, raster in [("bed", bed_raster), ("reference", aligned_reference), ("difference", difference_raster)]:
        path = output_dir / f"{name}.tif"
        raster.to_file(str(path), driver="GTiff", nodata=-9999.0, co_opts={"COMPRESS": "DEFLATE"})
        with rasterio.open(path, "r+") as dst:
            dst.update_tags(vertical_datum=config.vertical_datum, units="m", z_convention="elevation_positive_up" if name != "difference" else "current_minus_reference", reference_type=config.reference_type)
    if config.surface_method == "kriging":
        for role, variance in [("bed", bed_variance), ("reference", reference_variance)]:
            if role == "reference" and reference_surface is None:
                continue
            for kind, values, units in [("variance", variance, "m2"), ("standard_error", np.sqrt(variance), "m")]:
                raster = raster_from_values(values.reshape(height, width), transform, config.crs)
                path = output_dir / f"{role}_kriging_{kind}.tif"
                raster.to_file(str(path), driver="GTiff", nodata=-9999.0, co_opts={"COMPRESS": "DEFLATE"})
                with rasterio.open(path, "r+") as dst:
                    dst.update_tags(units=units, quantity=f"point_prediction_{kind}", surface_method="ordinary_kriging",
                                    includes_excluded_predictions="true", height_reference=config.vertical_datum)
    def array_json(array):
        return [[float(v) if np.isfinite(v) else None for v in row] for row in array]
    stride = max(1, math.ceil(math.sqrt(width*height / 40_000)))
    display_valid = valid[::stride, ::stride]
    # A regular display surface needs neighbouring values to draw a patch.
    # If it has none, draw the accepted area of each cell at its sampled height.
    has_patch = (display_valid[:-1, :-1] & display_valid[1:, :-1] &
                 display_valid[:-1, 1:] & display_valid[1:, 1:]).any()
    bed_mesh = bed_samples = None
    if not has_patch or design is not None:
        accepted_indices = np.flatnonzero(valid)
        sample_stride = max(1, math.ceil(len(accepted_indices) / 8000))
        displayed = accepted_indices[::sample_stride]
        try:
            faces, owners = shapely.get_parts(
                shapely.constrained_delaunay_triangles(clipped_cells[displayed]), return_index=True
            )
        except shapely.errors.ShapelyError:
            # A display triangulation failure must not discard a valid calculation.
            faces = []
        if len(faces):
            # Each exterior ring has three vertices followed by its closing point.
            vertices = shapely.get_coordinates(faces).reshape(-1, 4, 2)[:, :3].reshape(-1, 2)
            face_cells = displayed[owners]
            focus_cell = face_cells[np.argmax(areas.ravel()[face_cells])]
            bed_mesh = {"x": vertices[:, 0].tolist(), "y": vertices[:, 1].tolist(),
                        "bed": np.repeat(bed.ravel()[face_cells], 3).tolist(),
                        "reference": np.repeat(reference.ravel()[face_cells], 3).tolist(),
                        "cell_count": int(len(np.unique(face_cells))), "focus": sample_xy[focus_cell].tolist()}
        else:
            samples = np.column_stack((sample_xy[displayed], bed.ravel()[displayed], reference.ravel()[displayed]))
            bed_samples = dict(zip(("x", "y", "bed", "reference"), samples.T.tolist()))
    point_stride = max(1, math.ceil(len(unique) / 8000))
    result = {"summary": summary, "warnings": warnings, "provenance": provenance,
            "grid": {"x": x[::stride].tolist(), "y": y[::stride].tolist(), "bed": array_json(bed[::stride, ::stride]),
                     "reference": array_json(reference[::stride, ::stride]), "difference": array_json(difference[::stride, ::stride]),
                     "bed_variance": array_json(bed_variance.reshape(height, width)[::stride, ::stride]),
                     "reference_variance": array_json(reference_variance.reshape(height, width)[::stride, ::stride]),
                     "bed_standard_error": array_json(np.sqrt(bed_variance).reshape(height, width)[::stride, ::stride]),
                     "reference_standard_error": array_json(np.sqrt(reference_variance).reshape(height, width)[::stride, ::stride]),
                     "valid": display_valid.tolist(), "area": areas[::stride, ::stride].tolist(), "display_stride": stride},
            "bed_mesh": bed_mesh, "bed_samples": bed_samples,
            "points": {"x": unique[::point_stride, 0].tolist(), "y": unique[::point_stride, 1].tolist(),
                       "z": unique[::point_stride, 2].tolist(), "flagged": flags[::point_stride].tolist()}}
    if profile_comparison is not None:
        result["profile"] = profile_comparison
    return result
