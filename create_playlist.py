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

import sys

from language_utils import (filter_tracks_by_language, is_valid_language_input,
                            resolve_language_code)
from spotify_client import (add_tracks_to_playlist, create_playlist,
                            fetch_liked_songs, fetch_playlist_track_uris,
                            find_playlist_by_name, get_spotify_client)


def main() -> None:
    sp = get_spotify_client()

    language_input = input(
        "Enter the language for your playlist (e.g. Spanish, French): "
    ).strip()
    if not language_input:
        print("No language entered. Exiting.", file=sys.stderr)
        sys.exit(1)

    language_code = resolve_language_code(language_input)
    if not is_valid_language_input(language_input):
        print(
            f"Error: {language_input!r} is not a recognized language name or ISO 639-1 code. "
            "Please enter a language name (e.g. Spanish, French) or an ISO 639-1 code (e.g. es, fr).",
            file=sys.stderr,
        )
        sys.exit(1)
    print(f"Targeting language code: {language_code!r}")

    liked_songs = fetch_liked_songs(sp)
    if not liked_songs:
        print("No liked songs found in your library.")
        return

    matching_uris = filter_tracks_by_language(liked_songs, language_code)

    if not matching_uris:
        print(
            f"No liked songs detected as {language_input!r}. No playlist was created."
        )
        return

    playlist_name = language_input.strip().title()
    playlist_id = find_playlist_by_name(sp, playlist_name)
    if playlist_id:
        print(
            f"Playlist '{playlist_name}' already exists. Checking for new songs to add…"
        )
        existing_uris = fetch_playlist_track_uris(sp, playlist_id)
        new_uris = [uri for uri in matching_uris if uri not in existing_uris]
        if not new_uris:
            print(
                f"All {len(matching_uris)} detected song(s) are already in the playlist. Nothing to add."
            )
            print(f"Open it at: https://open.spotify.com/playlist/{playlist_id}")
            return
        print(f"Adding {len(new_uris)} new song(s) to '{playlist_name}'…")
        add_tracks_to_playlist(sp, playlist_id, new_uris)
        print(f"Done! Added {len(new_uris)} new track(s) to '{playlist_name}'.")
    else:
        print(f"Creating playlist '{playlist_name}' with {len(matching_uris)} songs…")
        playlist_id = create_playlist(sp, playlist_name)
        add_tracks_to_playlist(sp, playlist_id, matching_uris)
        print(
            f"Done! Playlist '{playlist_name}' created with {len(matching_uris)} tracks."
        )
    print(f"Open it at: https://open.spotify.com/playlist/{playlist_id}")


if __name__ == "__main__":
    main()
