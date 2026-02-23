"""Tests for language_utils module."""

import pytest
from unittest.mock import MagicMock, patch

from spotify_language_playlist.language_utils import (
    LANGUAGE_NAME_TO_CODE,
    VALID_LANGUAGE_CODES,
    detect_language,
    filter_tracks_by_language,
    get_genius_client,
    is_valid_language_input,
    resolve_language_code,
)


class TestResolveLanguageCode:
    def test_known_language_name(self):
        assert resolve_language_code("Spanish") == "es"

    def test_case_insensitive(self):
        assert resolve_language_code("FRENCH") == "fr"

    def test_iso_code_passthrough(self):
        assert resolve_language_code("es") == "es"

    def test_unknown_input_passthrough(self):
        assert resolve_language_code("ola") == "ola"

    def test_strips_whitespace(self):
        assert resolve_language_code("  english  ") == "en"


class TestIsValidLanguageInput:
    def test_valid_language_name(self):
        assert is_valid_language_input("Spanish") is True

    def test_valid_language_name_lowercase(self):
        assert is_valid_language_input("spanish") is True

    def test_valid_language_name_uppercase(self):
        assert is_valid_language_input("ENGLISH") is True

    def test_valid_iso_code(self):
        assert is_valid_language_input("es") is True

    def test_invalid_language(self):
        assert is_valid_language_input("ola") is False

    def test_empty_string(self):
        assert is_valid_language_input("") is False

    def test_whitespace_only(self):
        assert is_valid_language_input("   ") is False

    def test_all_known_names(self):
        for name in LANGUAGE_NAME_TO_CODE:
            assert is_valid_language_input(name) is True

    def test_all_known_codes(self):
        for code in VALID_LANGUAGE_CODES:
            assert is_valid_language_input(code) is True

    def test_random_word_rejected(self):
        for word in ("hello", "xyz", "123", "notlanguage"):
            assert is_valid_language_input(word) is False


class TestDetectLanguage:
    def test_english_song(self):
        track = {"track": {"name": "Hello world beautiful day", "artists": [{"name": "English Artist"}]}}
        assert detect_language(track) == "en"

    def test_missing_track_key(self):
        assert detect_language({}) is None

    def test_empty_text(self):
        track = {"track": {"name": "", "artists": []}}
        assert detect_language(track) is None

    def test_multiple_artists(self):
        track = {
            "track": {
                "name": "Song",
                "artists": [{"name": "Artist One"}, {"name": "Artist Two"}],
            }
        }
        result = detect_language(track)
        assert result is None or isinstance(result, str)

    def test_uses_genius_lyrics_when_available(self):
        mock_genius = MagicMock()
        mock_song = MagicMock()
        mock_song.lyrics = "Hello world this is an English song with many words"
        mock_genius.search_song.return_value = mock_song

        track = {"track": {"name": "Hello", "artists": [{"name": "Artist"}]}}
        result = detect_language(track, genius=mock_genius)

        mock_genius.search_song.assert_called_once_with("Hello", "Artist")
        assert result == "en"

    def test_falls_back_when_genius_song_not_found(self):
        mock_genius = MagicMock()
        mock_genius.search_song.return_value = None

        track = {"track": {"name": "Hello beautiful world today", "artists": [{"name": "English Artist"}]}}
        result = detect_language(track, genius=mock_genius)
        assert result == "en"

    def test_falls_back_when_genius_lyrics_empty(self):
        mock_genius = MagicMock()
        mock_song = MagicMock()
        mock_song.lyrics = ""
        mock_genius.search_song.return_value = mock_song

        track = {"track": {"name": "Hello beautiful world today", "artists": [{"name": "English Artist"}]}}
        result = detect_language(track, genius=mock_genius)
        assert result == "en"

    def test_falls_back_when_genius_raises_exception(self):
        mock_genius = MagicMock()
        mock_genius.search_song.side_effect = Exception("Network error")

        track = {"track": {"name": "Hello beautiful world today", "artists": [{"name": "English Artist"}]}}
        result = detect_language(track, genius=mock_genius)
        assert result == "en"

    def test_no_genius_client_uses_fallback(self):
        track = {"track": {"name": "Hello world beautiful day", "artists": [{"name": "English Artist"}]}}
        assert detect_language(track, genius=None) == "en"


class TestGetGeniusClient:
    def test_returns_none_when_token_not_set(self):
        with patch.dict("os.environ", {}, clear=True):
            assert get_genius_client() is None

    def test_returns_client_when_token_set(self):
        with patch.dict("os.environ", {"GENIUS_ACCESS_TOKEN": "fake_token"}):
            with patch("spotify_language_playlist.language_utils.lyricsgenius.Genius") as mock_genius_cls:
                mock_genius_cls.return_value = MagicMock()
                client = get_genius_client()
                mock_genius_cls.assert_called_once_with("fake_token", verbose=False, remove_section_headers=True)
                assert client is not None


class TestFilterTracksByLanguage:
    def _make_track(self, name: str, artist: str, uri: str) -> dict:
        return {"track": {"name": name, "artists": [{"name": artist}], "uri": uri}}

    def test_filters_matching_language(self):
        tracks = [
            self._make_track("Hello beautiful world today", "English Artist", "uri:en"),
            self._make_track("Hola mundo maravilloso hoy", "Artista Español", "uri:es"),
        ]
        result = filter_tracks_by_language(tracks, "es")
        assert "uri:es" in result
        assert "uri:en" not in result

    def test_empty_tracks_returns_empty(self):
        assert filter_tracks_by_language([], "en") == []

    def test_no_matching_language_returns_empty(self):
        tracks = [self._make_track("Hello world", "English Artist", "uri:en")]
        result = filter_tracks_by_language(tracks, "fr")
        assert result == []

    def test_track_without_uri_skipped(self):
        track = {"track": {"name": "Hello world beautiful", "artists": [{"name": "Artist"}]}}
        result = filter_tracks_by_language([track], "en")
        assert result == []

    def test_chinese_variants_treated_as_equivalent(self):
        track_cn = {"track": {"name": "你好世界美丽", "artists": [{"name": "艺术家"}], "uri": "uri:cn"}}
        result_cn = filter_tracks_by_language([track_cn], "zh-cn")
        result_tw = filter_tracks_by_language([track_cn], "zh-tw")
        assert result_cn == result_tw
