"""spotify_service smoke: fetch() dispatches to the shared spotify_core
helpers per scope, with the core swapped for a fake so there's no OAuth
and no network. A service has no render path, so this exercises fetch()
directly rather than the /_test/render harness the widget smokes use.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest

_MOD_PATH = Path(__file__).resolve().parents[1] / "server.py"
_spec = importlib.util.spec_from_file_location("spotify_service_server", _MOD_PATH)
assert _spec and _spec.loader
server = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(server)


class _FakeCore:
    """Stand-in for spotify_core.server_module."""

    def __init__(self, connected: bool = True) -> None:
        self._connected = connected
        self.calls: list[tuple[str, Any]] = []

    def connected(self) -> bool:
        return self._connected

    def now_playing(self) -> dict[str, Any]:
        return {"connected": True, "ok": True, "track": "Test Track"}

    def queue(self) -> dict[str, Any]:
        return {"connected": True, "ok": True, "items": []}

    def top_items(self, kind: str, time_range: str, limit: int) -> dict[str, Any]:
        self.calls.append((kind, (time_range, limit)))
        return {"connected": True, "ok": True, "kind": kind, "items": []}

    def _valid_access_token(self) -> str:
        return "tok"

    def _api_get(self, url: str, token: str) -> tuple[int, Any]:
        self.calls.append(("raw", url))
        return 200, {"devices": []}

    def _coerce_error(self, err: Exception) -> str:
        return f"{type(err).__name__}: {err}"


@pytest.fixture
def core(monkeypatch: pytest.MonkeyPatch) -> _FakeCore:
    fake = _FakeCore()
    monkeypatch.setattr(server, "_core", lambda: fake)
    return fake


def test_empty_scope_returns_discovery(core: _FakeCore) -> None:
    out = server.fetch({}, {}, ctx={})
    assert out["service"] == "spotify"
    assert set(out["scopes"]) == {"now_playing", "queue", "top", "raw"}


def test_now_playing_and_queue(core: _FakeCore) -> None:
    assert server.fetch({"scope": "now_playing"}, {}, ctx={})["track"] == "Test Track"
    assert server.fetch({"scope": "queue"}, {}, ctx={})["ok"] is True


def test_top_passes_options_through(core: _FakeCore) -> None:
    out = server.fetch(
        {"scope": "top", "kind": "artists", "time_range": "long_term", "limit": 5},
        {},
        ctx={},
    )
    assert out["kind"] == "artists"
    assert core.calls[-1] == ("artists", ("long_term", 5))


def test_raw_requires_v1_path(core: _FakeCore) -> None:
    assert "error" in server.fetch({"scope": "raw", "path": "/oops"}, {}, ctx={})
    out = server.fetch({"scope": "raw", "path": "/v1/me/player/devices"}, {}, ctx={})
    assert out["status"] == 200 and out["data"] == {"devices": []}


def test_raw_not_connected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(server, "_core", lambda: _FakeCore(connected=False))
    out = server.fetch({"scope": "raw", "path": "/v1/me"}, {}, ctx={})
    assert out["connected"] is False


def test_unknown_scope(core: _FakeCore) -> None:
    assert "error" in server.fetch({"scope": "nope"}, {}, ctx={})
