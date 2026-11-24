"""Assemble the pinned browser runtime and the allowlisted EASE Python code."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from importlib.metadata import distribution
from pathlib import Path

VERSION = "314.0.8"
CDN = f"https://cdn.jsdelivr.net/pyodide/v{VERSION}/full/"
CORE_ASSETS = {
    "pyodide.mjs": "1bb8cc14f9405aaa7cd4e00c12edd0a8539de9cc026618d6ee5a9663f367dc70",
    "pyodide.asm.mjs": "22514b8be6980e28a02c8b1d6387ce8dfe666fc4edf8d547cff5dce29ff4d972",
    "pyodide.asm.wasm": "e14d49ceca9b4a0e274ea918f3a898de2d3880b6e5573a6cfe1a2267ecc70329",
    "python_stdlib.zip": "2bd3394a145bfbbe5bbc9d9d6ab9136abbb986c6fef6c142b3a2962227aa5c28",
    "pyodide-lock.json": "5dc2fc119108bc148c7457dc86e7675b5c87e1cafd420b9c34c1eaef7b36c010",
}
PACKAGES = ("fastapi", "geopandas", "rasterio", "scipy", "xarray", "fsspec")
TIFFFILE = (
    "https://files.pythonhosted.org/packages/5d/06/bd0a6097da704a7a7c34a94cfd771c3ea3c2f405dd214e790d22c93f6be1/"
    "tifffile-2025.5.10-py3-none-any.whl",
    "e37147123c0542d67bc37ba5cdd67e12ea6fbe6e86c52bee037a9eb6a064e5ad",
)


def verified_asset(url: str, digest: str, cache: Path) -> Path:
    path = cache / url.rsplit("/", 1)[1]
    if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == digest:
        return path
    with urllib.request.urlopen(url, timeout=60) as response:
        content = response.read()
    if hashlib.sha256(content).hexdigest() != digest:
        raise ValueError(f"Checksum mismatch for {path.name}")
    path.write_bytes(content)
    return path


def build_browser_runtime(explorer: Path, root: Path, source: str):
    engine = explorer / "engine"
    runtime = engine / VERSION
    runtime.mkdir(parents=True)
    cache = root / "dist/.browser-runtime-cache" / VERSION
    cache.mkdir(parents=True, exist_ok=True)

    def copy_asset(item):
        name, digest = item
        shutil.copyfile(verified_asset(CDN + name, digest, cache), runtime / name)

    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(copy_asset, CORE_ASSETS.items()))
        packages = json.loads((runtime / "pyodide-lock.json").read_text())["packages"]
        remaining = [*PACKAGES, "fiona"]
        assets = {}
        while remaining:
            package = packages[re.sub(r"[-_.]+", "-", remaining.pop()).lower()]
            name = package["file_name"]
            if name not in assets:
                assets[name] = package["sha256"]
                remaining.extend(package["depends"])
        list(pool.map(copy_asset, assets.items()))

    license_url = f"https://raw.githubusercontent.com/pyodide/pyodide/{VERSION}/LICENSE"
    license_sha256 = "1f256ecad192880510e84ad60474eab7589218784b9a50bc7ceee34c2b91f1d5"
    shutil.copyfile(verified_asset(license_url, license_sha256, cache), runtime / "LICENSE")

    # Code is assembled from the same checkout and pinned dependencies as the
    # native analysis server. Its PyKrige execution mode uses Python and SciPy.
    with zipfile.ZipFile(engine / "source.zip", "w", zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted((root / "ease_volume").glob("*.py")):
            bundle.write(path, path.relative_to(root))
        for name in ("demo_current.csv", "demo_reference.csv", "demo_boundary.geojson", "demo_metadata.json"):
            bundle.write(root / "data" / name, f"data/{name}")
        for name in ("LICENSE", "NOTICE", "static/index.html"):
            bundle.write(root / name, name)
        vendor = root / "vendor/geoutils"
        for path in sorted((vendor / "geoutils").rglob("*")):
            if path.is_file() and path.suffix in {".py", ".ini"}:
                bundle.write(path, path.relative_to(vendor))
        for name in ("LICENSE", "NOTICE"):
            if (vendor / name).is_file():
                bundle.write(vendor / name, f"geoutils/{name}")
        for name in ("pykrige", "rioxarray", "python-multipart"):
            library = distribution(name)
            for path in library.files or ():
                if ".." not in path.parts and (path.suffix == ".py" or path.name in {"LICENSE", "LICENSE.txt", "METADATA"}):
                    bundle.write(library.locate_file(path), path)
        with zipfile.ZipFile(verified_asset(*TIFFFILE, cache)) as wheel:
            for path in wheel.namelist():
                if path.endswith((".py", "/LICENSE", "/LICENSE.txt", "/METADATA")):
                    bundle.writestr(path, wheel.read(path))

    browser_config = {"worker": f"./engine-worker.js?v={source[:12]}"}
    (explorer / "hosting.js").write_text("window.EASE_BROWSER = " + json.dumps(browser_config) + ";\n")
    worker = (root / "static/engine-worker.js").read_text()
    (explorer / "engine-worker.js").write_text(
        worker.replace("__RUNTIME__", VERSION).replace("__PACKAGES__", json.dumps(PACKAGES))
    )
