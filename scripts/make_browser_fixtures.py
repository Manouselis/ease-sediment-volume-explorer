"""Create synthetic inputs for the real browser analysis smoke test."""
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

import geopandas as gpd
import numpy as np
import rasterio
from pyproj import CRS
from rasterio.transform import from_origin
from shapely.geometry import Point

output = Path(__file__).resolve().parents[1] / "qa/pages/fixtures"
output.mkdir(parents=True, exist_ok=True)
with TemporaryDirectory() as folder:
    layer = Path(folder) / "survey.shp"
    points = [Point(x, y, -2.0) for x in range(5) for y in range(5)]
    gpd.GeoDataFrame({"name": ["SNDG00001"] * len(points)}, geometry=points, crs="EPSG:28992").to_file(layer)
    with ZipFile(output / "survey.zip", "w", ZIP_DEFLATED) as package:
        for file in layer.parent.iterdir():
            package.write(file, f"nested/{file.name.upper()}")

with rasterio.open(output / "compressed.tif", "w", driver="GTiff", width=5, height=5, count=1,
                   crs="EPSG:28992", transform=from_origin(1000, 1005, 1, 1), dtype="float32",
                   compress="deflate", predictor=2) as raster:
    raster.write(np.full((5, 5), -2.0, dtype="float32"), 1)
    mask = np.full((5, 5), 255, dtype="uint8")
    mask[2, 2] = 0
    raster.write_mask(mask)
    raster.update_tags(vertical_datum="NAP", z_convention="elevation_positive_up")

coordinates = [(177000 + x, 522000) for x in range(5)]
rows, snd, points = ["x,y,z"], ["VER 12.0", "NDT -9999"], []
for i, (x, y) in enumerate(coordinates):
    z = 1 if i == 4 else -6
    rows.append(f"{x},{y},{z}")
    points.append(Point(x, y, z))
    fields = ["0"] * 24
    fields[:5] = ["SND", str(1758097977 + i), str(x), str(y), "1"]
    fields[13] = "-9999" if i == 4 else "-5"
    snd.append(" ".join(fields))
(output / "paired-survey.csv").write_text("\n".join(rows) + "\n")
(output / "SNDG00001").write_text("\n".join(snd) + "\n")

with TemporaryDirectory() as folder:
    layer = Path(folder) / "track.shp"
    gpd.GeoDataFrame({"name": ["SNDG00001"] * len(points)}, geometry=points, crs="EPSG:28992").to_file(layer)
    legacy = (CRS("EPSG:28992").to_wkt(version="WKT1_GDAL")
              .replace("52.1561605555556", "52.15616056")
              .replace("5.38763888888889", "5.38763889")
              .replace("0.9999079", "0.999908"))
    layer.with_suffix(".prj").write_text(legacy)
    with ZipFile(output / "paired-rd-new.zip", "w", ZIP_DEFLATED) as package:
        for file in layer.parent.iterdir():
            package.write(file, file.name)
