"""Spotify service (kind: service).

A non-placeable data source that exposes the Spotify Web API to a code element.
It reuses the account connected in Plugins → Spotify (via the spotify_core
plugin) through the plugin registry, so it shares one OAuth token with the
spotify_* widget family and never stores its own.

The agent lists it via list_services(), probes it with an empty scope to learn
the scopes, then requests one: ``now_playing`` / ``queue`` (the shared widget
helpers), ``top`` (top tracks / artists / albums for a time window), or ``raw``
(an authenticated GET of any Spotify Web API path it names, e.g.
``/v1/me/player/devices``). fetch() returns the parsed Spotify JSON so the code
element reads whatever fields it needs off ctx.data.<name>.

There is no render side (kind "service"); ``fetch`` is the whole plugin.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

from flask import current_app

_API_BASE = "https://api.spotify.com"


def _core() -> Any:
    plugin = current_app.config["PLUGIN_REGISTRY"].get("spotify_core")
    return plugin.server_module if plugin is not None else None


def _discovery() -> dict[str, Any]:
    """Self-describing map returned when no scope is set, so the agent can
    explore the API before choosing what to fetch."""
    return {
        "service": "spotify",
        "auth": "shared (Plugins → Spotify: connect your account; needs Spotify Core 0.2.0+)",
        "scopes": {
            "now_playing": "Currently playing track (shared now_playing helper).",
            "queue": "Playback queue (shared queue helper).",
            "top": "Top items. Set options.kind (tracks/artists/albums), "
            "options.time_range (short_term/medium_term/long_term), options.limit.",
            "raw": "Authenticated GET of any Spotify Web API path you name in "
            "options.path (must start with /v1). Returns {status, data, path}.",
        },
        "usage": "Set options.scope to one of the scopes above.",
    }


def fetch(
    options: dict[str, Any], settings: dict[str, Any], *, ctx: dict[str, Any]
) -> dict[str, Any]:
    del settings, ctx
    scope = str(options.get("scope") or "").strip()
    if not scope:
        return _discovery()

    core = _core()
    if core is None:
        return {"error": "spotify_core plugin not available"}

    if scope == "now_playing":
        return dict(core.now_playing())

    if scope == "queue":
        return dict(core.queue())

    if scope == "top":
        kind = str(options.get("kind") or "tracks").strip()
        time_range = str(options.get("time_range") or "short_term").strip()
        try:
            limit = max(1, min(50, int(options.get("limit") or 10)))
        except (TypeError, ValueError):
            limit = 10
        return dict(core.top_items(kind, time_range, limit))

    if scope == "raw":
        path = str(options.get("path") or "").strip()
        if not path.startswith("/v1"):
            return {"error": "raw scope needs options.path starting with /v1"}
        if not core.connected():
            return {
                "connected": False,
                "error": "Spotify not connected (Plugins → Spotify)",
            }
        try:
            token = core._valid_access_token()
            status, data = core._api_get(urljoin(_API_BASE, path), token)
        except Exception as err:
            return {"error": core._coerce_error(err), "path": path}
        return {"status": status, "data": data, "path": path}

    return {"error": f"unknown scope {scope!r}"}
