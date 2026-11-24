# Reviewing a Hydromagic project export

The application starts with corrected XYZ. A native Hydromagic project can help
check how those coordinates were produced, but the project ZIP is not itself a
validated bed surface. Select a matching processed export and keep the raw and
modified records separate.

## Diagnostic export-pair reviewer

`scripts/review_hydromagic.py` cross-checks an explicitly paired PointZ/XYZ export
and a processed `SNDG...` file. This supports a **specific observed 24-token
Hydromagic 12.0 SND layout**. The field relationship was inferred from the
provided matching files, rather than an authoritative general sounding-file
specification. It is a diagnostic aid that needs provider confirmation.

The tool requires matching record counts and row-by-row XY correspondence. It
then checks whether every exported Z matches the observed correction-minus-depth
relationship, or a depth-like fallback when the correction equals the file's
`NDT` marker. A 0.0011 m comparison tolerance accommodates the two rounded
three-decimal text operands. It is not a survey-accuracy claim. Unsupported
versions, row order, layouts or numerical relationships are rejected before
candidate files are written.

It produces:

- `original_export_xyz.csv`: every original XYZ value, unchanged.
- `row_review.csv`: the source row, recorded UTC time, original Z, observed
  depth/correction fields and the reason for withholding a row.
- `candidate_elevation_points.csv`: original XYZ rows whose observed correction
  is present. This is a review subset, not validated bathymetry.
- `review.json`: checksums, numerical agreement, counts, assumptions and limits.

The withholding rule uses the missing-correction marker. It does **not** discard
all positive elevations. Positive elevations with an available correction remain
in the candidate file, as tested with synthetic data. No missing height is
reconstructed or substituted from another GNSS field.

Example, after unpacking and identifying a matching pair locally:

```sh
.venv/bin/python scripts/review_hydromagic.py \
  "path/to/processed-survey.zip" \
  --sounding "path/to/SNDG00001" \
  --crs EPSG:28992 --vertical-datum NAP \
  --output runs/survey-review
```

Confirm that the provider exported the paired observations as elevations in NAP.
The diagnostic performs no vertical transformation. The original archive, raw logs and generated
review files stay outside the application repository.

## Verification

`tests/test_hydromagic_review.py` checks missing corrections, retention of valid
positive elevations, unchanged source values, text rounding, unsupported versions,
wrong revisions, row order and Z mismatches. These software checks use synthetic
inputs and do not establish field accuracy.

## Primary technical references

- [Hydromagic raw record format](https://www.eye4software.com/hydromagic/documentation/articles-and-howtos/raw-data-storage-format/)
- [Generating corrected soundings](https://www.eye4software.com/hydromagic/documentation/manual/single-beam-processing/generate-soundings/)
- [Hydromagic echo-envelope BIN format](https://www.eye4software.com/hydromagic/documentation/articles-and-howtos/bin-data-storage-format/)

The raw-record and BIN documentation describes those formats, not a complete
mapping of the processed SND fields used by this diagnostic. Keep that distinction
when interpreting the results.
