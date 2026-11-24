# Numerical verification and validation limits

The application has been checked against analytical geometry and a genuine
Dutch bathymetry subset. These checks establish **numerical consistency of the
implemented surface-comparison calculation**. They do not establish field
accuracy, detect a real sludge underside, or validate Sonoptix ECHO processing.

## Reproduce the real-data verification

From the repository root, after installation:

```sh
.venv/bin/python scripts/run_demo.py
.venv/bin/python scripts/verify_demo.py
```

Alternatively, `scripts/verify_demo.py --rerun` first regenerates the default
`demo_output/` run. Without that flag it checks existing exports, or generates
them if they are missing. It writes
`demo_output/independent_verification.json` with its results and tolerances.
`--run-directory PATH` can check an existing export of the same bundled demo.

The verification script does **not** import the application core, GeoUtils,
`LinearNDInterpolator`, Rasterio, or Shapely. It independently:

1. Checks the bundled source-file SHA-256 values and the run's source hash.
2. Reads the original current-bed CSV and reconstructs its Delaunay triangles.
3. Confirms that all original points were retained and every triangle satisfies
   the configured maximum edge length. Those conditions make the convex hull a
   valid support boundary for this complete demonstration subset.
4. Clips each grid square against the source hull and requested boundary using
   a separate Sutherland–Hodgman convex-polygon implementation.
5. Calculates supported areas and partial-cell centroids with explicit
   shoelace formulas, using a shifted coordinate origin to reduce cancellation.
6. Evaluates bed heights from explicit barycentric triangle weights, then
   subtracts the assumed design height.
7. Independently sums positive and negative differences times clipped areas
   using `math.fsum` and checks every exported cell's validity, position,
   sample position, elevation, difference, and supported area.

**Shared dependency:** both calculations use SciPy/Qhull for Delaunay
connectivity and point location. This is separate verification of the
interpolation, clipping and integration arithmetic, not an independent
implementation of the triangulation engine itself. The checker is deliberately
scoped to this convex, complete demo footprint; it asserts its assumptions and
does not claim to validate arbitrary boundaries with holes or excluded
triangles.

## Verified real-data result

Source: 12,000 genuine multibeam-derived 1 m cell means from Rijkswaterstaat's
April 2025 national bathymetry snapshot. Coordinates are RD New / NAP. Reference:
**hypothetical flat design at −6.5 m NAP**. See [REAL_DATA.md](REAL_DATA.md) for
the source, license, survey-date limitations and exact download procedure.

| Quantity | Application | Independent computation |
|---|---:|---:|
| Cut above assumed design | 2,616.673785146473 m³ | 2,616.673785146509 m³ |
| Deficit below assumed design | 829.907363136496 m³ | 829.907363136465 m³ |
| Net bed volume relative to design | 1,786.766422009977 m³ | 1,786.766422010044 m³ |
| Common valid area | 11,741 m² | 11,741 m² |
| Requested source-raster footprint | 12,000 m² | 12,000 m² |

The check covers 12,261 output-grid cells, including 12,000 valid cells and
516 partially covered cells. It reconstructs 23,482 triangles. The largest
bed-elevation disagreement is approximately **2.27 × 10⁻¹¹ m**; the largest
supported-area disagreement is **zero**. Absolute volume disagreements are
below **4 × 10⁻¹¹ m³**. Verification tolerances are 10⁻⁸ m for coordinates and
elevations, 10⁻⁷ m² for area, and 10⁻⁶ m³ for volume.

These tiny discrepancies describe floating-point agreement between
computations. They are **not bathymetric measurement accuracy or volume
confidence limits**. A practical display should round totals, while exported
precision supports numerical reproduction.

### Why the original raster sum differs

Directly summing the original 12,000 source cells against the same assumed
design gives **2,672.86 m³ cut** and **867.25 m³ deficit** over **12,000 m²**.
That calculation retains the original full pixel areas and cell-mean heights.

The application's TIN joins source **cell centres**. Its hull spans
59 × 199 m = **11,741 m²**, leaving 259 m² of outer half-pixel strips unsupported.
The application also samples an aligned common grid through the interpolated
TIN, with centroids used for partial cells. Both the footprint and the
representation therefore differ from the original cell-mean raster sum.
The original sum cannot be compared identically to the application's total
or used as field ground truth. The independent check compares the **same
supported footprint and quadrature convention** instead.

## Analytical checks

Run the test suite with:

```sh
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests -q
```

`tests/test_independent.py` includes known-volume flat beds, an analytically
integrable sloping plane, separate positive/negative volumes, intersection of
two survey footprints, polygon holes, unsupported long-triangle gaps,
no extrapolation beyond the hull, partial cells whose nominal centres lie
outside the boundary, clipped-cell centroid integration, raster NoData,
duplicate observations, depth/elevation sign conventions, metadata rejection,
and explicit outlier flagging versus exclusion.

Disabling automatic pytest plugin discovery isolates this project's tests
from unrelated plugins installed on the host, including ROS testing plugins.
On 26 October 2026 the expanded application test suite passed **75 tests** in this environment.
The remaining warnings were dependency deprecation notices.

These synthetic analytical cases test geometry and safeguards. They complement
the measured-data demonstration; neither substitutes for independent field
control. Tests cover defined cases rather than every possible survey geometry.

## Browser interface checks

Start the application with `./run.sh`, then, from the repository root, run the
optional Playwright check in a separate terminal:

```sh
node scripts/ui_smoke.cjs
```

This requires the Node.js `playwright` package and a compatible browser. If
Playwright is installed outside the normal Node module search path, set
`NODE_PATH=/path/to/node_modules`. The script uses `/usr/bin/google-chrome`
when available; `CHROME_EXECUTABLE` can select another Chromium executable,
and `EASE_URL` can select another local application address.

The script exercises the genuine bundled RWS demonstration and a real CSV
upload with a reference file. It checks all three chart views in English and
Dutch, matching translation keys, translated errors and accessibility labels,
retained results after language changes, invalidated exports after settings
changes, the JSON download, rejection of an invalid CSV, and mobile/tablet
horizontal overflow. It also checks that non-design references require a
reference file. Screenshots are written to `qa/`, and successful completion
prints a JSON report with `status: "passed"`.

These checks cover the scripted browser paths. They do not establish full
accessibility conformance, every upload format in the browser, or performance
across devices. GeoTIFF and additional validation paths are covered by the
backend tests rather than this browser script.

The application was also checked directly in the Codex in-app browser after
restarting the local server. The real-data example completed with the same
totals. Switching EN/NL retained the result and export URLs. Changing the
assumed design elevation updated its automatically generated description;
switching language translated that description in both the form and results.
User-written descriptions remain unchanged. A running-app screenshot is saved
in [the application preview](images/application.png). Generated QA captures are excluded from version control. The backend suite was rerun successfully: 43 tests.

## 3D display regression, 13 October 2026

The revised 3D view was visually inspected in the in-app browser and in desktop
and mobile captures. Manual dragging rotated the bed; reset restored its
camera. The complete browser smoke test passed, including perspective, visible
height ticks and contours, Auto relief, explicit 1×/5×/10×/20×/50× factors,
EN/NL controls, mobile/tablet layout and flat/steep synthetic display cases.
It independently checked scene aspect ratios against coordinate spans and
verified that changing scale preserved elevation arrays, numerical results and
export URLs. Camera reset was tested after a programmatic camera change;
physical dragging was verified manually. No unexpected browser errors occurred.

The genuine RWS example selected 26× in Auto and retained 2,616.7 m³ above,
829.9 m³ below and 97.8% coverage in the displayed summary. The backend suite
also passed all 43 tests. Vertical exaggeration changes the presentation only;
it does not increase measurement accuracy or change exported heights/volumes.
See [the 3D preview](images/bed-surface-3d.png).

## Remaining approximation and field validation

The volume implementation uses common-grid quadrature: one supported sample
per cell multiplied by supported plan area. Centroid sampling is exact for a
single affine plane over a convex clipped cell. A cell can cross several TIN
triangles or the reference intersection, so real-data cut/deficit totals remain
a grid approximation. The independent checker verifies that approximation's
implementation; it does not prove equality to an exact polygon-by-polygon
integral. Grid-size sensitivity is appropriate before decision use.

The public source has already undergone hydrographic processing and averaging.
It supplies no per-cell uncertainty or independent control observations here.
Accordingly this demonstration establishes none of the following:

- Sonoptix ECHO's ability to produce validated bathymetric XYZ.
- Correctness of timing, positioning, attitude, sound-speed or water-level
  corrections on a new acquisition.
- Real sludge composition, sludge-layer thickness, or deposition between dates.
- Physical validity of the hypothetical −6.5 m design.
- Measurement accuracy, a detectable-change threshold, or a confidence
  interval on total volume.

Before operational use, obtain survey/control evidence, an authoritative
reference with matching datum, documented uncertainty and repeat-survey or
independent check measurements. Compare alternative grid spacings and inspect
coverage, bank transitions, survey-line offsets and flagged observations.
For actual sludge thickness, independently establish the layer's underside.


## Processed PointZ and Hydromagic checks

The PointZ tests use synthetic shapefiles to verify coordinates, CRS checks,
enforced coverage and comparison against a known reference. Synthetic
Hydromagic export pairs check row alignment, rounded fields, valid positive
elevations and missing height corrections. See [the Hydromagic guide](HYDROMAGIC_REVIEW.md).

## Ordinary Kriging addition, 30 October 2026

The full backend suite passes **98 tests**. New cases independently solve small
ordinary-Kriging semivariogram systems for spherical, exponential and Gaussian
models. They check exact observation values, nonnegative variance, automatic-fit
reproducibility, manual parameters, known constant-height volumes, partial-cell
sample positions, file-reference processing, search-radius and standard-error
exclusions, disconnected coverage, polygon/raster holes, numerical errors, size limits and API bundles.
A regression compares default and explicitly selected TIN outputs.

The bounded-memory test observes that no fitting constructor receives over 512
points and no prediction constructor over the configured local neighbour count.
The installed PyKrige source was inspected: its constructor uses pairwise
`pdist`, and execute builds a full matrix for its input data. EASE bounds those
inputs rather than relying on its global moving-window option.

The genuine browser checks exercised public RWS data, automatic and manual
Kriging, TIN switching, English/Dutch translations, the difference and 3D views,
uncertainty rendering, stale-result/export invalidation, and an insufficient-radius
error with no fallback. Summary and bundle downloads were saved and inspected.
The Kriging bundle contains both bed uncertainty TIFFs and cell uncertainty,
validity, exclusion reason and geometric area. The initial browser download-event
wait timed out. The documented direct-download operation then succeeded.
This does not imply that the standalone historical Playwright script was rerun.

Figures were visually checked and saved under `docs/images/kriging-*.jpg`.
The original workflow SVG and PNG were rendered and inspected. The compact
comparison and withheld-strip results, full-demo timing and limitations are in
[KRIGING.md](KRIGING.md). Reproduce with `scripts/compare_surfaces.py`.
These checks do not validate survey heights or actual sludge volume.
