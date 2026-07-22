"""Client side of TermQuarium's cloud saves: talks to the Cloud Saves API
(examples/aquarium/website/api/) over plain HTTP via the standard library --
no new dependency, and everything runs off cozy_tui's existing
`app.run_worker()` background-thread mechanism rather than asyncio (see
project memory: async support is deliberately not part of cozy_tui yet).

The Cloud Key is the whole auth model: a locally-generated, high-entropy
string sent as `Authorization: Bearer <key>`. Whoever holds it can read,
write, and list saves under it -- there's no username, password, or
server-side signup step. Losing the key means losing access to those saves,
same as losing a physical door key.
"""

from __future__ import annotations

import json
import secrets
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

CLOUD_API_BASE = "https://termquarium.vercel.app/api"

_KEY_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"  # no 0/O/1/I -- easy to type back in
_KEY_GROUPS = 4
_KEY_GROUP_LENGTH = 4


def generate_cloud_key() -> str:
    """A fresh Cloud Key, e.g. "K3F9-XQ2P-7RTN-JM4W" -- enough entropy
    (32**16, well over 2**76) to be an unforgeable credential, grouped for
    a human to read aloud or type back in on a new PC."""
    groups = [
        "".join(secrets.choice(_KEY_ALPHABET) for _ in range(_KEY_GROUP_LENGTH))
        for _ in range(_KEY_GROUPS)
    ]
    return "-".join(groups)


def _request(
    method: str,
    path: str,
    cloud_key: str,
    base_url: str = CLOUD_API_BASE,
    body: dict | None = None,
    timeout: float = 10.0,
) -> Any:
    """One HTTP round trip to the Cloud Saves API. Raises OSError on a
    connection failure and ValueError on anything else that means the
    request didn't succeed (bad status, unparsable response) -- the same
    two exception types aquarium.py already catches around every
    save/load call, so call sites don't need a third case."""
    url = f"{base_url}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {cloud_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise ValueError(f"Cloud Saves API returned {error.code}: {detail}") from error
    except urllib.error.URLError as error:
        raise OSError(f"Couldn't reach the Cloud Saves API: {error.reason}") from error
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError("Cloud Saves API returned an unreadable response") from error


def _name_path(name: str) -> str:
    # safe="" so even a "/" in a save's display name gets percent-encoded --
    # otherwise it would split across two URL path segments and never match
    # the API's single `/saves/{name}` route server-side.
    encoded = urllib.parse.quote(name, safe="")
    return f"/saves/{encoded}"


def upload_save(
    cloud_key: str, name: str, payload: dict, base_url: str = CLOUD_API_BASE
) -> None:
    """Upload/overwrite one save. `payload` is the exact
    `{version, metadata, aquarium}` dict already written locally."""
    _request("PUT", _name_path(name), cloud_key, base_url, body=payload)


def download_save(cloud_key: str, name: str, base_url: str = CLOUD_API_BASE) -> dict:
    """Return one save's full payload."""
    return _request("GET", _name_path(name), cloud_key, base_url)


def list_cloud_saves(cloud_key: str, base_url: str = CLOUD_API_BASE) -> list[dict]:
    """Return `{"name": ..., "metadata": ...}` for every save under this key."""
    return _request("GET", "/saves", cloud_key, base_url) or []


def delete_cloud_save(
    cloud_key: str, name: str, base_url: str = CLOUD_API_BASE
) -> None:
    """Remove one cloud save. A no-op if it was never there."""
    _request("DELETE", _name_path(name), cloud_key, base_url)
