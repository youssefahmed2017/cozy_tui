"""Cloud-save storage, backed by Vercel KV (Upstash Redis) over its plain
HTTP REST API -- no special SDK, just a bearer-token POST per command.

Every save lives under a Redis string key `save:<cloud_key>:<name>` holding
the exact same `{version, metadata, aquarium}` JSON already written locally
by `termquarium/save.py`. A Redis hash `meta:<cloud_key>` mirrors just each
save's (small) `metadata` dict, keyed by name -- so listing saves for the
Load-menu-style UI doesn't mean fetching every full aquarium blob just to
read its metadata.

`_redis_command()` is the one function that actually talks to Upstash and is
the seam tests monkeypatch -- everything else here is plain, dependency-free
logic (namespacing, JSON encode/decode) that's cheap to verify without a
real Redis instance.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


class StoreError(Exception):
    """Raised when the underlying KV request fails."""


def _redis_command(*args: str) -> Any:
    """POST one Redis command as a JSON array to Upstash's REST endpoint,
    per https://upstash.com/docs/redis/features/restapi -- returns the
    `result` field of the JSON response."""
    url = os.environ["KV_REST_API_URL"]
    token = os.environ["KV_REST_API_TOKEN"]
    body = json.dumps(list(args)).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as error:
        raise StoreError(f"KV request failed: {error}") from error
    if "error" in payload:
        raise StoreError(payload["error"])
    return payload["result"]


def _save_key(cloud_key: str, name: str) -> str:
    return f"save:{cloud_key}:{name}"


def _meta_key(cloud_key: str) -> str:
    return f"meta:{cloud_key}"


def put_save(cloud_key: str, name: str, payload: dict) -> None:
    """Upload/overwrite one save. `payload` is the same
    `{version, metadata, aquarium}` shape already used locally."""
    _redis_command("SET", _save_key(cloud_key, name), json.dumps(payload))
    _redis_command(
        "HSET", _meta_key(cloud_key), name, json.dumps(payload.get("metadata", {}))
    )


def get_save(cloud_key: str, name: str) -> dict | None:
    """Return one save's full payload, or None if it doesn't exist."""
    raw = _redis_command("GET", _save_key(cloud_key, name))
    return json.loads(raw) if raw is not None else None


def list_saves(cloud_key: str) -> list[dict]:
    """Return every save's `{name, metadata}` stored under this key, without
    fetching each one's full aquarium blob."""
    raw = _redis_command("HGETALL", _meta_key(cloud_key)) or []
    # Upstash returns HGETALL as a flat [field, value, field, value, ...] list.
    pairs = zip(raw[0::2], raw[1::2])
    return [{"name": name, "metadata": json.loads(value)} for name, value in pairs]


def delete_save(cloud_key: str, name: str) -> None:
    """Remove one save. A no-op if it was never there."""
    _redis_command("DEL", _save_key(cloud_key, name))
    _redis_command("HDEL", _meta_key(cloud_key), name)
