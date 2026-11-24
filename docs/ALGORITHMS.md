# Implemented algorithms

## 1. Validate and preserve

Read corrected XYZ, native XYZ from a PointZ shapefile ZIP, or centre elevations from a single-band GeoTIFF. Require finite numeric coordinates, a projected metric CRS, declared metre heights, an explicit vertical datum and a reference note. For two input surfaces, require matching CRS/datum; check raster metadata where supplied. The app neither corrects raw sonar nor performs vertical transformations. Exact duplicate XY observations are reduced to their median Z, with the count reported and original file hash recorded.

A shapefile ZIP must contain one PointZ layer and matching SHX/DBF/PRJ files. Embedded horizontal CRS must agree. Geometry Z supplies the height, with no attribute guessing. The horizontal PRJ does not verify the vertical datum.

Optional analysis bounds select observations inside a declared CRS-aligned box before deduplication, filtering and triangulation. Apply the same box to the reference and intersect it with an optional boundary. Outside observations do not influence the selected surface. Cropping can conservatively remove edge support. Input and selected counts remain separate in the summary. Inspection without a reference reports observations and metadata only, with no volume or inferred bed coverage.

## 2. Conservative potential-outlier flags

A KD-tree finds up to `neighbors` other points within twice `max_edge`. At least six neighbours and a full-rank local plane are required. Fit a plane in local XY coordinates, iteratively trim its residuals up to three times, and calculate the robust scale `1.4826 × median absolute deviation` about the residual median. Flag the observation if its leave-one-out residual exceeds `max(filter_k × robust_scale, filter_floor)`.

The fitted plane is a diagnostic trend; it never replaces observed Z. Default **flag** mode keeps all observations. **Exclude** removes flagged points before TIN construction, records that choice, and may reduce coverage. **Off** bypasses detection. References are not filtered. This is an explainable heuristic, not a validated sludge detector or a guaranteed vegetation/noise remover. Steep edges, sparse neighbourhoods, coherent false returns and real bed features need review.

## Experimental Ordinary Kriging

The operator can select `surface_method=kriging` instead of the default `tin`.
Both the bed and uploaded reference use the selected method, with separate
variogram fits. Constant references require no interpolation. Kriging predicts
directly at the shared integration sample locations, including clipped-cell
centroids. Delaunay geometry supplies only its original coverage mask and
connected neighbourhood components. No predicted XYZ is fed into TIN.

See [KRIGING.md](KRIGING.md) for the pinned solver, operator settings, automatic
fit sampling, exact-observation convention, uncertainty targets, bounded memory,
limits, exports and evaluation. The existing grid quadrature below remains
shared. Its affine exactness does not imply exact integration of Kriging surfaces.

## 3. Linear TIN and bounded support

Use SciPy/Qhull Delaunay triangulation of accepted XY and linear interpolation of vertex elevations. Reject triangles with any edge longer than `max_edge`; no interpolation is permitted in rejected triangles or outside accepted support. CSV gaps are controlled by this edge limit rather than inferred as fully surveyed waterway. GeoTIFF NoData holes are retained as explicit masks/geometry. Intersect measured support with reference support and optional boundary.

A centre-based TIN does not retain the full outer pixel footprint of an input raster. A maximum edge alone cannot identify every unobserved hole or preserve canal breaklines; supply a boundary/hole mask and inspect the maps. The same maximum edge applies to both surfaces.

Linear TIN is the project baseline because it is understandable, supported by available inputs, avoids variogram fitting and reproduces planar beds. This is a practical selection, not demonstrated universal superiority over kriging/IDW. See [the evaluation](OPEN_SOURCE_EVALUATION.md) and the project's [baseline rationale](OPEN_SOURCE_EVALUATION.md).

## 4. Common grid and integration

Construct one axis-aligned grid at the user cell size, with origins snapped to integer multiples of that size in the declared CRS. For every square cell, compute its exact plan-area intersection `A_i` with common supported geometry. Include partial cells even when their nominal centre is outside support. Sample full cells at their centres and partial cells at the clipped area's centroid. If a concave/disconnected fragment's centroid lies outside the support, use an interior representative point.

Construct georeferenced masked GeoUtils rasters. The GeoUtils reprojection/alignment call is an identity-grid consistency step here: both surfaces were already sampled on that grid. GeoUtils performs the checked masked subtraction and writes the GeoTIFFs.

With positive-up elevations, let `d_i = bed_i − reference_i`:

```text
V_above = Σ A_i × max(d_i, 0)
V_below = Σ A_i × max(−d_i, 0)
V_net   = V_above − V_below
```

Both above and below volumes are reported as non-negative magnitudes; net volume is signed. Positive clipping does not cancel dredging candidates against deeper areas. Coverage is supported integrated area divided by boundary area, or by the measured TIN bounding-box area if no boundary was supplied. NoData is excluded, never zero-filled.

This is **grid quadrature**, not exact integration of every intersecting TIN facet. A centroid sample is exact for an affine signed surface over a clipped area, but a cell may cross multiple facets or a positive/negative zero crossing. An interior fallback is also approximate. Change grid size to assess sensitivity; exact partial areas alone do not make the volume exact. Plot squares show the values at their regular grid locations; `cells.csv` additionally records actual sample XY.

## 5. Interpretation and uncertainty

| Reference | What above-reference volume means |
|---|---|
| Design level/surface | Material above the declared target; a potential dredging volume. It may include material other than sludge. |
| Earlier surveyed surface | Positive bed-level change over common support. It is not necessarily deposited sludge; erosion, bed movement and survey differences matter. |
| Measured sediment underside | A geometric thickness/volume estimate conditional on that interface being correctly identified and independently validated. The app cannot establish that itself. |

Only design references may use an assumed constant. Other types require an input surface and provenance.

Optionally supply **both** independent per-surface vertical standard deviations. The app computes `LoD95 = 1.96 × sqrt(sigma_current² + sigma_reference²)` and reports volumes from cells where `|d_i| > LoD95`. It retains the full measured difference in those selected cells. This assumes independent, unbiased Gaussian errors and ignores spatial correlation/systematic bias. It is not a confidence interval for volume, and it does not establish measurement accuracy. Missing uncertainty generates a warning; the real RWS demo supplies none.

## 6. Reproducibility

The 3D preview adjusts the scene's vertical aspect ratio for visibility while
retaining original metre elevations in the surface arrays, axis labels and
hover values. Auto targets a vertical scene span near 32% of the longest
horizontal span, bounded to 1–100×; an effectively flat surface uses 1×.
The factor is shown in the interface and can be set explicitly, including 1×
true proportions. It is a display preference, not an input to integration or
exports. Perspective, contour lines and lighting help show the actual shape;
they do not supply additional measured detail.

The JSON export records all parameters, source hashes, reference assumption, user-declared datum status, upstream commit and source metadata. `cells.csv` supplies the supported integration areas. `points.csv` supplies deduplicated values and flags. The independent real-data verifier and analytical tests are documented in [VALIDATION.md](VALIDATION.md).
