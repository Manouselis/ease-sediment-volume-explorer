"""Geometry of straight, standard wetted canal profiles in RD New/NAP."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict
from shapely.geometry import Polygon


@dataclass(frozen=True)
class Profile:
    bed_width: float
    depth: float
    run_per_rise: float

    @property
    def bed_edge(self):
        return self.bed_width / 2

    @property
    def water_edge(self):
        return self.bed_edge + self.depth * self.run_per_rise

    def elevations(self, offset, water_level):
        rise = np.maximum(0, np.abs(offset) - self.bed_edge) / self.run_per_rise
        return water_level - self.depth + rise


# Zuiderzeeland leggertabel W-A-AL-001, sheet 1, revision C, 21 September 2017.
# Base profiles from the wetted design. The optional dz details are separate.
PROFILES = {"L8": Profile(5.30, 1.20, 2), "L8A": Profile(2.30, 1.50, 2),
            "L10": Profile(7.00, 1.20, 2)}
PROFILE_SOURCE = "Waterschap Zuiderzeeland W-A-AL-001 rev C, sheet 1"
CRS = "EPSG:28992"
DATUM = "NAP"


class DesignSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    code: Literal["L8", "L8A", "L10"]
    water_level_m_nap: float
    water_level_confirmed: bool = False
    survey_nap_confirmed: bool = False
    coverage: Literal["track", "area"] = "track"
    endpoints: tuple[float, float, float, float] | None = None


@dataclass(frozen=True)
class Reach:
    start: np.ndarray
    direction: np.ndarray
    length: float

    @property
    def left(self):
        return np.array([-self.direction[1], self.direction[0]])

    def project(self, xy):
        delta = xy - self.start
        return delta @ self.direction, delta @ self.left

    def xy(self, station, offset):
        return self.start + station[..., None] * self.direction + offset[..., None] * self.left


def straight_reach(xy, endpoints, profile):
    if endpoints is not None:
        start, end = np.asarray(endpoints, dtype=float).reshape(2, 2)
        delta = end - start
        length = float(np.linalg.norm(delta))
        if not np.isfinite(length) or length <= 0:
            raise ValueError("Provide two distinct, finite centreline endpoints in RD New metres.")
        return Reach(start, delta / length, length)

    origin = xy.mean(axis=0)
    _, _, axes = np.linalg.svd(xy - origin, full_matrices=False)
    direction = axes[0]
    if direction @ (xy[-1] - xy[0]) < 0:
        direction = -direction
    station = (xy - origin) @ direction
    across = (xy - origin) @ axes[1]
    length = float(np.ptp(station))
    if length <= 0 or length < 4 * np.ptp(across) or np.abs(across).max() > profile.bed_edge:
        raise ValueError("Track alignment requires a long, narrow track inside the flat part of the design. "
                         "Supply surveyed endpoints for a single straight reach.")
    if np.diff(np.sort(station)).max() > 25:
        raise ValueError("The track contains a gap over 25 m. Supply endpoints or split the survey.")
    return Reach(origin + station.min() * direction, direction, length)


def reference_grid(reach, profile, water_level, spacing, max_points=100_000):
    # Sample each panel separately to preserve both transitions to the flat bed.
    breaks = [-profile.water_edge, -profile.bed_edge, profile.bed_edge, profile.water_edge]
    counts = [math.ceil((b - a) / spacing) for a, b in zip(breaks, breaks[1:])]
    stations = math.ceil(reach.length / spacing)
    if (stations + 1) * (sum(counts) + 1) > max_points:
        raise ValueError("Reference exceeds the app's point limit. Increase spacing or shorten the reach.")
    lateral = np.concatenate([np.linspace(a, b, n, endpoint=False)
                              for a, b, n in zip(breaks, breaks[1:], counts)] + [breaks[-1:]])
    distance, offset = np.meshgrid(np.linspace(0, reach.length, stations + 1), lateral)
    xy = reach.xy(distance, offset)
    z = profile.elevations(offset, water_level)
    return np.column_stack((xy.reshape(-1, 2), z.ravel()))


def compare_points(reach, profile, water_level, xyz, track):
    distance, offset = reach.project(xyz[:, :2])
    tolerance = 1e-7
    inside = ((distance >= -tolerance) & (distance <= reach.length + tolerance)
              & (np.abs(offset) <= profile.water_edge + tolerance))
    # Track mode declares a centreline survey. Cross-track jitter does not
    # change its reference elevation. Keep the observed XY for inspection.
    design_offset = np.zeros(len(xyz)) if track else offset
    design = np.where(inside, profile.elevations(design_offset, water_level), np.nan)
    return distance, offset, design


@dataclass(frozen=True)
class DesignReference:
    settings: DesignSettings
    reach: Reach

    @property
    def profile(self):
        return PROFILES[self.settings.code]

    @property
    def water_level(self):
        return self.settings.water_level_m_nap

    @property
    def footprint(self):
        edge = self.profile.water_edge
        return Polygon(self.reach.xy(
            np.array([0, self.reach.length, self.reach.length, 0]),
            np.array([-edge, -edge, edge, edge]),
        ))

    def compare(self, xyz):
        return compare_points(self.reach, self.profile, self.water_level, xyz, False)

    def sample(self, xy):
        # The calculation footprint is already clipped to the design. Keep
        # boundary-centroid rounding within the closed design cross-section.
        _, offset = self.reach.project(xy)
        return self.profile.elevations(np.clip(offset, -self.profile.water_edge, self.profile.water_edge),
                                       self.water_level)

    def metadata(self):
        return {
            "method": "design_profile", "code": self.settings.code, "source": PROFILE_SOURCE,
            "coverage": self.settings.coverage,
            "water_level_m_nap": self.water_level,
            "water_level_confirmed": self.settings.water_level_confirmed,
            "bed_elevation_m_nap": self.water_level - self.profile.depth,
            "bed_width_m": self.profile.bed_width, "depth_m": self.profile.depth,
            "waterline_width_m": 2 * self.profile.water_edge,
            "slope_horizontal_per_vertical": self.profile.run_per_rise,
            "alignment": "fitted" if self.settings.endpoints is None else "endpoints",
            "start_xy": self.reach.start.tolist(), "direction_xy": self.reach.direction.tolist(),
            "end_xy": (self.reach.start + self.reach.length * self.reach.direction).tolist(),
            "length_m": self.reach.length,
            "provisional": (self.settings.endpoints is None or not self.settings.water_level_confirmed
                            or not self.settings.survey_nap_confirmed),
        }
