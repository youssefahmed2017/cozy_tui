"""TermQuarium Cloud Saves API -- a thin FastAPI app deployed as a single
Vercel Python serverless function (any file under website/api/ is picked up
automatically). All real logic lives in store.py; this module only handles
HTTP routing, auth-header extraction, and status codes.

Auth model: the Cloud Key a player generates locally (see
termquarium/cloud.py) is sent as `Authorization: Bearer <key>` and used
directly as the storage namespace -- there is no account database and no
login step. Knowing the key is the credential, the same trust model as a
shareable secret link.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Vercel's Python runtime doesn't guarantee this file's own directory is on
# sys.path when it imports index.py -- a plain `import store` was failing
# there ("could not import api/index.py") even though the exact same layout
# works fine locally. Adding it explicitly makes the sibling import robust
# regardless of whatever working directory Vercel actually invokes this
# from.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI, Header, HTTPException  # noqa: E402
from pydantic import BaseModel  # noqa: E402

import store  # noqa: E402

app = FastAPI(title="TermQuarium Cloud Saves")

_SAFE_NAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _safe_name(name: str) -> str:
    """Mirrors termquarium/save.py's safe_filename() -- the backend can't
    import that module directly (separate deployment, separate repo), so
    the same small sanitization rule is duplicated here deliberately."""
    cleaned = _SAFE_NAME.sub("_", name).strip().rstrip(".")
    return cleaned or "Untitled Aquarium"


def _cloud_key(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or malformed Authorization header")
    key = authorization.removeprefix("Bearer ").strip()
    if not key:
        raise HTTPException(401, "Empty Cloud Key")
    return key


class SavePayload(BaseModel):
    version: int
    metadata: dict
    aquarium: dict


@app.get("/api/saves")
def list_saves(authorization: str | None = Header(default=None)):
    key = _cloud_key(authorization)
    return store.list_saves(key)


@app.put("/api/saves/{name}")
def upload_save(
    name: str, payload: SavePayload, authorization: str | None = Header(default=None)
):
    key = _cloud_key(authorization)
    store.put_save(key, _safe_name(name), payload.model_dump())
    return {"ok": True}


@app.get("/api/saves/{name}")
def download_save(name: str, authorization: str | None = Header(default=None)):
    key = _cloud_key(authorization)
    saved = store.get_save(key, _safe_name(name))
    if saved is None:
        raise HTTPException(404, f"No cloud save named {name!r}")
    return saved


@app.delete("/api/saves/{name}")
def remove_save(name: str, authorization: str | None = Header(default=None)):
    key = _cloud_key(authorization)
    store.delete_save(key, _safe_name(name))
    return {"ok": True}
