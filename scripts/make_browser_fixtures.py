"""Create synthetic inputs for the real browser analysis smoke test."""
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

import geopandas as gpd
import numpy as np
import rasterio
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

coordinates = [(x, y) for x in range(2) for y in range(2)] + [(0.5, 0.5)]
rows, snd = ["x,y,z"], ["VER 12.0", "NDT -9999"]
for i, (x, y) in enumerate(coordinates):
    rows.append(f"{x},{y},{1 if i == 4 else -6}")
    fields = ["0"] * 24
    fields[:5] = ["SND", str(1758097977 + i), str(x), str(y), "1"]
    fields[13] = "-9999" if i == 4 else "-5"
    snd.append(" ".join(fields))
(output / "paired-survey.csv").write_text("\n".join(rows) + "\n")
(output / "SNDG00001").write_text("\n".join(snd) + "\n")
