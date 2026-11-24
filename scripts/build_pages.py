"""Build only the public Pages assets from the canonical application checkout."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

from fastapi.testclient import TestClient

from ease_volume import server

ROOT = server.ROOT


def write_json(path: Path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n")


def build(destination: Path, api_origin: str, source: str):
    if api_origin:
        parts = urlsplit(api_origin)
        if (parts.scheme not in {"https", "http"} or not parts.hostname or parts.username
                or parts.path or parts.query or parts.fragment
                or (parts.scheme == "http" and parts.hostname not in {"localhost", "127.0.0.1"})):
            raise ValueError("Expected an HTTPS API origin, with HTTP allowed only for loopback tests")
    if not re.fullmatch(r"[a-f0-9]{40}", source):
        raise ValueError("Expected a full source commit SHA")
    destination.mkdir(parents=True)
    for name in ("index.html", "site.css"):
        shutil.copyfile(ROOT / "deploy" / "pages" / name, destination / name)
    for name in ("LICENSE", "NOTICE"):
        shutil.copyfile(ROOT / name, destination / name)
    (destination / ".nojekyll").touch()
    (destination / "images").mkdir()
    shutil.copyfile(ROOT / "deploy/pages/canal-bed.webp", destination / "images/canal-bed.webp")

    explorer = destination / "explore"
    static = explorer / "static"
    static.mkdir(parents=True)
    for name in ("app.js", "styles.css", "i18n.js", "plotly.min.js", "plotly-LICENSE.txt"):
        shutil.copyfile(ROOT / "static" / name, static / name)
    (explorer / "hosting.js").write_text("window.EASE_HOSTING = " + json.dumps({"apiOrigin": api_origin}) + ";\n")
    app_html = (ROOT / "static" / "index.html").read_text()
    app_html = app_html.replace('"/static/', '"./static/').replace('href="/" class="brand"', 'href="../" class="brand"')
    app_html = app_html.replace('  <script defer src="./static/app.js', '  <script defer src="./hosting.js"></script>\n  <script defer src="./static/app.js')
    app_html = app_html.replace('?v=survey-preprocess-1', f'?v={source[:12]}')
    app_html = app_html.replace('./hosting.js"', f'./hosting.js?v={source[:12]}"')
    (explorer / "index.html").write_text(app_html)

    original_runs = server.RUNS
    try:
        with tempfile.TemporaryDirectory(prefix="ease-pages-") as folder, TestClient(server.app) as client:
            server.RUNS = Path(folder)
            metadata = client.get("/api/demo").json()
            public_inputs = {"survey": "survey.csv", "reference": "reference.csv", "boundary": "boundary.geojson"}
            (explorer / "demo").mkdir()
            for key, name in public_inputs.items():
                response = client.get(metadata["files"][key])
                response.raise_for_status()
                (explorer / "demo" / name).write_bytes(response.content)
            metadata["files"] = {key: f"demo/{name}" for key, name in public_inputs.items()}
            for method in ("tin", "kriging"):
                result = client.post("/api/analyze", data={
                    "demo": "true", "config": json.dumps({"surface_method": method})
                })
                result.raise_for_status()
                payload = result.json()
                target = explorer / "demo" / method
                target.mkdir()
                for key, url in payload["exports"].items():
                    name = url.rsplit("/", 1)[-1]
                    response = client.get(url)
                    response.raise_for_status()
                    (target / name).write_bytes(response.content)
                    payload["exports"][key] = f"demo/{method}/{name}"
                payload.pop("id", None)
                write_json(target / "view.json", {"result": payload, "metadata": metadata})
                if method == "tin":
                    summary = payload["summary"]
    finally:
        server.RUNS = original_runs
    stats = {
        "above": [summary["positive_volume_m3"], "m³", 1],
        "below": [abs(summary["negative_volume_m3"]), "m³", 1],
        "area": [summary["valid_area_m2"], "m²", 0],
        "coverage": [summary["coverage_percent"], "%", 1],
    }
    (destination / "site-info.js").write_text(f"""const stats = {json.dumps(stats, ensure_ascii=False)};
for (const [key, [value, unit, digits]] of Object.entries(stats)) {{
  const formatted = new Intl.NumberFormat('en-GB', {{maximumFractionDigits:digits}}).format(value);
  document.querySelector('[data-stat="' + key + '"]').textContent = formatted + (unit === '%' ? unit : ' ' + unit);
}}
""" + ("document.querySelector('#analysis-availability').textContent = 'Project users can connect to the analysis server from the explorer.';\n" if api_origin else ""))
    write_json(destination / "release.json", {"source_commit": source, "hosted_analysis_configured": bool(api_origin)})
    build_page = (ROOT / "deploy/pages/build.html").read_text()
    analysis_status = ("Project access key required to analyse surveys online." if api_origin
                       else "Use the local application to analyse new surveys. The public demo is available here.")
    (destination / "build.html").write_text(
        build_page.replace("{{SOURCE_COMMIT}}", source).replace("{{ANALYSIS_STATUS}}", analysis_status)
    )
    (destination / "README.md").write_text(
        "# EASE Sediment Volume Explorer\n\n"
        "Generated GitHub Pages assets and public Rijkswaterstaat demo results. "
        "Releases are built from the canonical GitHub application.\n\n"
        f"Source commit: `{source}`.\n"
    )


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("destination", type=Path, help="Path that does not already exist")
    cli.add_argument("--api-origin", default="")
    cli.add_argument("--source", default=subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip())
    args = cli.parse_args()
    build(args.destination, args.api_origin, args.source)
