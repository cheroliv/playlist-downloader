from unittest.mock import MagicMock
from youtube_api import create_playlist, delete_playlist, get_playlist_url
from domain.errors import YouTubeApiError
from googleapiclient.errors import HttpError


# Scenario 1: Successful playlist creation
def test_create_playlist_success(mocker, caplog):
    """
    Checks that playlist creation calls the API with the correct parameters
    and returns a Right(playlist_id) on success.
    LDD: Verifies info logs.
    """
    mock_credentials = MagicMock()
    mock_credentials.universe_domain = "googleapis.com"

    # Simulate the API call chain
    mock_insert = MagicMock()
    api_response = {"id": "PL123456789", "snippet": {"title": "My Test Playlist"}}
    mock_insert.execute.return_value = api_response

    mock_playlists = MagicMock()
    mock_playlists.insert.return_value = mock_insert

    mock_youtube_service = MagicMock()
    mock_youtube_service.playlists.return_value = mock_playlists

    mocker.patch("youtube_api.build", return_value=mock_youtube_service)

    result = create_playlist(
        mock_credentials, "Test Title", "Test Description", private=True
    )

    assert result.is_right()
    assert result.value == "PL123456789"

    # Check that the API was called correctly
    mock_playlists.insert.assert_called_once_with(
        part="snippet,status",
        body={
            "snippet": {"title": "Test Title", "description": "Test Description"},
            "status": {"privacyStatus": "private"},
        },
    )
    assert "Playlist 'PL123456789' created successfully." in caplog.text


# Scenario 2: Playlist creation failure (API error)
def test_create_playlist_api_error(mocker, caplog):
    """
    Checks that the function returns a Left on API error.
    LDD: Verifies error logs.
    """
    mock_credentials = MagicMock()
    mock_credentials.universe_domain = "googleapis.com"

    # Simulate a realistic HTTP error response
    mock_http_resp = MagicMock()
    mock_http_resp.status = 403
    mock_http_resp.reason = "Forbidden"

    http_error = HttpError(resp=mock_http_resp, content=b"Permission denied")

    mock_youtube_service = MagicMock()
    mock_youtube_service.playlists().insert().execute.side_effect = http_error

    mocker.patch("youtube_api.build", return_value=mock_youtube_service)

    result = create_playlist(mock_credentials, "Title", "Description", private=False)

    assert result.is_left()
    error_value, _ = result.monoid
    assert isinstance(error_value, YouTubeApiError)
    assert "Permission denied" in error_value.message
    assert "Failed to create playlist" in caplog.text
    assert "Permission denied" in caplog.text


# Scenario 3: Successful playlist deletion
def test_delete_playlist_success(mocker, caplog):
    """
    Checks that playlist deletion calls the API with the correct ID
    and returns a Right with a success message.
    LDD: Verifies info logs.
    """
    mock_credentials = MagicMock()
    mock_credentials.universe_domain = "googleapis.com"
    playlist_id = "PL123456789"

    mock_delete_execute = MagicMock(return_value=None)  # Deletion returns nothing
    mock_delete = MagicMock()
    mock_delete.execute = mock_delete_execute

    mock_playlists = MagicMock()
    mock_playlists.delete.return_value = mock_delete

    mock_youtube_service = MagicMock()
    mock_youtube_service.playlists.return_value = mock_playlists

    mocker.patch("youtube_api.build", return_value=mock_youtube_service)

    result = delete_playlist(mock_credentials, playlist_id)

    assert result.is_right()
    assert result.value == f"Playlist '{playlist_id}' deleted successfully."
    mock_playlists.delete.assert_called_once_with(id=playlist_id)
    assert f"Playlist '{playlist_id}' deleted successfully." in caplog.text


# Scenario 4: Deletion failure (playlist not found)
def test_delete_playlist_not_found_error(mocker, caplog):
    """
    Checks that the function returns a Left(YouTubeApiError) if the playlist does not exist.
    LDD: Verifies error logs.
    """
    mock_credentials = MagicMock()
    mock_credentials.universe_domain = "googleapis.com"
    playlist_id = "PL_NON_EXISTENT"

    mock_http_resp = MagicMock()
    mock_http_resp.status = 404
    mock_http_resp.reason = "Not Found"

    http_error = HttpError(resp=mock_http_resp, content=b"Playlist not found.")

    mock_youtube_service = MagicMock()
    mock_youtube_service.playlists().delete().execute.side_effect = http_error

    mocker.patch("youtube_api.build", return_value=mock_youtube_service)

    result = delete_playlist(mock_credentials, playlist_id)

    assert result.is_left()
    error_value, _ = result.monoid
    assert isinstance(error_value, YouTubeApiError)
    assert "Playlist not found" in error_value.message
    assert f"Failed to delete playlist '{playlist_id}'" in caplog.text


# Scenario 6: Get share URL successfully
def test_get_playlist_url_success(mocker, caplog):
    """
    Checks that the function returns a Right with the playlist URL.
    LDD: Verifies info logs.
    """
    mock_credentials = MagicMock()
    mock_credentials.universe_domain = "googleapis.com"
    playlist_id = "PL123456789"
    expected_url = f"https://www.youtube.com/playlist?list={playlist_id}"

    # Simulate the API response (even though we don't use it directly)
    mock_list_execute = MagicMock(return_value={"items": [{"id": playlist_id}]})
    mock_list = MagicMock()
    mock_list.execute = mock_list_execute

    mock_playlists = MagicMock()
    mock_playlists.list.return_value = mock_list

    mock_youtube_service = MagicMock()
    mock_youtube_service.playlists.return_value = mock_playlists

    mocker.patch("youtube_api.build", return_value=mock_youtube_service)

    result = get_playlist_url(mock_credentials, playlist_id)

    assert result.is_right()
    assert result.value == expected_url
    assert f"URL for playlist '{playlist_id}' retrieved successfully." in caplog.text
