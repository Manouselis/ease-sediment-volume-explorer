# EASE web deployment

GitHub `main` is the application source. The [GitHub Pages project](https://manouselis.github.io/ease-sediment-volume-explorer/) receives an allowlisted static build and two saved calculations from the public [Rijkswaterstaat dataset](https://maps.rijkswaterstaat.nl/dataregister-publicatie/srv/api/records/1d23ce9d-a11a-4e56-9538-c6f4c8a0fb77) under CC0. Both use the same hypothetical −6.50 m NAP design and 1 m calculation grid. The 3D image is from the public TIN result at 26× vertical exaggeration. The repository root `release.json` records the tested GitHub commit.

The public demo includes interactive plots and ZIP, CSV, TIFF and JSON exports. It uses saved results. The URL preserves the active surface method for sharing or refreshing. Changing survey files or configuration takes a running analysis server. The existing localhost launch uses its original settings and does not require a key.

## Build and preview

From the checkout with the usual dependencies installed:

```sh
.venv/bin/python scripts/bundle_plotly.py
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/build_pages.py dist/preview/ease-sediment-volume-explorer
python3 -m http.server 8790 --bind 127.0.0.1 --directory dist/preview
```

Open [the preview](http://127.0.0.1:8790/ease-sediment-volume-explorer/). Run `scripts/pages_smoke.cjs` with Node.js, Playwright and Chrome. Set `EASE_PAGES_URL` to check a different preview or the live site. The screenshot is distributed as WebP. The build publishes only the assembled client, public demo inputs and calculated demo exports.

## Protected analysis API

The hosted container uses the same Python dependencies and calculation engine as localhost. It adds an exact browser origin allowlist, individual access keys, one admitted analysis or inspection at a time, a multipart size check, and an isolated results directory per job. Results require the originating key and expire after one hour or when the 12-result capacity is reached. Original uploads are removed after request processing. Host restarts can drop results sooner. Result bundles include derived survey points and should be handled as survey data.

Deploy `deploy/Dockerfile` from GitHub `main` with build context at the checkout root and the pinned GeoUtils submodule initialized. CPU, ingress and memory must be verified on the actual host. Start with one worker and one instance, HTTPS, capped resource use, ephemeral storage, and no proxy body or header logs. Render’s Git integration can deploy **After CI Checks Pass** from GitHub, subject to provider authorization, plan limits and access. Use a deployment account and region approved for the project.

Set these environment values on the host:

| Setting | Value |
| --- | --- |
| `EASE_PAGES_ORIGIN` | `https://manouselis.github.io` |
| `EASE_ACCESS_KEY_HASHES` | Comma-delimited SHA-256 hex digests of distinct high-entropy random project keys. Share the original keys with approved operators using an approved channel. |
| `EASE_RELEASE` | Optional full source SHA on platforms that do not provide `RENDER_GIT_COMMIT`. |
| `EASE_RUNS_DIR` | Optional writable ephemeral directory. Defaults to `/tmp/ease-results`. |

Set `GET /api/health` as the health check. Verify the reported commit over HTTPS. Before enabling the browser UI, test a 100 MiB public or synthetic survey, the supported import types, representative TIN and Kriging runs, and export sizes through the actual proxy. Provision enough ephemeral disk for multipart buffering, temporary inputs and result bundles. An unsuitable plan must not be compensated for by quietly reducing application limits. The project origin is shared by other Pages projects under the account. The access key remains the authorization boundary and is stored only in the current page's memory.

## Local deployment checks

The 512 MiB, half-CPU Linux container accepted a 100 MiB CSV containing public demo observations plus comment padding. The test checks the multipart size and inspection path. The representative 12,000-point analysis took about 5 seconds with TIN and 15 seconds with Kriging. Both matched the local baseline within 0.00000001 m³ and covered 11,741 m². The container recorded a peak of about 345 MiB across these runs. Larger or more complex surveys and production ingress still need verification on the chosen host.

The automated browser check opens the release under the project path, switches maps and languages, checks a page refresh and saves an export. With a locally connected API and a test access key, it also checks invalid keys, server outages, upload inspection, calculation and private downloads. `tests/test_hosted.py` checks expiry and file cleanup.

## Automatic releases

Push reviewed changes to GitHub `main`. The [Pages workflow](https://github.com/Manouselis/ease-sediment-volume-explorer/actions/workflows/pages.yml) runs Python tests, builds the static demo, and smoke-tests it in Chromium before publishing. Pull requests run the same checks. The workflow verifies that the public release marker reports the exact deployed commit.

The optional GitHub Actions repository variable `EASE_API_ORIGIN` connects the explorer to an approved HTTPS analysis server. With the variable unset, visitors can explore and download the saved public example. Keep analysis access keys and their hashes on the approved server and keep survey inputs out of Git.

To retry, rerun the latest workflow from the Actions tab. To roll back a release, revert the relevant source commit on `main`. GitHub Actions then tests and publishes the reverted code.

## Optional Bitbucket mirror

The private repository retains its original project history. If you keep it as a separate Git remote named `bitbucket`, you can mirror the clean GitHub history on a separate branch with `git push bitbucket main:github-mirror`. Use GitHub `main` for development and releases.
