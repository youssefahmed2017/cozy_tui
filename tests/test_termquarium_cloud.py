"""Client-side cloud saves contract tests (termquarium/cloud.py) -- all
network calls are mocked; nothing here touches a real socket."""

import io
import json
import urllib.error

from examples.aquarium.termquarium import cloud


class _FakeResponse:
    def __init__(self, data: bytes):
        self._data = data

    def read(self):
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


def test_generate_cloud_key_has_the_expected_shape():
    key = cloud.generate_cloud_key()
    groups = key.split("-")
    assert len(groups) == cloud._KEY_GROUPS
    assert all(len(g) == cloud._KEY_GROUP_LENGTH for g in groups)
    assert all(ch in cloud._KEY_ALPHABET for g in groups for ch in g)


def test_generate_cloud_key_is_effectively_unique():
    keys = {cloud.generate_cloud_key() for _ in range(200)}
    assert len(keys) == 200


def test_upload_save_sends_a_put_with_bearer_auth_and_json_body(monkeypatch):
    captured = []

    def fake_urlopen(request, timeout=10):
        captured.append(request)
        return _FakeResponse(b'{"ok": true}')

    monkeypatch.setattr(cloud.urllib.request, "urlopen", fake_urlopen)

    payload = {"version": 1, "metadata": {"name": "Steve's Kingdom"}, "aquarium": {}}
    cloud.upload_save(
        "MY-KEY", "Steve's Kingdom", payload, base_url="https://x.test/api"
    )

    request = captured[0]
    assert request.get_method() == "PUT"
    assert request.full_url == "https://x.test/api/saves/Steve%27s%20Kingdom"
    assert request.get_header("Authorization") == "Bearer MY-KEY"
    assert json.loads(request.data) == payload


def test_a_slash_in_the_save_name_stays_within_one_url_path_segment(monkeypatch):
    # A raw "/" would otherwise split across two path segments and never
    # match the API's single `/saves/{name}` route.
    captured = []

    def fake_urlopen(request, timeout=10):
        captured.append(request)
        return _FakeResponse(b"null")

    monkeypatch.setattr(cloud.urllib.request, "urlopen", fake_urlopen)

    cloud.download_save("MY-KEY", "Reef/Castle", base_url="https://x.test/api")

    assert captured[0].full_url == "https://x.test/api/saves/Reef%2FCastle"


def test_download_save_returns_the_parsed_payload(monkeypatch):
    payload = {"version": 1, "metadata": {}, "aquarium": {"state": {"money": 5}}}
    monkeypatch.setattr(
        cloud.urllib.request,
        "urlopen",
        lambda request, timeout=10: _FakeResponse(json.dumps(payload).encode("utf-8")),
    )

    result = cloud.download_save(
        "MY-KEY", "Steve's Kingdom", base_url="https://x.test/api"
    )

    assert result == payload


def test_list_cloud_saves_returns_entries(monkeypatch):
    entries = [{"name": "A", "metadata": {}}, {"name": "B", "metadata": {}}]
    monkeypatch.setattr(
        cloud.urllib.request,
        "urlopen",
        lambda request, timeout=10: _FakeResponse(json.dumps(entries).encode("utf-8")),
    )

    assert cloud.list_cloud_saves("MY-KEY", base_url="https://x.test/api") == entries


def test_delete_cloud_save_sends_delete(monkeypatch):
    captured = []

    def fake_urlopen(request, timeout=10):
        captured.append(request)
        return _FakeResponse(b"")

    monkeypatch.setattr(cloud.urllib.request, "urlopen", fake_urlopen)

    cloud.delete_cloud_save("MY-KEY", "Old Save", base_url="https://x.test/api")

    assert captured[0].get_method() == "DELETE"


def test_a_404_response_raises_value_error(monkeypatch):
    def fake_urlopen(request, timeout=10):
        raise urllib.error.HTTPError(
            request.full_url, 404, "Not Found", None, io.BytesIO(b"no such save")
        )

    monkeypatch.setattr(cloud.urllib.request, "urlopen", fake_urlopen)

    try:
        cloud.download_save("MY-KEY", "Missing", base_url="https://x.test/api")
        assert False, "expected ValueError"
    except ValueError as error:
        assert "404" in str(error)


def test_a_connection_failure_raises_os_error(monkeypatch):
    def fake_urlopen(request, timeout=10):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(cloud.urllib.request, "urlopen", fake_urlopen)

    try:
        cloud.list_cloud_saves("MY-KEY", base_url="https://x.test/api")
        assert False, "expected OSError"
    except OSError:
        pass
