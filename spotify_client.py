"""Spotify authentication and API helper functions."""

import os
import sys

import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

# Scopes required to read liked songs and manage playlists
SPOTIFY_SCOPES = "user-library-read playlist-modify-public playlist-modify-private"


def get_spotify_client() -> spotipy.Spotify:
    """Authenticate with Spotify and return an authorised client."""
    load_dotenv()

    required_vars = (
        "SPOTIPY_CLIENT_ID",
        "SPOTIPY_CLIENT_SECRET",
        "SPOTIPY_REDIRECT_URI",
    )
    missing = [v for v in required_vars if not os.getenv(v)]
    if missing:
        print(
            "Error: the following environment variables are not set:\n  "
            + "\n  ".join(missing)
            + "\nCopy .env.example to .env and fill in your Spotify credentials.",
            file=sys.stderr,
        )
        sys.exit(1)

    auth_manager = SpotifyOAuth(
        client_id=os.getenv("SPOTIPY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
        scope=SPOTIFY_SCOPES,
    )
    return spotipy.Spotify(auth_manager=auth_manager)


def fetch_liked_songs(sp: spotipy.Spotify) -> list[dict]:
    """Fetch all liked (saved) tracks from the current user's library."""
    tracks = []
    limit = 50
    offset = 0

    print("Fetching your liked songs…", end="", flush=True)
    while True:
        response = sp.current_user_saved_tracks(limit=limit, offset=offset)
        items = response.get("items", [])
        if not items:
            break
        tracks.extend(items)
        print(f"\rFetching your liked songs… {len(tracks)} fetched", end="", flush=True)
        if response.get("next") is None:
            break
        offset += limit

    print()  # newline after progress indicator
    return tracks


def find_playlist_by_name(sp: spotipy.Spotify, name: str) -> str | None:
    """Return the ID of the first user playlist whose name matches *name*, or None."""
    limit = 50
    offset = 0
    user_id = sp.me()["id"]
    while True:
        response = sp.current_user_playlists(limit=limit, offset=offset)
        items = response.get("items", [])
        if not items:
            break
        for playlist in items:
            if playlist.get("owner", {}).get("id") == user_id and playlist.get("name") == name:
                return playlist["id"]
        if response.get("next") is None:
            break
        offset += limit
    return None


def fetch_playlist_track_uris(sp: spotipy.Spotify, playlist_id: str) -> set[str]:
    """Return the set of track URIs already present in *playlist_id*."""
    uris: set[str] = set()
    limit = 100
    offset = 0
    while True:
        response = sp.playlist_items(
            playlist_id, fields="items(track(uri)),next", limit=limit, offset=offset
        )
        items = response.get("items", [])
        if not items:
            break
        for item in items:
            uri = (item.get("track") or {}).get("uri")
            if uri:
                uris.add(uri)
        if response.get("next") is None:
            break
        offset += limit
    return uris


def create_playlist(sp: spotipy.Spotify, name: str) -> str:
    """Create a new private playlist for the current user and return its ID."""
    payload = {
        "name": name,
        "public": False,
        "description": f"Songs in {name} – created by spotify-language-playlist",
    }
    playlist = sp._post("me/playlists", payload=payload)
    return playlist["id"]


def add_tracks_to_playlist(
    sp: spotipy.Spotify, playlist_id: str, track_uris: list[str]
) -> None:
    """Add tracks to a playlist in batches of 100 (Spotify API limit)."""
    batch_size = 100
    for i in range(0, len(track_uris), batch_size):
        batch = track_uris[i : i + batch_size]
        sp._post(f"playlists/{playlist_id}/items", payload={"uris": batch})
