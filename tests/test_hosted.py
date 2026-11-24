import hashlib
import os
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ease_volume import hosted, server


ORIGIN = "https://manouselis.github.io"
OWNER = {"Authorization": "Bearer pytest-owner"}
OTHER = {"Authorization": "Bearer pytest-other"}


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Use the original routes without attaching hosted middleware to localhost.
    api = FastAPI()
    api.router.routes.extend(server.app.router.routes)
    api.exception_handlers.update(server.app.exception_handlers)
    hashes = ",".join(hashlib.sha256(headers["Authorization"].split()[1].encode()).hexdigest()
                      for headers in (OWNER, OTHER))
    monkeypatch.setattr(server, "RUNS", tmp_path)
    protected = hosted.configure_hosted(api, origin=ORIGIN, key_hashes=hashes, runs=tmp_path)
    with TestClient(protected) as session:
        yield session


def test_hosted_cors_and_size_limit(client):
    headers = {"Origin": ORIGIN, "Access-Control-Request-Method": "POST",
               "Access-Control-Request-Headers": "Authorization"}
    preflight = client.options("/api/analyze", headers=headers)
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == ORIGIN
    assert client.options("/api/analyze", headers={**headers, "Origin": "https://unrelated.example"}).status_code == 400
    assert client.post("/api/analyze", headers=OWNER | {"Content-Length": str(hosted.MAX_BODY + 1)}).status_code == 413
    assert client.post("/api/analyze").status_code == 401
    assert client.get("/api/health").json()["status"] == "ok"
    assert "foundation_source" not in client.get("/api/health").json()


def test_hosted_result_ownership_expiry_and_raw_cleanup(client, tmp_path):
    response = client.post("/api/analyze", headers=OWNER,
                           data={"config": '{"reference_mode":"constant","reference_elevation":-6.5,'
                                           '"reference_note":"Hypothetical reference"}'},
                           files={"survey": ("survey.csv", (server.DATA / "demo_current.csv").read_bytes())})
    assert response.status_code == 200, response.text
    result = response.json()
    link = result["exports"]["bundle"]
    folder = tmp_path / result["id"]
    assert not (folder / "inputs").exists()
    assert client.get(link).status_code == 401
    assert client.get(link, headers=OTHER).status_code == 404
    download = client.get(link, headers=OWNER)
    assert download.status_code == 200
    assert download.headers["Cache-Control"] == "private, no-store"
    assert download.content.startswith(b"PK")
    stamp = time.time() - 7200
    os.utime(folder, (stamp, stamp))
    with (server.DATA / "demo_current.csv").open("rb") as survey:
        assert client.post("/api/inspect", headers=OWNER, files={"survey": ("review.csv", survey)}).status_code == 200
    assert client.get(link, headers=OWNER).status_code == 404
    assert all(not p.is_dir() for p in tmp_path.iterdir())
