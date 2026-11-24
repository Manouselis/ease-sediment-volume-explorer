# Real Dutch demonstration data

The bundled current bed is **genuine measured-data-derived bathymetry** from
Rijkswaterstaat. It is a small, fully populated 60 × 200 m crop of the
Amsterdam–Rhine Canal near Utrecht. The reference is an **assumed flat design**
at −6.5 m NAP. Consequently this demo estimates material above that assumed
design; it does not measure sludge thickness, sludge composition, or change
between surveys.

## Source and provenance

- Dataset: [Bathymetrie Nederland — binnenwateren 1 mtr — april 2025](https://maps.rijkswaterstaat.nl/dataregister-publicatie/srv/api/records/1d23ce9d-a11a-4e56-9538-c6f4c8a0fb77).
- Publisher: Rijkswaterstaat / RWS Centrale Informatievoorziening (CIV).
- [Primary ISO metadata record](https://maps.rijkswaterstaat.nl/dataregister-publicatie/srv/api/records/1d23ce9d-a11a-4e56-9538-c6f4c8a0fb77/formatters/xml).
- License: [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/), stated in the primary metadata and Dutch government catalogue.
- Horizontal coordinates: **Amersfoort / RD New, EPSG:28992, metres**.
- Vertical coordinates: **NAP height, EPSG:5709, metres, positive upward**.
- Snapshot/publication date: **23 April 2025**. This is not the acquisition date of every source sounding. Individual survey dates are unavailable in this subset.
- Official lineage states that the product aggregates multibeam soundings from Rijkswaterstaat's national sounding storage. Each 1 m² cell contains the average of measured points in that cell.
- The source marks this product as unsuitable for navigation.

These are **raster cell-centre samples of measured cell means**, not the original
individual sonar returns. The demo neither invents bathymetry nor tests raw
sonar processing. The source does not supply sensor-model details, per-cell
uncertainty, or a verified sediment underside.

## Files

| File in `data/` | Meaning |
|---|---|
| `demo_current.csv` | 12,000 current-bed XYZ cell-centre samples; no added perturbations. |
| `demo_reference.csv` | Same XY locations, with an explicitly hypothetical −6.5 m NAP design elevation. |
| `demo_boundary.geojson` | Original raster pixel-edge rectangle in EPSG:28992; not a surveyed canal boundary. |
| `demo_metadata.json` | Source URLs, license, datums, snapshot status, settings, bounds, limitations and SHA-256 hashes. |
| `demo_rws_wcs.txt` | Exact small WCS response used to construct the CSV. |
| `demo_rws_metadata.xml` | Downloaded primary source metadata, including lineage and license. |
| `demo_rws_coverage.xml` | Downloaded WCS coverage description, including CRS, resolution and NoData. |

The GeoJSON uses the older explicit `crs` member because these coordinates are
projected RD metres. It must not be treated as RFC 7946 longitude/latitude.

## Reproduce the download and conversion

From the repository root, using any Python 3.10+ interpreter:

```sh
python3 scripts/download_demo.py
```

For a fully offline reconstruction using the checked-in source files:

```sh
python3 scripts/download_demo.py --offline
```

The downloader needs only Python's standard library. Its WCS request fixes the
April 2025 coverage and asks for a native 1 m subset around RD bounds
`133875,455250,133935,455450`. The service snaps those bounds to its native grid.
The converter uses the returned affine transform and global grid indices to
locate **pixel centres**, checks them against the returned pixel-edge bounds,
and excludes the declared NoData marker. No horizontal reprojection, vertical
transformation, regridding or filtering occurs during conversion.

An offline rerun preserves the original retrieval timestamp. A new online run
records the new retrieval time and hashes, so future upstream changes remain
visible. Checked-in CSV numeric formatting does not imply millimetre or
micrometre survey accuracy.

## Numerical check independent of the application's TIN

All 12,000 source cells are valid and have area 1 m². On **this original source
grid**, direct integration against the assumed −6.5 m design gives:

| Quantity | Direct source-grid result |
|---|---:|
| Valid cell area | 12,000 m² |
| Cut above assumed design | 2,672.86 m³ |
| Deficit below assumed design | 867.25 m³ |
| Net difference | 1,805.61 m³ |

Reproduce that separate arithmetic without importing the application:

```python
import csv

with open("data/demo_current.csv", newline="") as stream:
    values = [float(row["z"]) + 6.5 for row in csv.DictReader(stream)]
print("cut", sum(max(dz, 0.0) for dz in values))
print("deficit", sum(max(-dz, 0.0) for dz in values))
```

**Compare like areas.** The original grid covers full pixel areas, while a TIN
through cell centres has an outer boundary half a pixel inside the original
pixel-edge footprint. The application's grid origin, common valid support,
triangle-length checks and cleaning decisions may further change the accepted
area. Its result should be checked against independent integration over that
same accepted footprint; it should not be forced to match the larger source
grid's total.

The initial 1 m cell size and 2.5 m maximum triangle edge suit this complete,
regular source subset. They are not justified defaults for unprocessed ECHO
recordings or an unrelated sparse survey. The 1 m source resolution is not a
statement of vertical accuracy. Any uncertainty scenarios in the application
are user assumptions unless independently established by survey evidence.
