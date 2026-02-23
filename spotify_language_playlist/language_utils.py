"""Language detection utilities for spotify-language-playlist."""

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

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


def detect_language(track: dict, lyrics: str | None = None) -> str | None:
    """
    Detect the language of a track.

    If *lyrics* is provided, detect from those first. Otherwise fall back to
    detecting from the track name, album name, and artist names.

    Returns an ISO 639-1 language code, or None if detection fails.
    """
    if lyrics:
        try:
            return detect(lyrics)
        except LangDetectException:
            # fall through to metadata-based detection
            pass

    track_info = track.get("track", {})
    song_name = track_info.get("name", "")
    album_name = track_info.get("album", {}).get("name", "")
    artists = " ".join(a.get("name", "") for a in track_info.get("artists", []))
    text = f"{song_name} {album_name} {artists}".strip()

    if not text:
        return None

    try:
        return detect(text)
    except LangDetectException:
        return None


def filter_tracks_by_language(tracks: list[dict], language_code: str) -> list[str]:
    """
    Return Spotify track URIs whose detected language matches *language_code*.

    This implementation will perform a small number of concurrent Genius
    lookups (if a GENIUS_ACCESS_TOKEN is configured) to speed up detection for
    tracks where lyrics are available. There is no persistent caching.
    """
    matching_uris = []
    chinese_codes = {"zh-cn", "zh-tw"}

    total = len(tracks)
    matched_count = 0

    genius = get_genius_client()

    # If we have a Genius client, fetch lyrics concurrently for tracks that
    # have a title and artist. We keep a simple aligned list of lyrics per track
    # index; missing entries remain None and detection falls back to metadata.
    lyrics_list: list[str | None] = [None] * total
    if genius is not None and total:
        max_workers = 5

        def _safe_search(title: str, artist: str) -> str | None:
            try:
                song = genius.search_song(title, artist)
                return getattr(song, "lyrics", None) if song else None
            except Exception:
                return None

        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {}
            for idx, track in enumerate(tracks):
                ti = track.get("track", {})
                title = ti.get("name", "")
                artists = ti.get("artists", [])
                primary = artists[0].get("name", "") if artists else ""
                if title and primary:
                    futures[ex.submit(_safe_search, title, primary)] = idx

            # Show progress while fetching lyrics concurrently
            total_fetch = len(futures)
            completed = 0
            start = time.perf_counter()
            for fut in as_completed(futures):
                idx = futures[fut]
                try:
                    lyrics_list[idx] = fut.result()
                except Exception:
                    lyrics_list[idx] = None
                completed += 1
                elapsed = time.perf_counter() - start
                print(
                    f"\rFetching lyrics from Genius: {completed}/{total_fetch} completed (elapsed {elapsed:.1f}s)",
                    end="",
                    flush=True,
                )
            print()  # newline after fetch progress

    # Progress header
    print(f"Detecting languages across {total} songs…", end="", flush=True)

    for idx, track in enumerate(tracks):
        lyrics = lyrics_list[idx] if idx < len(lyrics_list) else None
        detected = detect_language(track, lyrics)

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
