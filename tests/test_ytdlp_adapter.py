# tests/test_ytdlp_adapter.py
import pytest
from unittest.mock import patch, MagicMock
from pymonad.either import Left, Right

from playlist_downloader.adapters.ytdlp_adapter import YTDLPAdapter
from playlist_downloader.domain.models import Playlist
from playlist_downloader.domain.errors import DownloaderError
from playlist_downloader.logger_config import setup_logger

# Setup logger for tests
setup_logger()

@pytest.fixture
def ytdlp_adapter():
    """Fixture to provide a YTDLPAdapter instance."""
    return YTDLPAdapter()


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


def test_download_playlist_with_best_quality(ytdlp_adapter):
    """
    Vérifie que la qualité 'best' est correctement passée aux options de yt-dlp.
    """
    playlist = Playlist(playlist_id="PL12345", title="Test Playlist", url="http://fake.url")
    destination_path = "/fake/path"

    with patch('yt_dlp.YoutubeDL') as mock_ytdl:
        mock_instance = MagicMock()
        mock_ytdl.return_value.__enter__.return_value = mock_instance
        mock_instance.download.return_value = 0

        ytdlp_adapter.download_playlist(playlist, destination_path, quality="best")

        # Vérifier que 'preferredquality' est mis à '0' pour la meilleure qualité
        expected_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{destination_path}/%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '0',  # '0' est la meilleure qualité pour yt-dlp
            }],
            'ignoreerrors': True,
            'verbose': False,
        }
        mock_ytdl.assert_called_once_with(expected_opts)


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
