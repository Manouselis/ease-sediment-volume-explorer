"""Read one bounded PointZ shapefile package without guessing a height field."""
from __future__ import annotations

import stat
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

import geopandas as gpd
import numpy as np
from pyproj import CRS


class VectorInputError(ValueError):
    def __init__(self, code: str, **params):
        self.code, self.params = code, params
        super().__init__(code)


def read_pointz_zip(path: Path, declared_crs: CRS, max_points: int) -> tuple[np.ndarray, dict]:
    """Preserve embedded XYZ. A .prj establishes XY only, never the height datum."""
    try:
        with zipfile.ZipFile(path) as archive:
            entries = [i for i in archive.infolist() if not i.is_dir()]
            if len(entries) > 64 or sum(i.file_size for i in entries) > 100 * 1024 * 1024:
                raise VectorInputError("invalid_shapefile", reason="archive_limits")
            names = {}
            for entry in entries:
                name = PurePosixPath(entry.filename.replace("\\", "/"))
                mode = entry.external_attr >> 16
                if (name.is_absolute() or ".." in name.parts or ":" in name.parts[0]
                        or stat.S_ISLNK(mode) or entry.flag_bits & 1 or entry.filename.lower() in names):
                    raise VectorInputError("invalid_shapefile", reason="unsafe_archive")
                names[entry.filename.lower()] = entry
            layers = [i for i in entries if i.filename.lower().endswith(".shp")]
            if len(layers) != 1:
                raise VectorInputError("invalid_shapefile", reason="one_layer_required")
            layer = layers[0]
            stem = layer.filename[:-4].lower()
            if any(stem + ext not in names for ext in (".shx", ".dbf", ".prj")):
                raise VectorInputError("invalid_shapefile", reason="missing_sidecars")
            # Only selected sidecars are copied, under fixed names in a private directory.
            with tempfile.TemporaryDirectory(prefix="ease-shape-") as folder:
                target = Path(folder) / "surface.shp"
                for ext in (".shp", ".shx", ".dbf", ".prj", ".cpg"):
                    if stem + ext in names:
                        (Path(folder) / ("surface" + ext)).write_bytes(archive.read(names[stem + ext]))
                if sys.platform == "emscripten":
                    import fiona
                    with fiona.open(target) as dataset:
                        source_crs, features = dataset.crs_wkt, len(dataset)
                    engine = "fiona"
                else:
                    import pyogrio
                    info = pyogrio.read_info(target)
                    source_crs, features = info["crs"], info["features"]
                    engine = "pyogrio"
                if not source_crs or not CRS(source_crs).equals(declared_crs):
                    raise VectorInputError("crs_mismatch")
                if features > max_points:
                    raise VectorInputError("too_many_points", limit=max_points)
                frame = gpd.read_file(target, engine=engine, rows=max_points + 1)
                if len(frame) > max_points:
                    raise VectorInputError("too_many_points", limit=max_points)
                if (frame.empty or frame.geometry.isna().any() or frame.geometry.is_empty.any()
                        or not frame.geom_type.eq("Point").all() or not frame.has_z.all()):
                    raise VectorInputError("shapefile_requires_pointz")
                xyz = np.column_stack((frame.geometry.x, frame.geometry.y, frame.geometry.z))
                metadata = {
                    "layer": PurePosixPath(layer.filename).name,
                    "geometry": "PointZ", "embedded_crs": CRS(frame.crs).to_string(),
                    "height_source": "geometry Z, unchanged except declared depth sign conversion",
                    "vertical_datum_status": "not encoded by the horizontal .prj; user-declared",
                    "attributes": [str(c) for c in frame.columns if c != frame.geometry.name],
                }
                if "name" in frame and frame["name"].nunique(dropna=False) <= 50:
                    metadata["name_counts"] = {str(k): int(v) for k, v in frame["name"].value_counts(dropna=False).items()}
                return xyz, metadata
    except VectorInputError:
        raise
    except Exception as exc:
        raise VectorInputError("invalid_shapefile", reason="unreadable_package") from exc
