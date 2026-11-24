"""Read GeoTIFF codecs unavailable in the browser build of Rasterio."""
from __future__ import annotations

import geoutils as gu
import numpy as np
import rasterio
from rasterio.enums import MaskFlags
from rasterio.errors import RasterioIOError


def read_geotiff(path):
    from tifffile import TiffFile

    # Rasterio still owns the interpretation of CRS, affine transform, and
    # nodata. Tifffile decodes the pixels losslessly for the same GeoUtils grid.
    with rasterio.open(path) as dataset, TiffFile(path) as tif:
        page = tif.pages[0]
        if page.shape != dataset.shape:
            raise ValueError("TIFF page does not match the single-band dataset")
        values = page.asarray(maxworkers=1)
        invalid = ~np.isfinite(values)
        if dataset.nodata is not None:
            invalid |= values == dataset.nodata
        flags = dataset.mask_flag_enums[0]
        if MaskFlags.per_dataset in flags or MaskFlags.alpha in flags:
            try:
                valid = dataset.read_masks(1) != 0
            except RasterioIOError:
                candidates = [mask for mask in tif.pages[1:] if mask.is_mask and mask.shape == dataset.shape]
                if len(candidates) != 1:
                    raise ValueError("Could not decode the original TIFF mask")
                valid = candidates[0].asarray(maxworkers=1) != 0
            invalid |= ~valid
        return gu.Raster.from_array(
            np.ma.array(values, mask=invalid), transform=dataset.transform,
            crs=dataset.crs, nodata=dataset.nodata,
            area_or_point=dataset.tags().get("AREA_OR_POINT"),
        )
