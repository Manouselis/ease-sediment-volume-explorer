"""Bounded local Ordinary Kriging using unmodified PyKrige solvers.

Never give PyKrige all survey points: its initialization and execute paths
allocate pairwise arrays even when n_closest_points is selected.
"""
from __future__ import annotations

import hashlib
import warnings

import numpy as np
import pykrige
from pykrige.ok import OrdinaryKriging
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

from .core import AnalysisError

FIT_POINTS = 512
MAX_PREDICTIONS = 20000


class KrigingSurface:
    def __init__(self, geometry, xyz, config):
        self.geometry, self.xyz, self.config = geometry, xyz, config
        # Fixed-seed random spatial observations, sorted for reproducible fitting.
        indices = np.sort(np.random.default_rng(42).choice(len(xyz), min(FIT_POINTS, len(xyz)), replace=False))
        fit = xyz[indices]
        params = {"psill": config.kriging_partial_sill, "range": config.kriging_range,
                  "nugget": config.kriging_nugget} if config.kriging_fit == "manual" else None
        if params is None and np.ptp(fit[:, 2]) < 1e-10:
            raise AnalysisError("kriging_fit_failed")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", RuntimeWarning)
                model = OrdinaryKriging(fit[:, 0], fit[:, 1], fit[:, 2],
                                       variogram_model=config.kriging_model, variogram_parameters=params,
                                       exact_values=True, enable_statistics=False)
            psill, distance, nugget = map(float, model.variogram_model_parameters)
            if not np.isfinite([psill, distance, nugget]).all() or psill <= 1e-12 or distance <= 1e-9 or nugget < 0:
                raise ValueError("degenerate variogram")
        except (ValueError, RuntimeError, RuntimeWarning, np.linalg.LinAlgError) as exc:
            raise AnalysisError("kriging_fit_failed") from exc
        self.parameters = {"psill": psill, "range": distance, "nugget": nugget}
        # Neighbours must belong to the same connected set of accepted triangles.
        triangles = geometry.triangulation.simplices[geometry.allowed]
        edges = np.concatenate([triangles[:, [0, 1]], triangles[:, [1, 2]], triangles[:, [2, 0]]])
        graph = coo_matrix((np.ones(len(edges)), (edges[:, 0], edges[:, 1])), shape=(len(xyz), len(xyz)))
        _, self.labels = connected_components(graph, directed=False)
        self.groups = {}
        for label in np.unique(self.labels[triangles.ravel()]):
            ids = np.flatnonzero(self.labels == label)
            self.groups[int(label)] = (ids, cKDTree(xyz[ids, :2]))
        self.metadata = {"method": "ordinary_kriging", "library": "PyKrige", "version": pykrige.__version__,
                         "fit": config.kriging_fit, "variogram_model": config.kriging_model,
                         "partial_sill_m2": psill, "total_sill_m2": psill + nugget,
                         "nugget_m2": nugget, "range_m": distance,
                         "fit_points": len(fit), "fit_seed": 42,
                         "fit_sample_sha256": hashlib.sha256(fit.tobytes()).hexdigest(),
                         "neighbors": config.kriging_neighbors, "radius_m": config.kriging_radius,
                         "exact_values": True, "anisotropy": "isotropic",
                         "uncertainty_target": "point elevation of the modelled process, exact at observations; nugget is unresolved variation, not a separately calibrated sensor-noise filter",
                         "limits": {"fit_points": FIT_POINTS, "neighbors": 64, "predictions": MAX_PREDICTIONS}}

    def sample(self, xy):
        z, variance = np.full(len(xy), np.nan), np.full(len(xy), np.nan)
        reason = np.full(len(xy), "outside_support", dtype=object)
        supported = self.geometry.support(xy)
        if supported.sum() > MAX_PREDICTIONS:
            raise AnalysisError("kriging_limit", limit=MAX_PREDICTIONS)
        simplex = self.geometry.triangulation.find_simplex(xy[supported], tol=1e-10)
        component = self.labels[self.geometry.triangulation.simplices[simplex, 0]]
        supported_ids = np.flatnonzero(supported)
        for label in np.unique(component):
            target_ids = supported_ids[component == label]
            ids, tree = self.groups[int(label)]
            k = min(self.config.kriging_neighbors, len(ids))
            dist, neighbors = tree.query(xy[target_ids], k=k, distance_upper_bound=self.config.kriging_radius)
            # Group equal neighbourhoods so PyKrige factors each small system once.
            groups = {}
            for target, ds, ns in zip(target_ids, dist, neighbors):
                selected = tuple(sorted(ids[ns[np.isfinite(ds)]].tolist()))
                if len(selected) < 3:
                    reason[target] = "insufficient_neighbors"
                    continue
                groups.setdefault(selected, []).append(target)
            for selected, targets in groups.items():
                local = self.xyz[list(selected)]
                try:
                    model = OrdinaryKriging(local[:, 0], local[:, 1], local[:, 2],
                                            variogram_model=self.config.kriging_model,
                                            variogram_parameters=self.parameters, exact_values=True,
                                            enable_statistics=False)
                    values, errors = model.execute("points", xy[targets, 0], xy[targets, 1], backend="vectorized")
                    values, errors = np.asarray(values), np.asarray(errors)
                    tolerance = 1e-8 * max(1, self.parameters["psill"] + self.parameters["nugget"])
                    if not np.isfinite(values).all() or not np.isfinite(errors).all() or np.any(errors < -tolerance):
                        raise ValueError("invalid prediction or variance")
                except (ValueError, RuntimeError, np.linalg.LinAlgError) as exc:
                    raise AnalysisError("kriging_solve_failed") from exc
                z[targets], variance[targets], reason[targets] = values, np.maximum(errors, 0), "accepted"
        return z, variance, reason
