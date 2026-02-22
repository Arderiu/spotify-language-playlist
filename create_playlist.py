#!/usr/bin/env python3
"""
Create a Spotify playlist from your liked songs filtered by language.

Usage:
    python create_playlist.py

The script will prompt you for a language name (e.g. "Spanish", "French"),
fetch all your Spotify liked songs, detect the language of each track using
the song title and artist names, and create a new playlist containing only
the tracks that match the requested language.

Requirements:
    - A Spotify developer application (https://developer.spotify.com/dashboard)
    - A .env file with SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, and
      SPOTIPY_REDIRECT_URI set (copy .env.example and fill in your values)
"""

import os
import sys

import spotipy
from dotenv import load_dotenv
from langdetect import DetectorFactory, LangDetectException, detect
from spotipy.oauth2 import SpotifyOAuth

# Make language detection deterministic across runs
DetectorFactory.seed = 0

# Scopes required to read liked songs and manage playlists
SPOTIFY_SCOPES = "user-library-read playlist-modify-public playlist-modify-private"

# Map of user-friendly language names to ISO 639-1 codes.
# Covers the most common languages; users can still type an ISO code directly.
LANGUAGE_NAME_TO_CODE = {
    "afrikaans": "af",
    "arabic": "ar",
    "bulgarian": "bg",
    "bengali": "bn",
    "catalan": "ca",
    "czech": "cs",
    "danish": "da",
    "german": "de",
    "greek": "el",
    "english": "en",
    "spanish": "es",
    "estonian": "et",
    "persian": "fa",
    "finnish": "fi",
    "french": "fr",
    "gujarati": "gu",
    "hindi": "hi",
    "croatian": "hr",
    "hungarian": "hu",
    "indonesian": "id",
    "italian": "it",
    "japanese": "ja",
    "kannada": "kn",
    "korean": "ko",
    "lithuanian": "lt",
    "latvian": "lv",
    "macedonian": "mk",
    "malayalam": "ml",
    "marathi": "mr",
    "nepali": "ne",
    "dutch": "nl",
    "norwegian": "no",
    "punjabi": "pa",
    "polish": "pl",
    "portuguese": "pt",
    "romanian": "ro",
    "russian": "ru",
    "slovak": "sk",
    "slovenian": "sl",
    "somali": "so",
    "albanian": "sq",
    "swedish": "sv",
    "swahili": "sw",
    "tamil": "ta",
    "telugu": "te",
    "thai": "th",
    "tagalog": "tl",
    "turkish": "tr",
    "ukrainian": "uk",
    "urdu": "ur",
    "vietnamese": "vi",
    "chinese": "zh-cn",
    "simplified chinese": "zh-cn",
    "traditional chinese": "zh-tw",
}


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


def resolve_language_code(user_input: str) -> str:
    """
    Convert a user-supplied language name or ISO 639-1 code to a code.

    Accepts full names like "Spanish" or codes like "es".  Returns the
    matching ISO 639-1 code in lower-case, or the raw input if it is not
    found in the built-in map (allowing users to pass codes directly).
    """
    normalised = user_input.strip().lower()
    return LANGUAGE_NAME_TO_CODE.get(normalised, normalised)


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


def detect_language(track: dict) -> str | None:
    """
    Detect the language of a track from its name and artist names.

    Returns an ISO 639-1 language code, or None if detection fails.
    """
    track_info = track.get("track", {})
    song_name = track_info.get("name", "")
    artists = " ".join(a.get("name", "") for a in track_info.get("artists", []))
    text = f"{song_name} {artists}".strip()

    if not text:
        return None

    try:
        return detect(text)
    except LangDetectException:
        return None


def filter_tracks_by_language(tracks: list[dict], language_code: str) -> list[str]:
    """
    Return Spotify track URIs whose detected language matches *language_code*.

    Chinese variants (zh-cn / zh-tw) are treated as equivalent when the user
    requests either "zh-cn" or "zh-tw".
    """
    matching_uris = []
    chinese_codes = {"zh-cn", "zh-tw"}

    for track in tracks:
        detected = detect_language(track)
        if detected is None:
            continue

        if language_code in chinese_codes:
            match = detected in chinese_codes
        else:
            match = detected == language_code

        if match:
            uri = track.get("track", {}).get("uri")
            if uri:
                matching_uris.append(uri)

    return matching_uris


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


def main() -> None:
    sp = get_spotify_client()

    language_input = input(
        "Enter the language for your playlist (e.g. Spanish, French): "
    ).strip()
    if not language_input:
        print("No language entered. Exiting.", file=sys.stderr)
        sys.exit(1)

    language_code = resolve_language_code(language_input)
    print(f"Targeting language code: {language_code!r}")

    liked_songs = fetch_liked_songs(sp)
    if not liked_songs:
        print("No liked songs found in your library.")
        return

    print(f"Detecting languages across {len(liked_songs)} songs…")
    matching_uris = filter_tracks_by_language(liked_songs, language_code)

    if not matching_uris:
        print(
            f"No liked songs detected as {language_input!r}. No playlist was created."
        )
        return

    playlist_name = language_input.strip().title()
    print(f"Creating playlist '{playlist_name}' with {len(matching_uris)} songs…")
    playlist_id = create_playlist(sp, playlist_name)
    add_tracks_to_playlist(sp, playlist_id, matching_uris)

    print(f"Done! Playlist '{playlist_name}' created with {len(matching_uris)} tracks.")
    print(f"Open it at: https://open.spotify.com/playlist/{playlist_id}")


if __name__ == "__main__":
    main()
