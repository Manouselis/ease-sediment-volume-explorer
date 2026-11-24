# Third-party source and attribution

## Cloned and integrated foundation: GeoUtils

- Upstream project: GeoUtils, by the GeoUtils developers.
- Repository: <https://github.com/GlacioHack/geoutils>
- Local source: `vendor/geoutils/`
- Exact upstream commit: `fda51a598f81f8cdd5f96855ae59edb23738ac45`
- Cloned: 12 October 2026, with `git clone --depth 1`.
- License: Apache License 2.0; full license preserved at [vendor/geoutils/LICENSE](../vendor/geoutils/LICENSE).
- Upstream notices preserved at [vendor/geoutils/NOTICE](../vendor/geoutils/NOTICE).

The source checkout is incorporated and installed locally. Application code imports GeoUtils and uses its georeferenced raster loading/construction, masked surface comparison and GeoTIFF export. Both CSV and GeoTIFF pixel-centre inputs are reconstructed through the selected interpolation method with bounded SciPy triangle coverage onto one common grid. GeoUtils' reference-grid alignment call is therefore currently an identity consistency operation, not a native resampling of the uploaded raster. No upstream source modification is required. Editable installation may generate normal packaging/version metadata; those are not algorithm changes. EASE-specific validation, support masks, integration and UI live outside the upstream checkout.

For redistribution, retain the complete upstream LICENSE and NOTICE, original source notices and this attribution. Identify any future modifications. The application’s own license does not replace licenses of its dependencies. GeoUtils is not an endorsement of this application or its hydrographic fitness.

## Other runtime components

The implementation also depends on existing open-source software rather than reimplementing numerical/GIS kernels:

| Component | Main role | License declared by project |
|---|---|---|
| [SciPy](https://github.com/scipy/scipy) | Delaunay/TIN, interpolation, spatial search | BSD-3-Clause |
| [NumPy](https://github.com/numpy/numpy) | Array arithmetic and volume summation | BSD-3-Clause |
| [Rasterio](https://github.com/rasterio/rasterio) | GDAL-backed raster I/O, used through GeoUtils | BSD-3-Clause |
| [PyProj](https://github.com/pyproj4/pyproj) | CRS parsing and checks | MIT |
| [Shapely](https://github.com/shapely/shapely) | Geometry and polygon operations | BSD-3-Clause |
| [pandas](https://github.com/pandas-dev/pandas) | Tabular data handling | BSD-3-Clause |

These are package dependencies, not additional projects claimed as cloned/adapted foundations. Their installed distributions contain their respective notices. Preserve those notices and transitive dependency licenses when packaging an executable or environment. UI/server dependencies and exact tested versions are listed in the application requirements/lock records.

Data have separate usage conditions; see the real-data provenance documentation. Software licenses do not grant rights over unrelated data.

The locally bundled [Plotly.js](https://github.com/plotly/plotly.js) browser library keeps its original header and full MIT permission notice in [static/plotly-LICENSE.txt](../static/plotly-LICENSE.txt). FastAPI (MIT), Starlette (BSD-3-Clause), Uvicorn (BSD-3-Clause), Pydantic (MIT), python-multipart (Apache-2.0), pytest (MIT) and HTTPX (BSD-3-Clause) retain their installed package notices. Playwright is an optional development-only browser check, not a runtime dependency.


## Ordinary Kriging

[PyKrige](https://github.com/GeoStat-Framework/PyKrige), version **1.7.3**, supplies
unmodified variogram fitting and Ordinary Kriging numerical solves. It is
BSD-3-Clause licensed. Its installed distribution preserves its licence. EASE
adds bounded sampling, local neighbourhood selection, coverage restrictions,
uncertainty exports and UI controls. See [upstream licence](https://github.com/GeoStat-Framework/PyKrige/blob/v1.7.3/LICENSE)
and [the integration description](KRIGING.md). No upstream source is modified.
