"""Tests for the create_playlist main function."""

from unittest.mock import MagicMock, patch

import pytest

from create_playlist import main


def _make_sp() -> MagicMock:
    return MagicMock()


class TestMainLanguageValidation:
    @patch("create_playlist.get_spotify_client")
    def test_invalid_language_exits_with_error(self, mock_client):
        mock_client.return_value = _make_sp()
        with patch("builtins.input", return_value="ola"):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 1

    @patch("create_playlist.get_spotify_client")
    def test_empty_language_exits_with_error(self, mock_client):
        mock_client.return_value = _make_sp()
        with patch("builtins.input", return_value=""):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 1

    @patch("create_playlist.get_spotify_client")
    def test_whitespace_only_language_exits_with_error(self, mock_client):
        mock_client.return_value = _make_sp()
        with patch("builtins.input", return_value="   "):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 1

    @patch("create_playlist.get_spotify_client")
    def test_random_word_language_exits_with_error(self, mock_client, capsys):
        mock_client.return_value = _make_sp()
        with patch("builtins.input", return_value="xyz123"):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "not a recognized language" in captured.err


class TestMainValidLanguage:
    @patch("create_playlist.fetch_liked_songs")
    @patch("create_playlist.get_spotify_client")
    def test_valid_language_name_proceeds(self, mock_client, mock_fetch):
        mock_client.return_value = _make_sp()
        mock_fetch.return_value = []
        with patch("builtins.input", return_value="Spanish"):
            main()  # Should not raise
        mock_fetch.assert_called_once()

    @patch("create_playlist.fetch_liked_songs")
    @patch("create_playlist.get_spotify_client")
    def test_valid_iso_code_proceeds(self, mock_client, mock_fetch):
        mock_client.return_value = _make_sp()
        mock_fetch.return_value = []
        with patch("builtins.input", return_value="es"):
            main()  # Should not raise
        mock_fetch.assert_called_once()

    @patch("create_playlist.fetch_liked_songs")
    @patch("create_playlist.get_spotify_client")
    def test_no_liked_songs_returns_early(self, mock_client, mock_fetch, capsys):
        mock_client.return_value = _make_sp()
        mock_fetch.return_value = []
        with patch("builtins.input", return_value="French"):
            main()
        captured = capsys.readouterr()
        assert "No liked songs found" in captured.out

    @patch("create_playlist.filter_tracks_by_language")
    @patch("create_playlist.fetch_liked_songs")
    @patch("create_playlist.get_spotify_client")
    def test_no_matching_songs_returns_early(self, mock_client, mock_fetch, mock_filter, capsys):
        mock_client.return_value = _make_sp()
        mock_fetch.return_value = [{"track": {"name": "Test", "artists": [], "uri": "uri:1"}}]
        mock_filter.return_value = []
        with patch("builtins.input", return_value="German"):
            main()
        captured = capsys.readouterr()
        assert "No liked songs detected" in captured.out
