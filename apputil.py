"""
Week 6 utilities: Genius API class + helpers.

Public API:
- class Genius:
    Genius(access_token: str | None = None,
           cache_json: str | None = "data/genius_search_sample.json",
           timeout: float = 10.0)
    .get_artist(search_term: str) -> dict
    .get_artists(search_terms: list[str]) -> "pd.DataFrame"

Notes
-----
- If no `access_token` is passed, the class looks in the environment variable
  GENIUS_ACCESS_TOKEN.
- If the live API call fails, we optionally fall back to a cached JSON search
  response (same structure as Genius search endpoint) to keep exercises runnable.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd
import requests


GENIUS_BASE = "https://api.genius.com"
SEARCH_ENDPOINT = f"{GENIUS_BASE}/search"
ARTIST_ENDPOINT = f"{GENIUS_BASE}/artists/{{artist_id}}"  # format with id


@dataclass
class _HTTPResult:
    ok: bool
    data: Optional[dict]
    status: Optional[int]
    error: Optional[str]


class Genius:
    """
    Minimal Genius API client for this week’s exercise.

    Parameters
    ----------
    access_token : str | None
        Genius Client Access Token. If None, reads os.environ['GENIUS_ACCESS_TOKEN'].
    cache_json : str | None
        Optional path to a local JSON file with a cached Genius *search* response
        (containing `response.hits[...]`). Used as a fallback for demos/offline.
    timeout : float
        Per-request timeout (seconds).
    """

    def __init__(
        self,
        access_token: Optional[str] = None,
        cache_json: Optional[str] = "data/genius_search_sample.json",
        timeout: float = 10.0,
    ) -> None:
        tok = access_token or os.getenv("GENIUS_ACCESS_TOKEN")
        if not tok:
            # keep going without raising: we can still use offline JSON fallback
            tok = ""
        self.access_token = tok
        self.cache_json = cache_json
        self.timeout = float(timeout)

        self._session = requests.Session()
        if self.access_token:
            self._session.headers.update({"Authorization": f"Bearer {self.access_token}"})

    # -------------------------
    # Low-level HTTP helper
    # -------------------------
    def _get(self, url: str, params: Optional[dict] = None) -> _HTTPResult:
        """GET wrapper with small, readable result object."""
        try:
            resp = self._session.get(url, params=params, timeout=self.timeout)
            status = resp.status_code
            if 200 <= status < 300:
                return _HTTPResult(True, resp.json(), status, None)
            return _HTTPResult(False, None, status, f"HTTP {status}")
        except Exception as e:  # network/JSON errors
            return _HTTPResult(False, None, None, str(e))

    # -------------------------
    # JSON fallback utilities
    # -------------------------
    def _load_cached_search(self) -> Optional[dict]:
        """Load a cached Genius search response if available."""
        if not self.cache_json:
            return None
        try:
            with open(self.cache_json, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    @staticmethod
    def _first_hit_artist_id(search_json: dict) -> Optional[int]:
        """Extract the most-likely artist id from the first hit in a Genius search JSON."""
        try:
            hits = search_json["response"]["hits"]
            if not hits:
                return None
            # First hit
            hit = hits[0]
            # Prefer the primary artist on the hit result
            primary = hit["result"]["primary_artist"]
            return int(primary["id"])
        except Exception:
            return None

    @staticmethod
    def _first_hit_artist_name(search_json: dict) -> Optional[str]:
        """Extract the artist name parallel to `_first_hit_artist_id`."""
        try:
            hits = search_json["response"]["hits"]
            if not hits:
                return None
            return str(hits[0]["result"]["primary_artist"]["name"])
        except Exception:
            return None

    # -------------------------
    # Public methods
    # -------------------------
    def get_artist(self, search_term: str) -> dict:
        """
        Search for `search_term`, resolve the first hit's primary artist ID,
        fetch that artist JSON, and return it as a dict.

        Returns
        -------
        dict
            The Genius Artist JSON object (e.g., keys: 'id', 'name', 'followers_count'...).
            If the API is unavailable and a cached JSON file is configured, returns
            a minimal dict with 'id' and 'name' inferred from the cached search JSON.
            If nothing can be resolved, returns {}.
        """
        # 1) Attempt live search
        search_json: Optional[dict] = None
        if self.access_token:
            r = self._get(SEARCH_ENDPOINT, params={"q": search_term})
            if r.ok and isinstance(r.data, dict):
                search_json = r.data

        # 2) Fallback: cached search JSON (for offline/rate-limited scenarios)
        if search_json is None:
            cached = self._load_cached_search()
            if isinstance(cached, dict):
                search_json = cached

        if not isinstance(search_json, dict):
            return {}

        artist_id = self._first_hit_artist_id(search_json)
        artist_name = self._first_hit_artist_name(search_json)

        # If we have an id and a live token, fetch artist details
        if artist_id is not None and self.access_token:
            r_artist = self._get(ARTIST_ENDPOINT.format(artist_id=artist_id))
            if r_artist.ok and isinstance(r_artist.data, dict):
                try:
                    return r_artist.data["response"]["artist"]
                except Exception:
                    pass  # fall through to minimal dict

        # Minimal dict if we can’t fetch the full artist payload
        if artist_id is not None or artist_name is not None:
            out = {}
            if artist_id is not None:
                out["id"] = artist_id
            if artist_name is not None:
                out["name"] = artist_name
            return out

        return {}

    def get_artists(self, search_terms: Iterable[str]) -> pd.DataFrame:
        """
        For each search term, resolve the (most likely) artist and return a table.

        Columns
        -------
        search_term : str
        artist_name : str | None
        artist_id : int | None
        followers_count : int | None   (present only when full artist JSON was retrieved)
        """
        rows: List[Dict[str, Any]] = []
        for term in search_terms:
            artist = self.get_artist(term)

            if not artist:  # could not resolve
                rows.append(
                    {
                        "search_term": term,
                        "artist_name": None,
                        "artist_id": None,
                        "followers_count": None,
                    }
                )
                continue

            rows.append(
                {
                    "search_term": term,
                    "artist_name": artist.get("name"),
                    "artist_id": artist.get("id"),
                    "followers_count": artist.get("followers_count"),
                }
            )

        return pd.DataFrame(rows)