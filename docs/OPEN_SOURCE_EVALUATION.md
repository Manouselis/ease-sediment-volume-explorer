# Open-source foundation selection

Evaluated 12 October 2026 for the EASE proof of concept. The scope is a small, reproducible surface-comparison application for corrected bathymetric data.

The required starting input is corrected, georeferenced bed XYZ, not raw imaging-sonar pixels. No candidate below was verified as an end-to-end Sonoptix ECHO processor. Repository inspection establishes software capabilities; it does not establish EASE measurement accuracy.

## Candidate comparison

| Candidate | Inputs and useful functionality | Algorithms and adaptation | Maintenance, license and decision |
|---|---|---|---|
| **[GeoUtils](https://github.com/GlacioHack/geoutils)** | Georeferenced rasters, vectors and point clouds; GeoTIFF reading/writing; masked raster arithmetic; reference-grid reprojection. | Reuses Rasterio/GDAL, NumPy and PyProj. Provides linear/nearest/cubic point gridding and reference-grid matching. A small Python adapter can keep datum checks, conservative support masks and volume interpretation explicit. **Low–medium integration effort.** | Main updated 11 October 2026 UTC; tests, CI and API documentation. Current source is **Apache-2.0**. **Selected for the raster alignment, comparison and export stages.** It is a GIS foundation, not a hydrographic acquisition system. |
| **[NOAA bathygrid](https://github.com/noaa-ocs-hydrography/bathygrid)** | Projected-metre XYZ in structured NumPy arrays/xarray; optional sounding uncertainties; tiled grids; CSV, GeoTIFF and BAG export. | Mean/shoalest cell gridding, variable-resolution tiles and optional CUBE integration. Appropriate bathymetric tooling, but the intended linear TIN and volume application still require an adapter. **Medium effort**, including GDAL/Numba/Dask dependencies. | Last repository push 28 September 2022. Documented environment uses Python 3.8/GDAL 3.2; `setup.py` declares **CC0-1.0**, although the repository has no top-level license file. Not selected because of integration and environment risk within the small prototype. |
| **[MB-System](https://github.com/dwcaress/MB-System)** | Many supported raw swath-sonar formats through MBIO; bathymetry, navigation and sound-speed processing; cleaning and gridding. | Strongest upstream option when compatible raw bathymetric sonar is available. Native tools, GMT/GDAL/NetCDF/PROJ and format-specific configuration make embedding a web prototype more involved. **High effort** for this task. | Updated October 2026; extensive documentation and change history. **GPL-3.0**, see upstream COPYING/GPL files. Not selected for the downstream XYZ prototype. No verified ECHO reader. |
| **[CloudCompare](https://github.com/CloudCompare/CloudCompare)** | ASCII point clouds and common geospatial/3D formats; interactive editing, rasterization and 2.5D volume between clouds or a plane. | Excellent independent desktop comparison. Its volume tool uses a common XY grid and sums cell area times height difference. Embedding its desktop C++/Qt interface into the requested bilingual application adds work. **Low effort as a separate tool; high as the application foundation.** | Updated October 2026. **GPL-2.0-or-later** according to `license.txt`. Retain as a future independent numerical cross-check, not a test already performed. |
| **[xDEM](https://github.com/GlacioHack/xdem)** | DEMs and elevation point clouds; surface comparison, co-registration and error analysis. | Strong extension for repeat-survey uncertainty. Adds terrain-specific methods that this minimal design-volume calculation does not need. Avoid automatic co-registration on genuinely changing bed regions. **Medium effort.** | Updated September 2026; tests and scientific documentation. **Apache-2.0**. Not selected because GeoUtils supplies the essential GIS stages with less application scope. |

Maintenance dates are the GitHub API `pushed_at` values observed on the evaluation date, not a guarantee of future support. Complexity ratings concern integration effort, not benchmarked runtime.

## Selected reuse and adaptation

The public GeoUtils repository was actually cloned to `vendor/geoutils`:

- Repository: <https://github.com/GlacioHack/geoutils>
- Exact commit: `fda51a598f81f8cdd5f96855ae59edb23738ac45`
- Commit timestamp: `2026-10-10T18:24:35-08:00`
- Commit subject: `Add RPCs/GCPs support throughout raster functionalities (#982)`
- Source version and reuse notices: [THIRD_PARTY.md](THIRD_PARTY.md)

The application adapts the project through composition rather than rewriting upstream source. GeoUtils reads uploaded GeoTIFFs and exposes masked values and georeferencing; accepted raster pixel centres become XYZ just as uploaded CSV rows do. In the default route, SciPy constructs both bounded TIN surfaces and samples them on one explicitly defined grid. The experimental route retains this coverage geometry but uses PyKrige for elevation predictions. GeoUtils `Raster.from_array` then wraps those grids with georeferencing and NoData, georeferenced masked arithmetic creates the difference, and `Raster.to_file` writes GeoTIFF products. `Raster.reproject(ref=...)` is currently an identity operation on the already matching grids: an explicit common-grid consistency step, not a claimed native resampling of the original uploaded raster. No vertical transformation is performed.

Application code supplies input validation, optional conservative anomaly flags, coverage restrictions, positive/negative integration and the bilingual interface. This is substantive reuse of the selected foundation, not a claim that GeoUtils already contained a complete sludge application. Reconstructing raster cell centres through TIN can shrink their original pixel-edge coverage and change sampled values; the interface reports this limitation. A direct native-raster comparison route could be a later extension.

GeoUtils also offers `PointCloud.grid` in the pinned revision. The application retains explicit SciPy TIN construction so its longest-edge support restrictions and preserved raster NoData mask can be inspected directly. The original evaluation selected linear TIN as the baseline. Ordinary Kriging was added as an experimental comparator on 30 October 2026 using PyKrige. ML, CUBE and acoustic material classification remain outside the implementation. See [KRIGING.md](KRIGING.md).

## Scientific basis and limits

The selection follows the baseline described in [ALGORITHMS.md](ALGORITHMS.md): clean XYZ → linear TIN → common grid → separate positive/negative volumes. Linear interpolation is explainable and matches the [documented Hydromagic Delaunay route](https://www.eye4software.com/hydromagic/documentation/manual/post-processing/generate-matrix/). Its selection is practical, not evidence that it universally outperforms IDW or kriging. [Wheaton et al.](https://doi.org/10.1002/esp.1886) motivate treating small survey differences and positive clipping cautiously; this prototype does not establish a field uncertainty model.

Integration uses each grid cell's supported plan area. Partial cells use their clipped-area centroid, or an interior representative point when that centroid lies outside the supported fragment. This is exact for an affine surface over such a centroid-sampled fragment; general TIN breakpoints and zero crossings still make it a grid approximation. Refine the grid and assess sensitivity before an operational use. Polygon holes, rejected long triangles and native raster NoData remain excluded; excluded area is reported rather than assigned zero bed elevation.

A design comparison yields material above a target profile. An earlier survey yields bed-volume change. A verified underside can support defined-layer volume, but merely selecting that label does not verify the boundary. None of these calculations identifies sediment composition, density or dry mass.

ECHO is documented as [forward-looking imaging sonar](https://sonoptix.com/specifications). Integration requires a separately validated bottom-detection/reconstruction route, calibrated geometry and sound speed, synchronized position/attitude, offsets, and a traceable vertical datum. The app accepts the resulting corrected XYZ; it does not invent that conversion. Hydromagic can export accepted XYZ/matrices for the same downstream route, subject to the actual installed software and supported input.

## Primary evidence

- GeoUtils: [README](https://github.com/GlacioHack/geoutils/blob/fda51a598f81f8cdd5f96855ae59edb23738ac45/README.md), [Raster API source](https://github.com/GlacioHack/geoutils/blob/fda51a598f81f8cdd5f96855ae59edb23738ac45/geoutils/raster/base.py), [license](https://github.com/GlacioHack/geoutils/blob/fda51a598f81f8cdd5f96855ae59edb23738ac45/LICENSE).
- bathygrid: [README](https://github.com/noaa-ocs-hydrography/bathygrid/blob/main/README.md), [algorithm source](https://github.com/noaa-ocs-hydrography/bathygrid/blob/main/bathygrid/algorithms.py), [license declaration](https://github.com/noaa-ocs-hydrography/bathygrid/blob/main/setup.py).
- MB-System: [README, functionality and dependencies](https://github.com/dwcaress/MB-System/blob/master/README.md), [GPL](https://github.com/dwcaress/MB-System/blob/master/GPL.md).
- CloudCompare: [2.5D volume documentation](https://www.cloudcompare.org/doc/wiki/index.php/2.5D_Volume), [license](https://github.com/CloudCompare/CloudCompare/blob/master/license.txt).
- xDEM: [repository and documentation links](https://github.com/GlacioHack/xdem), [license](https://github.com/GlacioHack/xdem/blob/main/LICENSE).

The cloned project was imported successfully from `vendor/geoutils/geoutils/__init__.py` in the application's virtual environment. A numerical smoke check aligned a synthetic 2×2 reference at −3 m to a 4×4, 1 m survey grid at −2 m, subtracted the rasters and exported/reloaded a GeoTIFF. All 16 cells retained the expected 1 m difference, projected CRS and affine transform, giving 16 m³. This verifies API execution and bookkeeping, not field accuracy. The smoke check used the working but deprecated `save` wrapper; application exports use the current `to_file` API.

Installation, automated tests and real-data results are recorded in the application README and demo documentation; the comparison above is not a claim that all rejected candidates were installed or benchmarked.
