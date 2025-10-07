"""
Week 6 – Genius API class and helpers (with multiprocessing).
Implements:
  - Genius(access_token)
  - get_artist(search_term)
  - get_artists(search_terms) [serial]
  - get_artists_mp(search_terms) [parallel]
"""

from __future__ import annotations
import os
import requests
import pandas as pd
from typing import List, Dict, Any
import concurrent.futures


class Genius:
    """Wrapper class for Genius.com API."""

    BASE_URL = "https://api.genius.com"

    def __init__(self, access_token: str | None = None):
        """
        Initialize Genius API wrapper.

        Parameters
        ----------
        access_token : str
            Personal Genius API token (get from https://genius.com/api-clients)
        """
        self.access_token = access_token or os.getenv("GENIUS_ACCESS_TOKEN")
        if not self.access_token:
            raise ValueError(
                "No access token provided. Pass one explicitly or set GENIUS_ACCESS_TOKEN in environment."
            )
        self.headers = {"Authorization": f"Bearer {self.access_token}"}

    def _get(self, endpoint: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """Internal helper for GET requests with error handling."""
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        resp = requests.get(url, headers=self.headers, params=params)
        resp.raise_for_status()
        return resp.json()

    def get_artist(self, search_term: str) -> Dict[str, Any]:
        """
        Search for an artist by name and return their artist metadata dict.

        Steps:
        1. Call /search?q=search_term
        2. Extract the artist_id from the first “hit”
        3. Call /artists/{artist_id}
        4. Return the artist JSON dict
        """
        search_data = self._get("search", params={"q": search_term})
        hits = search_data.get("response", {}).get("hits", [])
        if not hits:
            raise ValueError(f"No results found for search term '{search_term}'")
        artist_id = hits[0]["result"]["primary_artist"]["id"]
        artist_data = self._get(f"artists/{artist_id}")
        return artist_data.get("response", {}).get("artist", {})

    def get_artists(self, search_terms: List[str]) -> pd.DataFrame:
        """
        Take a list of artist search terms, and return a DataFrame
        with columns: search_term, artist_name, artist_id, followers_count
        (serial version)
        """
        rows = []
        for term in search_terms:
            try:
                artist_info = self.get_artist(term)
                rows.append(
                    {
                        "search_term": term,
                        "artist_name": artist_info.get("name"),
                        "artist_id": artist_info.get("id"),
                        "followers_count": artist_info.get("followers_count"),
                    }
                )
            except Exception as e:
                rows.append(
                    {
                        "search_term": term,
                        "artist_name": None,
                        "artist_id": None,
                        "followers_count": None,
                        "error": str(e),
                    }
                )
        df = pd.DataFrame(rows)
        return df

    def _get_artist_safe(self, term: str) -> Dict[str, Any]:
        """
        Safe wrapper for get_artist to use in parallel: returns a dict row.
        """
        try:
            artist_info = self.get_artist(term)
            return {
                "search_term": term,
                "artist_name": artist_info.get("name"),
                "artist_id": artist_info.get("id"),
                "followers_count": artist_info.get("followers_count"),
            }
        except Exception as e:
            return {
                "search_term": term,
                "artist_name": None,
                "artist_id": None,
                "followers_count": None,
                "error": str(e),
            }

    def get_artists_mp(self, search_terms: List[str], max_workers: int = 10) -> pd.DataFrame:
        """
        Parallel version using multiprocessing / threads (concurrent.futures).
        Returns same output as get_artists but faster for 100+ items.
        """
        rows = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_term = {
                executor.submit(self._get_artist_safe, term): term for term in search_terms
            }
            for future in concurrent.futures.as_completed(future_to_term):
                res = future.result()
                rows.append(res)
        df = pd.DataFrame(rows)
        return df


# --- If run directly, quick test (requires a valid access token) ---
if __name__ == "__main__":
    # Example usage
    token = os.getenv("GENIUS_ACCESS_TOKEN") or "your_token_here"
    genius = Genius(access_token=token)
    print(genius.get_artist("Radiohead"))
    print(genius.get_artists(["Rihanna", "Tycho", "Seal", "U2"])[["search_term","artist_name"]])
    # Parallel
    print(genius.get_artists_mp(["Rihanna", "Tycho", "Seal", "U2"])[["search_term","artist_name"]])