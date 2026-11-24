"""Run the native request handlers inside the browser's Python worker."""
from __future__ import annotations

import json
import re
import shutil
import sys
from contextlib import ExitStack
from pathlib import Path
from types import ModuleType, SimpleNamespace

# GeoUtils imports its vector backend when loading Raster. Browser PointZ
# imports explicitly use Fiona, so the Pyogrio extension is never called.
if sys.platform == "emscripten":
    sys.modules.setdefault("pyogrio", ModuleType("pyogrio"))

from fastapi import UploadFile
from starlette.responses import FileResponse, JSONResponse

from . import server
from .core import AnalysisError

REQUEST = SimpleNamespace(state=SimpleNamespace(result_owner="browser"))
RESULT = re.compile(r"/api/results/([a-f0-9]{32})/([\w.-]+)", re.ASCII)
FILES = ("survey", "reference", "boundary", "sounding")


def dispatch(path: str, fields_json: str, files_json: str) -> str:
    """Route the existing input validation, calculations and export rules."""
    fields = json.loads(fields_json)
    names = json.loads(files_json)
    try:
        with ExitStack() as files:
            uploads = {
                role: UploadFile(files.enter_context((Path("/incoming") / role).open("rb")),
                                 filename=names[role]) if role in names else None
                for role in FILES
            }
            if path == "/api/inspect":
                response = server.inspect_upload(
                    uploads["survey"], fields["crs"], fields["vertical_datum"],
                    fields["z_convention"], uploads["sounding"],
                )
            elif path == "/api/analyze":
                if server.RUNS.exists():
                    shutil.rmtree(server.RUNS)
                response = server.run_analysis(
                    REQUEST, fields.get("config", "{}"), fields.get("demo") == "true",
                    **uploads,
                )
            elif match := RESULT.fullmatch(path):
                response = server.export_result(REQUEST, *match.groups())
            else:
                return json.dumps({"status": 404, "body": {"error": {"code": "not_found"}}})

        if isinstance(response, FileResponse):
            payload = {"status": 200, "file": str(response.path), "type": response.media_type}
        elif isinstance(response, JSONResponse):
            payload = {"status": response.status_code, "body": json.loads(response.body)}
        else:
            payload = {"status": 200, "body": response}
    except AnalysisError as error:
        payload = {"status": 422, "body": {"error": {"code": error.code, "params": error.params}}}
    return json.dumps(payload, allow_nan=False, separators=(",", ":"))
