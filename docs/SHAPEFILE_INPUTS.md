# Processed sonar shapefiles

The application can read one **PointZ shapefile in a ZIP**. This supports processed survey exports whose 3D coordinates already exist. It does not process raw sonar recordings.

## Import and inspect

1. Upload the ZIP in **Measured waterbed**.
2. Declare the actual horizontal CRS, height datum and Z convention.
3. Click **Inspect survey without a reference**.
4. Rotate the **3D points** view to review the elevations. Amber marks readings above datum zero. **Auto** exaggerates height and displays the scale factor. Choose **1×** for true proportions. Inspection computes no volume.
5. Switch to **Plan view**, zoom to a short reach and click **Use visible map area**, or enter its coordinate bounds manually.
6. Supply an actual reference, or a clearly labelled assumed design, before running a comparison.

For narrow coverage, **Bed surface · 3D** can show the covered parts of accepted cells as individual surface patches. Each patch uses the bed and reference heights calculated for its cell. Gaps in survey coverage remain empty. Use **Zoom to patch** to inspect a small area of the surface.

The ZIP must contain exactly one `.shp` and matching `.shx`, `.dbf` and `.prj` files. An optional `.cpg` is supported. Nested folders and uppercase extensions are accepted. Loose `.shp` files, multiple layers, 2D points, lines and polygons are rejected. This importer does not interpret an attribute as height or infer heights from a coloured drawing.

X, Y and Z come from geometry. `name` and `transducer` are ordinary attributes. Their values are not dates, frequencies, confidence estimates or sediment classes unless the survey provider documents that meaning. The importer records the layer, CRS, attributes, source hash and height source in result provenance.

The height datum remains a declaration. A shapefile `.prj` can identify RD New but does not by itself establish NAP, sonar correction quality or survey accuracy. Positive-up and positive-down declarations behave like the other input formats. Changing the sign convention is an explicit conversion.

## Area selection

`analysis_bounds` is `[xmin, ymin, xmax, ymax]` in the declared survey CRS. Both surfaces use only observations inside that box. The app then intersects their supported area with the box and any uploaded boundary. This conservative selection can lose edge coverage because it does not use observations outside the box as a halo. `input_points`, `selected_points`, `outside_analysis_area_points` and `accepted_points` distinguish the stages.

Long or curved routes can have huge bounding rectangles. A 1 m grid over the entire route is often inappropriate for this prototype. Use a short reach. The preview estimates the bounding-grid size but does not claim that the rectangle is fully surveyed. Keep gap masks and inspect the actual supported area.

## Local XYZ conversion

The helper preserves float64 coordinates using 17 significant digits and leaves the original ZIP untouched:

```sh
.venv/bin/python scripts/inspect_survey.py \
  "path/to/processed-survey.zip" \
  --crs EPSG:28992 --vertical-datum NAP \
  --output runs/survey-inspection
```

This creates `survey_xyz.csv` and `inspection.json`. The example assumes the provider confirmed NAP elevations. Optional `--bounds xmin ymin xmax ymax` restricts the exported points, with that choice recorded in the report.

## What to request from the survey provider

- A full XYZ, PointZ ZIP or single-band elevation GeoTIFF for one short canal reach, with the original survey coverage retained. Confirm whether this GeoWeb export is thinned to tracks.
- The matching official design profile or earlier survey, depending on the intended comparison. A sludge underside is a different input and needs independent identification.
- Survey date including year, metre units, horizontal CRS, vertical datum and sign convention, plus the correction and quality record.
- The meaning of the three `SNDG...` names and the positive heights. Keep such observations until their interpretation is known.

Raw sonar files are useful for studying acquisition and processing, but are not required by this downstream app when validated 3D survey coordinates are already available.
