"""Analysis API and localhost static application."""
from __future__ import annotations

import json
import logging
import shutil
import uuid
import zipfile
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .core import MAX_SURVEY_MB, MAX_UPLOAD_MB, MIB, AnalysisConfig, AnalysisError, analyze, inspect_survey

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RUNS = ROOT / "runs"
app = FastAPI(title="EASE bathymetric surface comparison", version="0.2.0")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.exception_handler(AnalysisError)
async def analysis_error_handler(request, exc: AnalysisError):
    return JSONResponse(status_code=422, content={"error": {"code": exc.code, "params": exc.params}})


@app.exception_handler(RequestValidationError)
async def request_error_handler(request, exc):
    return JSONResponse(status_code=422, content={"error": {"code": "invalid_config", "params": {}}})


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/api/health")
def health():
    import geoutils
    return {"status": "ok", "version": "0.2.0", "foundation": "GeoUtils", "foundation_source": str(Path(geoutils.__file__).resolve())}


@app.get("/api/demo")
def demo_info():
    metadata = json.loads((DATA / "demo_metadata.json").read_text())
    metadata["vertical_datum"] = "NAP"
    metadata["defaults"]["filter_k"] = metadata["defaults"].get("filter_k", metadata["defaults"].get("mad_k", 4.5))
    metadata["defaults"]["filter_floor"] = metadata["defaults"].get("filter_floor", metadata["defaults"].get("mad_floor", 0.25))
    metadata["files"] = {"survey": "/api/demo/survey", "reference": "/api/demo/reference", "boundary": "/api/demo/boundary"}
    return metadata


@app.get("/api/demo/{kind}")
def demo_file(kind: str):
    names = {"survey": "demo_current.csv", "reference": "demo_reference.csv", "boundary": "demo_boundary.geojson", "metadata": "demo_metadata.json"}
    if kind not in names:
        return JSONResponse(status_code=404, content={"error": {"code": "not_found", "params": {}}})
    return FileResponse(DATA / names[kind], filename=names[kind])


def save_upload(upload: UploadFile, folder: Path, stem: str, *, limit_mb: int = MAX_UPLOAD_MB) -> Path:
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix not in {".csv", ".txt", ".xyz", ".tif", ".tiff", ".zip", ".json", ".geojson"}:
        raise AnalysisError("unsupported_format")
    upload.file.seek(0, 2)
    if upload.file.tell() > limit_mb * MIB:
        raise AnalysisError("file_too_large", limit_mb=limit_mb)
    upload.file.seek(0)
    path = folder / (stem + suffix)
    with path.open("wb") as stream:
        shutil.copyfileobj(upload.file, stream, length=MIB)
    return path


def save_sounding(upload: UploadFile | None, folder: Path) -> Path | None:
    if upload is None:
        return None
    content = upload.file.read(MAX_UPLOAD_MB * MIB + 1)
    if len(content) > MAX_UPLOAD_MB * MIB:
        raise AnalysisError("file_too_large", limit_mb=MAX_UPLOAD_MB)
    path = folder / "input_sounding"
    path.write_bytes(content)
    return path


@app.post("/api/inspect")
def inspect_upload(survey: UploadFile = File(...), crs: str = Form("EPSG:28992"),
                   vertical_datum: str = Form("NAP"), z_convention: str = Form("elevation"),
                   sounding: UploadFile | None = File(None)):
    RUNS.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="inspect-", dir=RUNS) as folder:
        path = save_upload(survey, Path(folder), "input_survey", limit_mb=MAX_SURVEY_MB)
        return inspect_survey(path, crs, z_convention, vertical_datum, save_sounding(sounding, Path(folder)))


@app.post("/api/analyze")
def run_analysis(request: Request, config: str = Form("{}"), demo: bool = Form(False), survey: UploadFile | None = File(None),
                 reference: UploadFile | None = File(None), boundary: UploadFile | None = File(None),
                 sounding: UploadFile | None = File(None)):
    try:
        config_data = json.loads(config)
        if not isinstance(config_data, dict):
            raise ValueError("config")
    except (json.JSONDecodeError, ValueError) as exc:
        raise AnalysisError("invalid_config") from exc
    metadata = None
    if demo:
        info = demo_info()
        defaults = {key: value for key, value in info["defaults"].items() if key in AnalysisConfig.model_fields}
        defaults.update(crs=info["crs"], vertical_datum="NAP", reference_elevation=info["reference_elevation"],
                        reference_note=info["reference_status"])
        defaults.update(config_data)
        config_data = defaults
        metadata = json.loads((DATA / "demo_metadata.json").read_text())
        metadata["source_kind"] = "raster_cell_centres"
    settings = AnalysisConfig.parse(config_data)
    if settings.reference_mode == "profile" and demo:
        raise AnalysisError("profile_points_required")
    if demo and sounding is not None:
        raise AnalysisError("preprocess_coordinates")
    if demo:
        # Validate types first, then prevent relabelling authoritative metadata.
        from .core import canonical_datum, validate_crs
        if not validate_crs(settings.crs).equals(validate_crs(info["crs"])):
            raise AnalysisError("crs_mismatch")
        if canonical_datum(settings.vertical_datum) != "NAP":
            raise AnalysisError("datum_mismatch")
        if settings.z_convention != "elevation":
            raise AnalysisError("invalid_config", fields=["z_convention"])
    result_id = uuid.uuid4().hex
    folder = RUNS / result_id
    folder.mkdir(parents=True)
    owner = getattr(request.state, "result_owner", None)
    input_dir = folder / "inputs" if owner else folder
    try:
        input_dir.mkdir(exist_ok=True)
        if demo:
            survey_path = DATA / "demo_current.csv"
        elif survey is not None:
            survey_path = save_upload(survey, input_dir, "input_survey", limit_mb=MAX_SURVEY_MB)
        else:
            raise AnalysisError("invalid_csv")
        reference_path = save_upload(reference, input_dir, "input_reference") if reference else None
        if demo and reference_path is None and settings.reference_mode == "file":
            if settings.reference_type != "design":
                raise AnalysisError("invalid_reference")
            reference_path = DATA / "demo_reference.csv"
        boundary_path = save_upload(boundary, input_dir, "input_boundary") if boundary else (DATA / "demo_boundary.geojson" if demo else None)
        sounding_path = save_sounding(sounding, input_dir)
        result = analyze(survey_path, reference_path, boundary_path, settings, folder, metadata, sounding_path)
        exports = {"summary": "summary.json", "bundle": "bundle.zip"}
        names = ["summary.json"]
        if "summary" in result:
            names += ["cells.csv", "points.csv", "bed.tif", "reference.tif", "difference.tif"]
            exports.update(cells="cells.csv", points="points.csv", geotiff="difference.tif")
        if "profile" in result:
            names += ["comparison.csv", "reference_xyz.csv"]
            exports.update(comparison="comparison.csv", design="reference_xyz.csv")
        with zipfile.ZipFile(folder / "bundle.zip", "w", zipfile.ZIP_DEFLATED) as bundle:
            for name in names:
                bundle.write(folder / name, arcname=name)
            for path in sorted(folder.glob("*_kriging_*.tif")):
                bundle.write(path, arcname=path.name)
        result["id"] = result_id
        result["exports"] = {key: f"/api/results/{result_id}/{name}" for key, name in exports.items()}
        if owner:
            (folder / ".owner").write_text(owner)
        return result
    except AnalysisError:
        if owner:
            shutil.rmtree(folder, ignore_errors=True)
        raise
    except Exception:
        if owner:
            shutil.rmtree(folder, ignore_errors=True)
            logging.error("Hosted analysis failed")
        else:
            logging.exception("Analysis failed")
        return JSONResponse(status_code=500, content={"error": {"code": "processing_failed", "params": {}}})
    finally:
        if owner:
            shutil.rmtree(input_dir, ignore_errors=True)



@app.get("/api/results/{result_id}/{filename}")
def export_result(request: Request, result_id: str, filename: str):
    allowed = {"summary.json", "cells.csv", "points.csv", "bed.tif", "reference.tif", "difference.tif",
               "comparison.csv", "reference_xyz.csv", "bundle.zip"}
    allowed.update(f"{role}_kriging_{kind}.tif" for role in ["bed", "reference"] for kind in ["variance", "standard_error"])
    if len(result_id) != 32 or any(c not in "0123456789abcdef" for c in result_id) or filename not in allowed:
        return JSONResponse(status_code=404, content={"error": {"code": "not_found", "params": {}}})
    path = RUNS / result_id / filename
    owner = getattr(request.state, "result_owner", None)
    owned = path.parent / ".owner"
    if not path.is_file() or (owner and (not owned.is_file() or owned.read_text() != owner)):
        return JSONResponse(status_code=404, content={"error": {"code": "not_found", "params": {}}})
    return FileResponse(path, filename=filename)
