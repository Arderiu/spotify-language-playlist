"""Language detection utilities for spotify-language-playlist."""

import os

import lyricsgenius
from langdetect import DetectorFactory, LangDetectException, detect

# Make language detection deterministic across runs
DetectorFactory.seed = 0

# Map of user-friendly language names to ISO 639-1 codes.
# Covers the most common languages; users can still type an ISO code directly.
LANGUAGE_NAME_TO_CODE: dict[str, str] = {
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

# All ISO 639-1 codes recognized by this tool
VALID_LANGUAGE_CODES: set[str] = set(LANGUAGE_NAME_TO_CODE.values())


def is_valid_language_input(user_input: str) -> bool:
    """Return True if *user_input* is a recognized language name or ISO 639-1 code."""
    normalised = user_input.strip().lower()
    return normalised in LANGUAGE_NAME_TO_CODE or normalised in VALID_LANGUAGE_CODES


def resolve_language_code(user_input: str) -> str:
    """
    Convert a user-supplied language name or ISO 639-1 code to a code.

    Accepts full names like "Spanish" or codes like "es".  Returns the
    matching ISO 639-1 code in lower-case, or the raw input if it is not
    found in the built-in map (allowing users to pass codes directly).
    """
    normalised = user_input.strip().lower()
    return LANGUAGE_NAME_TO_CODE.get(normalised, normalised)


def get_genius_client() -> lyricsgenius.Genius | None:
    """Return a Genius client if GENIUS_ACCESS_TOKEN is set, otherwise None."""
    token = os.getenv("GENIUS_ACCESS_TOKEN")
    if not token:
        return None
    return lyricsgenius.Genius(token, verbose=False, remove_section_headers=True)


def detect_language(track: dict, genius: lyricsgenius.Genius | None = None) -> str | None:
    """
    Detect the language of a track.

    First tries to fetch lyrics from the Genius API and detect the language
    from those.  If lyrics are unavailable (song not found or no Genius client),
    falls back to detecting from the track name, album name, and artist names.

    Returns an ISO 639-1 language code, or None if detection fails.
    """
    track_info = track.get("track", {})
    song_name = track_info.get("name", "")
    artists = track_info.get("artists", [])
    primary_artist = artists[0].get("name", "") if artists else ""

    if genius is not None and song_name:
        try:
            song = genius.search_song(song_name, primary_artist)
            if song and song.lyrics:
                return detect(song.lyrics)
        except LangDetectException:
            pass
        except Exception:
            pass

    album_name = track_info.get("album", {}).get("name", "")
    all_artists = " ".join(a.get("name", "") for a in artists)
    text = f"{song_name} {album_name} {all_artists}".strip()

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

    total = len(tracks)
    matched_count = 0

    genius = get_genius_client()

    # Always show progress
    print(f"Detecting languages across {total} songs…", end="", flush=True)

    for idx, track in enumerate(tracks):
        detected = detect_language(track, genius)

        if detected is None:
            print(
                f"\rDetecting languages… {idx+1}/{total} checked, {matched_count} matched",
                end="",
                flush=True,
            )
            continue

        if language_code in chinese_codes:
            match = detected in chinese_codes
        else:
            match = detected == language_code

        if match:
            uri = track.get("track", {}).get("uri")
            if uri:
                matching_uris.append(uri)
                matched_count += 1

        print(
            f"\rDetecting languages… {idx+1}/{total} checked, {matched_count} matched",
            end="",
            flush=True,
        )

    print()  # newline after progress indicator

    return matching_uris
