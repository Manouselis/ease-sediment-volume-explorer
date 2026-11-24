# EASE web deployment

GitHub `main` is the application source. The [published explorer](https://manouselis.github.io/ease-sediment-volume-explorer/explore/) opens directly to the survey upload and processing form. The first inspection or calculation downloads a WebAssembly runtime. The page stays responsive while a worker runs the shared Python analysis. Worker files and results live for the current tab session.

The site also ships two example results from [public Rijkswaterstaat bathymetry](https://maps.rijkswaterstaat.nl/dataregister-publicatie/srv/api/records/1d23ce9d-a11a-4e56-9538-c6f4c8a0fb77) under CC0. Both use a hypothetical −6.50 m NAP design and a 1 m calculation grid. The 3D image shows the TIN result at 26× vertical exaggeration. [Build information](https://manouselis.github.io/ease-sediment-volume-explorer/build.html) links to the deployed GitHub commit.

## Build and preview

From the checkout with the usual dependencies installed:

```sh
.venv/bin/python scripts/bundle_plotly.py
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/build_pages.py dist/preview/ease-sediment-volume-explorer
python3 -m http.server 8790 --bind 127.0.0.1 --directory dist/preview
```

Open [the preview](http://127.0.0.1:8790/ease-sediment-volume-explorer/). Run `python scripts/make_browser_fixtures.py`, then `node scripts/pages_smoke.cjs` with Playwright and Chrome. Set `EASE_PAGES_URL` to check a different preview or the live site. The screenshot is distributed as WebP. The build publishes only the assembled client, public demo inputs and calculated demo exports.

## Browser runtime

The Pages build packages Pyodide 314.0.8, the required libraries from its locked release, the pinned GeoUtils source and the shared EASE code. The worker uses the same validation, TIN, PyKrige, design profiles, volume integration and export handlers as the local app. It uses Fiona to read PointZ, and writes lossless LZW GeoTIFFs. Tifffile handles Deflate-compressed data when the browser build of Rasterio cannot decode it. Use the native app for GeoTIFFs that require unsupported codecs or when browser memory limits prevent a run.

The Chromium smoke test starts with the direct upload form, runs TIN and Kriging in the worker, reads PointZ and a compressed masked GeoTIFF, screens a matching SND, and checks exports. The source data is public or synthetic. The protected FastAPI container remains available for separate native deployments through `deploy/Dockerfile`.

## Automatic releases

Push reviewed changes to GitHub `main`. The [Pages workflow](https://github.com/Manouselis/ease-sediment-volume-explorer/actions/workflows/pages.yml) runs Python tests, builds the static demo, and smoke-tests it in Chromium before publishing. Pull requests run the same checks. The workflow verifies that the public release marker reports the exact deployed commit.

To retry, rerun the latest workflow from the Actions tab. To roll back a release, revert the relevant source commit on `main`. GitHub Actions then tests and publishes the reverted code.

## Optional Bitbucket mirror

The private repository retains its original project history. If you keep it as a separate Git remote named `bitbucket`, you can mirror the clean GitHub history on a separate branch with `git push bitbucket main:github-mirror`. Use GitHub `main` for development and releases.
