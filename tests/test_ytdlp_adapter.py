import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from pymonad.either import Left, Right

from adapters.ytdlp_adapter import YTDLPAdapter
from domain.models import Playlist
from domain.errors import DownloaderError
from logger_config import setup_logger

# Setup logger for tests
setup_logger()

@pytest.fixture
def ytdlp_adapter():
    """Fixture to provide a YTDLPAdapter instance."""
    return YTDLPAdapter()

# Tests for download_tune
@patch('yt_dlp.YoutubeDL')
def test_download_tune_success(mock_ytdl, ytdlp_adapter, caplog):
    """
    Given a valid tune URL,
    When download_tune is called,
    Then it should successfully download the tune.
    """
    mock_instance = MagicMock()
    mock_ytdl.return_value.__enter__.return_value = mock_instance
    mock_instance.extract_info.return_value = {'title': 'Test Tune', 'id': '123'}
    mock_instance.download.return_value = 0  # Success

    with patch('pathlib.Path.exists', return_value=False):
        result = ytdlp_adapter.download_tune("fake_url", "/fake/path")

    assert result.is_right()
    assert "Test Tune" in result.value
    assert "Téléchargement ignoré" not in caplog.text
    mock_instance.download.assert_called_once()

@patch('yt_dlp.YoutubeDL')
def test_download_tune_green_file_exists(mock_ytdl, ytdlp_adapter, caplog):
    """
    Given a tune URL and green=True,
    When the file already exists,
    Then it should skip the download.
    """
    mock_instance = MagicMock()
    mock_ytdl.return_value.__enter__.return_value = mock_instance
    mock_instance.extract_info.return_value = {'title': 'Existing Tune', 'id': '456'}

    with patch('pathlib.Path.exists', return_value=True):
        result = ytdlp_adapter.download_tune("fake_url", "/fake/path", green=True)

    assert result.is_right()
    assert "déjà présent" in result.value
    assert "Téléchargement ignoré" in caplog.text
    mock_instance.download.assert_not_called()

@patch('yt_dlp.YoutubeDL')
def test_download_tune_green_file_does_not_exist(mock_ytdl, ytdlp_adapter):
    """
    Given a tune URL and green=True,
    When the file does not exist,
    Then it should download the tune.
    """
    mock_instance = MagicMock()
    mock_ytdl.return_value.__enter__.return_value = mock_instance
    mock_instance.extract_info.return_value = {'title': 'New Tune', 'id': '789'}
    mock_instance.download.return_value = 0

    with patch('pathlib.Path.exists', return_value=False):
        result = ytdlp_adapter.download_tune("fake_url", "/fake/path", green=True)

    assert result.is_right()
    mock_instance.download.assert_called_once()

@patch('yt_dlp.YoutubeDL')
def test_download_tune_no_green_file_exists(mock_ytdl, ytdlp_adapter):
    """
    Given a tune URL and green=False,
    When the file exists,
    Then it should still download (overwrite).
    """
    mock_instance = MagicMock()
    mock_ytdl.return_value.__enter__.return_value = mock_instance
    mock_instance.extract_info.return_value = {'title': 'Overwrite Tune', 'id': '101'}
    mock_instance.download.return_value = 0

    # Path.exists should not be called, but we patch it for safety
    with patch('pathlib.Path.exists', return_value=True):
        result = ytdlp_adapter.download_tune("fake_url", "/fake/path", green=False)

    assert result.is_right()
    mock_instance.download.assert_called_once()


# Tests for download_playlist
def test_download_playlist_success(ytdlp_adapter, caplog):
    """
    Given a valid playlist URL and a destination path,
    When the download_playlist method is called,
    Then it should return a Right with a success message
    And log the appropriate info messages.
    """
    playlist_url = "https://www.youtube.com/playlist?list=PL12345"
    destination_path = "/fake/path"
    playlist = Playlist(playlist_id="PL12345", title="Test Playlist", url=playlist_url)

    with patch('yt_dlp.YoutubeDL') as mock_ytdl:
        # Mock the context manager
        mock_instance = MagicMock()
        mock_ytdl.return_value.__enter__.return_value = mock_instance
        mock_instance.download.return_value = 0  # Success code

        # When
        result = ytdlp_adapter.download_playlist(playlist, destination_path)

        # Then
        assert result.is_right()
        assert result.value == f"Playlist '{playlist.title}' téléchargée avec succès dans '{destination_path}'."

        # Check that YoutubeDL was called with the correct options
        expected_ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{destination_path}/%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'ignoreerrors': True,
            'verbose': False,
            'no_overwrites': False,
            'noplaylist': False,
        }
        mock_ytdl.assert_called_once_with(expected_ydl_opts)

        # Check that the download method was called
        mock_instance.download.assert_called_once_with([playlist_url])

        # Check logs
        assert "Début du téléchargement de la playlist 'Test Playlist'..." in caplog.text
        assert f"Playlist '{playlist.title}' téléchargée avec succès." in caplog.text


def test_download_playlist_download_error(ytdlp_adapter, caplog):
    """
    Given a playlist URL,
    When the download process fails (returns a non-zero code),
    Then it should return a Left with an error message
    And log the appropriate error message.
    """
    playlist_url = "https://www.youtube.com/playlist?list=PL12345"
    destination_path = "/fake/path"
    playlist = Playlist(playlist_id="PL12345", title="Test Playlist", url=playlist_url)

    with patch('yt_dlp.YoutubeDL') as mock_ytdl:
        mock_instance = MagicMock()
        mock_ytdl.return_value.__enter__.return_value = mock_instance
        mock_instance.download.return_value = 1  # Error code

        # When
        result = ytdlp_adapter.download_playlist(playlist, destination_path)

        # Then
        assert result.is_left()
        error_value, _ = result.monoid
        assert isinstance(error_value, DownloaderError)
        assert "Erreur lors du téléchargement de la playlist" in error_value.message

        # Check logs
        assert "Début du téléchargement de la playlist 'Test Playlist'..." in caplog.text
        assert "Échec du téléchargement de la playlist 'Test Playlist' avec le code de sortie 1" in caplog.text


def test_download_playlist_with_green_option(ytdlp_adapter):
    """
    Checks that the 'no_overwrites' option is passed correctly to yt-dlp when green=True.
    """
    playlist = Playlist(playlist_id="PL12345", title="Test Playlist", url="http://fake.url")
    destination_path = "/fake/path"

    with patch('yt_dlp.YoutubeDL') as mock_ytdl:
        mock_instance = MagicMock()
        mock_ytdl.return_value.__enter__.return_value = mock_instance
        mock_instance.download.return_value = 0

        ytdlp_adapter.download_playlist(playlist, destination_path, green=True)

        # Check that 'no_overwrites' is True
        args, kwargs = mock_ytdl.call_args
        assert args[0]['no_overwrites'] is True


def test_download_playlist_exception(ytdlp_adapter, caplog):
    """
    Given a playlist URL,
    When the download process raises an exception,
    Then it should return a Left with an error message
    And log the appropriate critical error message.
    """
    playlist_url = "https://www.youtube.com/playlist?list=PL12345"
    destination_path = "/fake/path"
    playlist = Playlist(playlist_id="PL12345", title="Test Playlist", url=playlist_url)
    error_message = "A nasty error occurred"

    with patch('yt_dlp.YoutubeDL') as mock_ytdl:
        mock_instance = MagicMock()
        mock_ytdl.return_value.__enter__.return_value = mock_instance
        mock_instance.download.side_effect = Exception(error_message)

        # When
        result = ytdlp_adapter.download_playlist(playlist, destination_path)

        # Then
        assert result.is_left()
        error_value, _ = result.monoid
        assert isinstance(error_value, DownloaderError)
        assert f"Une erreur inattendue est survenue : {error_message}" in error_value.message

        # Check logs
        assert "Début du téléchargement de la playlist 'Test Playlist'..." in caplog.text
        assert f"Erreur critique lors du téléchargement : {error_message}" in caplog.text
