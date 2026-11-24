"""Upload and result boundary for the hosted EASE API."""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import os
import re
import shutil
import time
from pathlib import Path
from urllib.parse import urlsplit

from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from . import server

# Four file fields (100 + 25 + 25 + 25 MiB) plus multipart headers.
MAX_BODY = 176 * server.MIB
RUN_ID = re.compile(r"[0-9a-f]{32}")


def configure_hosted(api, *, origin: str, key_hashes: str, runs: Path):
    origin_parts = urlsplit(origin)
    if (origin_parts.scheme not in {"http", "https"} or not origin_parts.netloc
            or origin_parts.username or origin_parts.path or origin_parts.query or origin_parts.fragment):
        raise ValueError("EASE_PAGES_ORIGIN must be a single frontend origin")
    if origin_parts.scheme != "https" and origin_parts.hostname not in {"127.0.0.1", "localhost"}:
        raise ValueError("A hosted frontend must use HTTPS")
    allowed = tuple(value.strip() for value in key_hashes.split(",") if value.strip())
    if not allowed or any(not re.fullmatch(r"[0-9a-f]{64}", value) for value in allowed):
        raise ValueError("EASE_ACCESS_KEY_HASHES must contain SHA-256 hashes of separate random access keys")

    server.RUNS = runs
    ttl = 3600
    max_results = 12
    active = False
    janitor = None

    def prune(reserve=0):
        cutoff = time.time() - ttl
        saved = []
        for item in runs.iterdir():
            if RUN_ID.fullmatch(item.name) and item.is_dir():
                stamp = item.stat().st_mtime
                if stamp <= cutoff:
                    shutil.rmtree(item, ignore_errors=True)
                else:
                    saved.append((stamp, item))
        excess = max(0, len(saved) + reserve - max_results)
        for _, item in sorted(saved)[:excess]:
            shutil.rmtree(item, ignore_errors=True)

    async def cleanup():
        while True:
            if not active:
                prune()
            await asyncio.sleep(60)

    @api.on_event("startup")
    async def start():
        nonlocal janitor
        runs.mkdir(parents=True, exist_ok=True, mode=0o700)
        janitor = asyncio.create_task(cleanup())

    @api.on_event("shutdown")
    async def stop():
        if janitor:
            janitor.cancel()

    def error(status, code):
        return JSONResponse({"error": {"code": code, "params": {}}}, status_code=status,
                            headers={"Cache-Control": "no-store"})

    @api.middleware("http")
    async def hosted_request(request, call_next):
        nonlocal active
        path = request.url.path
        if path == "/api/health":
            return JSONResponse({"status": "ok", "release": os.getenv("EASE_RELEASE") or os.getenv("RENDER_GIT_COMMIT", "dev")},
                                headers={"Cache-Control": "no-store"})
        if path == "/api/demo" or path.startswith("/api/demo/"):
            return await call_next(request)
        if path not in {"/api/access", "/api/analyze", "/api/inspect"} and not path.startswith("/api/results/"):
            return error(404, "not_found")

        scheme, _, key = request.headers.get("Authorization", "").partition(" ")
        digest = hashlib.sha256(key.encode()).hexdigest()
        if scheme.lower() != "bearer" or not any(hmac.compare_digest(digest, value) for value in allowed):
            return error(401, "hosted_access")
        request.state.result_owner = digest
        if path == "/api/access":
            return JSONResponse({"status": "ok"}, headers={"Cache-Control": "no-store"})
        if path.startswith("/api/results/"):
            response = await call_next(request)
            response.headers["Cache-Control"] = "private, no-store"
            return response
        if request.method != "POST":
            return error(405, "invalid_config")
        size = request.headers.get("content-length", "")
        if not size.isdecimal() or len(size) > 12:
            return error(411, "hosted_size")
        if int(size) > MAX_BODY:
            return error(413, "hosted_size")
        if active:
            return error(503, "hosted_busy")
        active = True
        try:
            prune(reserve=int(path == "/api/analyze"))
            response = await call_next(request)
            response.headers["Cache-Control"] = "no-store"
            return response
        finally:
            active = False

    # Run outside the request guard so preflight and structured errors carry CORS headers.
    return CORSMiddleware(api, allow_origins=[origin], allow_methods=["GET", "POST"],
                          allow_headers=["Authorization", "Content-Type"])


def from_environment():
    return configure_hosted(
        server.app, origin=os.environ["EASE_PAGES_ORIGIN"],
        key_hashes=os.environ["EASE_ACCESS_KEY_HASHES"],
        runs=Path(os.environ.get("EASE_RUNS_DIR", "/tmp/ease-results")),
    )


def run_local():
    """Open a temporary, authenticated loopback API for the published explorer."""
    import secrets
    import tempfile

    import uvicorn

    key = secrets.token_urlsafe(32)
    with tempfile.TemporaryDirectory(prefix="ease-pages-local-") as folder:
        app = configure_hosted(server.app, origin="https://manouselis.github.io",
                               key_hashes=hashlib.sha256(key.encode()).hexdigest(),
                               runs=Path(folder))
        print("Open https://manouselis.github.io/ease-sediment-volume-explorer/explore/?analysis=1", flush=True)
        print("Analysis access key:", key, flush=True)
        uvicorn.run(app, host="127.0.0.1", port=8767, workers=1, limit_concurrency=16, access_log=False)


if __name__ == "__main__":
    run_local()
