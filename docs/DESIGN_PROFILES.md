# Reconstruct a straight canal design

EASE creates a 3D wetted design from a standard profile and a constant
design water level. It places the design across one straight reach in
RD New and compares it with survey elevations in metres NAP.

| Code | Flat bed width | Depth below design water level | Underwater slope | Width at design water level |
|---|---:|---:|---:|---:|
| L8 | 5.30 m | 1.20 m | 1 vertical to 2 horizontal | 10.10 m |
| L8a | 2.30 m | 1.50 m | 1 vertical to 2 horizontal | 8.30 m |
| L10 | 7.00 m | 1.20 m | 1 vertical to 2 horizontal | 11.80 m |

Dimensions come from Waterschap Zuiderzeeland drawing W-A-AL-001,
sheet 1, revision C (21 September 2017). The reconstruction models the base
wetted trapezoid. Site-specific berms, bank protection, structures,
bends and changes in design elevation require additional geometry.
The [Zuiderzeeland legger policy, section 4.4](https://repository.officiele-overheidspublicaties.nl/externebijlagen/exb-2024-44238/1/bijlage/exb-2024-44238.pdf)
describes where the authority records a centreline and profile assignment.

## In the web app

1. Upload a processed PointZ ZIP or XYZ point file in RD New
   (EPSG:28992) with positive-up elevations in m NAP.
   To screen a matching Hydromagic export, select **Preprocess survey
   with Hydromagic SND**, upload its SND file, and click **Preprocess and
   inspect survey**. The preview reports retained and excluded soundings.
   The same screening applies when you run the comparison.
2. **Standard design profile** is the default reference for survey
   uploads. Select a code and enter the signed
   design water level. With L8 and `-5.70`, the flat bed is
   `-6.90 m NAP`. Mark the level confirmed only when it applies to the
   selected reach.
3. For **Single survey track**, enter design endpoints or fit the
   alignment to a straight centreline survey. Confirm corrected NAP
   heights, or use the SND screening in Step 01 for a provisional
   comparison. This mode
   shows the 3D overlay, along-reach elevations and point differences.
4. For **Survey across the canal**, enter design endpoints in RD New and
   confirm the retained survey heights in Step 01. The app adds a measured bed display and
   calculates volumes over the overlap of the surveyed and design areas,
   clipped to any selected area or boundary. By default, the coverage
   percentage uses the full design footprint as its denominator.

The app evaluates the standard profile directly at the calculation
locations. The surface method and triangle limit apply to the surveyed
bed, while the design has a flat bottom and planar slopes. Volume still
uses the app's grid approximation. Check cell size sensitivity near
slope breaks and where the survey crosses the design elevation.

Both modes export the design XYZ, point comparison CSV and a summary in
the ZIP. Area mode also exports the standard grid, volume and raster
results. The point comparison shows individual observations, while the
volume applies the selected outlier and coverage settings. The reference
XYZ export uses up to 1 m spacing and is limited to 100,000 points.

The fitted alignment and matching SND review are provisional. The SND
diagnostic checks the observed Hydromagic 12 file layout and withholds
points with missing corrections. Confirm the survey heights and actual
design geometry before using the comparison for decisions.

## Standalone command

After running `./setup.sh`, run from the repository root:

```sh
.venv/bin/python scripts/reconstruct_reference.py path/to/pointz.zip \
  --sounding path/to/SNDG00001 \
  --profile L8 --water-level-nap=-5.70 --track-is-centreline \
  --output runs/l8-review
```

Pass the signed **design** water elevation. With `-5.70` and L8 the flat
design bed is `-6.90 m NAP`. Use the level confirmed for the reach and add
`--design-level-confirmed` when you have that confirmation.

`--track-is-centreline` declares that the survey ran along the canal
centre. The script fits a straight line to the XY locations, checks that
the track is at least four times as long as its observed width and fits
within the modelled flat bottom, and rejects gaps over 25 m in the
alignment inputs. The design is displayed around this fitted line
and flagged as provisional. Each sounding is compared with the flat
design bed. The exported XY and Z retain their original values.

`--sounding` checks the pairing with the existing
[Hydromagic review](HYDROMAGIC_REVIEW.md) and withholds rows whose
height correction is missing. The comparison remains provisional.
For a corrected PointZ ZIP or XYZ file whose NAP elevations the provider
has verified, pass `--verified-nap` in place of `--sounding`.
Use corrected positive-up elevations. The command performs no vertical
transformation or processing of raw sonar.

### Design endpoints and an area survey

Supply the design centreline and reach limits together as
`--centreline X1 Y1 X2 Y2` in RD New metres for a straight reach. The
comparison evaluates the design at each sounding's lateral offset and
leaves values outside the design footprint blank in the CSV.

With verified NAP elevations, design endpoints and actual survey
coverage across the canal, pass `--measured-max-edge METRES` to overlay a
linear TIN of the measured bed. Choose the limit based on survey spacing
and gaps. The command uses the same bounded-triangle rule as the app.
For a single boat track, omit this option and inspect the sounding
points. To estimate a volume for the full reach, collect adequate
cross-canal measurements and review the supported area before using the
app's volume calculation. See [SIKB 2501, sections 5 and 7](https://www.sikb.nl/doc/Richtlijn_Baggervolumebepalingen_V2.1.pdf).

### Outputs

- `comparison.html` contains the interactive 3D overlay and a longitudinal
  elevation plot. The 3D view states its display scale.
- `comparison.csv` contains the accepted XYZ soundings, along-reach
  distances, offsets and signed differences. Positive values indicate
  material above design.
- `reference_xyz.csv` is the reconstructed design sampled at up to 1 m
  spacing by default. Use `--spacing` to adjust it. It preserves the
  transitions between the flat bed and the slopes. The web app accepts
  it as a file reference in RD New/NAP. The app reconstructs it through
  the chosen surface method, so use linear TIN to retain straight design
  slopes and check the coverage settings. Keep the summary with the CSV.
- `summary.json` records the dimensions, water elevation, fitted or
  supplied alignment, source hash, survey review and whether the result
  is provisional.

The output directory must be new. Store private survey files and outputs
under ignored locations such as `local_data/` and `runs/`.
