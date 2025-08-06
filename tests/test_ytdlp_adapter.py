import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

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


@patch(
    "adapters.ytdlp_adapter.YTDLPAdapter._is_tune_already_present", return_value=False
)
@patch("yt_dlp.YoutubeDL")
def test_download_tune_success(mock_ytdl, mock_is_present, ytdlp_adapter, caplog):
    """
    Given a valid tune URL,
    When download_tune is called,
    Then it should successfully download the tune.
    """
    mock_instance = MagicMock()
    mock_ytdl.return_value.__enter__.return_value = mock_instance
    mock_instance.extract_info.return_value = {"title": "Test Tune", "id": "123"}
    mock_instance.download.return_value = 0  # Success

    result = ytdlp_adapter.download_tune("fake_url", "/fake/path")

    assert result.is_right()
    assert "Test Tune" in result.value
    assert "Skipping download" not in caplog.text
    mock_is_present.assert_not_called()  # Should not be called if green=False
    mock_instance.download.assert_called_once()


@patch(
    "adapters.ytdlp_adapter.YTDLPAdapter._is_tune_already_present", return_value=True
)
@patch("yt_dlp.YoutubeDL")
def test_download_tune_green_tune_exists(
    mock_ytdl, mock_is_present, ytdlp_adapter, caplog
):
    """
    Given a tune URL and green=True,
    When the tune's URL is already present in the destination,
    Then it should skip the download.
    """
    mock_instance = MagicMock()
    mock_ytdl.return_value.__enter__.return_value = mock_instance

    result = ytdlp_adapter.download_tune(
        "http://matching.url", "/fake/path", green=True
    )

    assert result.is_right()
    assert "already exists" in result.value
    assert "Skipping download" in caplog.text
    mock_is_present.assert_called_once_with("http://matching.url", "/fake/path")
    mock_instance.download.assert_not_called()


@patch(
    "adapters.ytdlp_adapter.YTDLPAdapter._is_tune_already_present", return_value=False
)
@patch("yt_dlp.YoutubeDL")
def test_download_tune_green_tune_does_not_exist(
    mock_ytdl, mock_is_present, ytdlp_adapter
):
    """
    Given a tune URL and green=True,
    When the tune's URL is not present,
    Then it should download the tune.
    """
    mock_instance = MagicMock()
    mock_ytdl.return_value.__enter__.return_value = mock_instance
    mock_instance.extract_info.return_value = {"title": "New Tune", "id": "789"}
    mock_instance.download.return_value = 0

    result = ytdlp_adapter.download_tune("http://new.url", "/fake/path", green=True)

    assert result.is_right()
    mock_is_present.assert_called_once_with("http://new.url", "/fake/path")
    mock_instance.download.assert_called_once()


@patch(
    "adapters.ytdlp_adapter.YTDLPAdapter._is_tune_already_present", return_value=True
)
@patch("yt_dlp.YoutubeDL")
def test_download_tune_no_green_tune_exists(mock_ytdl, mock_is_present, ytdlp_adapter):
    """
    Given a tune URL and green=False,
    When the tune already exists,
    Then it should still download (overwrite).
    """
    mock_instance = MagicMock()
    mock_ytdl.return_value.__enter__.return_value = mock_instance
    mock_instance.extract_info.return_value = {"title": "Overwrite Tune", "id": "101"}
    mock_instance.download.return_value = 0

    result = ytdlp_adapter.download_tune(
        "http://existing.url", "/fake/path", green=False
    )

    assert result.is_right()
    mock_is_present.assert_not_called()  # Green check is skipped
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

    with patch("yt_dlp.YoutubeDL") as mock_ytdl:
        # Mock the context manager
        mock_instance = MagicMock()
        mock_ytdl.return_value.__enter__.return_value = mock_instance
        mock_instance.download.return_value = 0  # Success code

        # When
        result = ytdlp_adapter.download_playlist(playlist, destination_path)

        # Then
        assert result.is_right()
        assert (
            result.value
            == f"Playlist '{playlist.title}' downloaded successfully to '{destination_path}'."
        )

        # Check that YoutubeDL was called with the correct options
        called_opts = mock_ytdl.call_args[0][0]
        assert called_opts["format"] == "bestaudio/best"
        assert called_opts["noplaylist"] is False

        # Check postprocessors
        pp_keys = [p["key"] for p in called_opts["postprocessors"]]
        assert "FFmpegExtractAudio" in pp_keys
        assert "EmbedThumbnail" in pp_keys
        assert "FFmpegMetadata" in pp_keys
        assert "ModifyTags" in pp_keys

        # Check that the download method was called
        mock_instance.download.assert_called_once_with([playlist_url])

        # Check logs
        assert "Starting download of playlist 'Test Playlist'..." in caplog.text
        assert f"Playlist '{playlist.title}' downloaded successfully." in caplog.text


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

    with patch("yt_dlp.YoutubeDL") as mock_ytdl:
        mock_instance = MagicMock()
        mock_ytdl.return_value.__enter__.return_value = mock_instance
        mock_instance.download.return_value = 1  # Error code

        # When
        result = ytdlp_adapter.download_playlist(playlist, destination_path)

        # Then
        assert result.is_left()
        error_value, _ = result.monoid
        assert isinstance(error_value, DownloaderError)
        assert "Error downloading playlist" in error_value.message

        # Check logs
        assert "Starting download of playlist 'Test Playlist'..." in caplog.text
        assert (
            "Failed to download playlist 'Test Playlist' with exit code 1"
            in caplog.text
        )


def test_download_playlist_with_green_option(ytdlp_adapter):
    """
    Checks that the 'no_overwrites' option is passed correctly to yt-dlp when green=True.
    """
    playlist = Playlist(
        playlist_id="PL12345", title="Test Playlist", url="http://fake.url"
    )
    destination_path = "/fake/path"

    with patch("yt_dlp.YoutubeDL") as mock_ytdl:
        mock_instance = MagicMock()
        mock_ytdl.return_value.__enter__.return_value = mock_instance
        mock_instance.download.return_value = 0

        ytdlp_adapter.download_playlist(playlist, destination_path, green=True)

        # Check that 'no_overwrites' is True
        args, kwargs = mock_ytdl.call_args
        assert args[0]["no_overwrites"] is True


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

    with patch("yt_dlp.YoutubeDL") as mock_ytdl:
        mock_instance = MagicMock()
        mock_ytdl.return_value.__enter__.return_value = mock_instance
        mock_instance.download.side_effect = Exception(error_message)

        # When
        result = ytdlp_adapter.download_playlist(playlist, destination_path)

        # Then
        assert result.is_left()
        error_value, _ = result.monoid
        assert isinstance(error_value, DownloaderError)
        assert f"An unexpected error occurred: {error_message}" in error_value.message

        # Check logs
        assert "Starting download of playlist 'Test Playlist'..." in caplog.text
        assert f"Critical error during download: {error_message}" in caplog.text


# --- Tests for _is_tune_already_present ---


@patch("pathlib.Path.is_dir", return_value=True)
@patch("pathlib.Path.glob")
def test_is_tune_present_found(mock_glob, mock_is_dir, ytdlp_adapter):
    """
    Given a directory containing an MP3 with a matching URL,
    When _is_tune_already_present is called,
    Then it should return True.
    """
    mock_glob.return_value = [Path("/fake/path/song.mp3")]
    ytdlp_adapter._mutagen_adapter.get_comment = MagicMock(
        return_value="http://matching.url"
    )

    result = ytdlp_adapter._is_tune_already_present("http://matching.url", "/fake/path")

    assert result is True
    ytdlp_adapter._mutagen_adapter.get_comment.assert_called_once_with(
        Path("/fake/path/song.mp3")
    )


@patch("pathlib.Path.is_dir", return_value=True)
@patch("pathlib.Path.glob")
def test_is_tune_present_not_found(mock_glob, mock_is_dir, ytdlp_adapter):
    """
    Given a directory with MP3s but none with a matching URL,
    When _is_tune_already_present is called,
    Then it should return False.
    """
    mock_glob.return_value = [
        Path("/fake/path/song1.mp3"),
        Path("/fake/path/song2.mp3"),
    ]
    ytdlp_adapter._mutagen_adapter.get_comment = MagicMock(
        return_value="http://different.url"
    )

    result = ytdlp_adapter._is_tune_already_present("http://matching.url", "/fake/path")

    assert result is False
    assert ytdlp_adapter._mutagen_adapter.get_comment.call_count == 2


@patch("pathlib.Path.is_dir", return_value=False)
def test_is_tune_present_dir_not_exists(mock_is_dir, ytdlp_adapter):
    """
    Given a destination that is not a directory,
    When _is_tune_already_present is called,
    Then it should return False.
    """
    result = ytdlp_adapter._is_tune_already_present("http://any.url", "/not/a/dir")
    assert result is False


@patch("pathlib.Path.is_dir", return_value=True)
@patch("pathlib.Path.glob", return_value=[])
def test_is_tune_present_empty_dir(mock_glob, mock_is_dir, ytdlp_adapter):
    """
    Given an empty directory,
    When _is_tune_already_present is called,
    Then it should return False.
    """
    ytdlp_adapter._mutagen_adapter.get_comment = MagicMock()

    result = ytdlp_adapter._is_tune_already_present("http://any.url", "/empty/dir")

    assert result is False
    ytdlp_adapter._mutagen_adapter.get_comment.assert_not_called()
