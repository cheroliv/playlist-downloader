import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from mutagen.id3 import ID3, COMM, ID3NoHeaderError
from adapters.mutagen_adapter import MutagenAdapter
from logger_config import setup_logger

# Setup logger for tests
setup_logger()

@pytest.fixture
def mutagen_adapter():
    """Provides a MutagenAdapter instance."""
    return MutagenAdapter()

def test_get_comment_file_not_found(mutagen_adapter, caplog):
    """
    Given a path to a non-existent file,
    When get_comment is called,
    Then it should return None and not log an error.
    """
    non_existent_file = Path("/non/existent/file.mp3")
    result = mutagen_adapter.get_comment(non_existent_file)
    assert result is None
    assert "Error" not in caplog.text

@patch('pathlib.Path.exists', return_value=True)
@patch('adapters.mutagen_adapter.ID3')
def test_get_comment_success(mock_id3_class, mock_exists, mutagen_adapter):
    """
    Given a valid MP3 file with a comment,
    When get_comment is called,
    Then it should return the comment text.
    """
    # Mock the instance returned by the ID3 constructor
    mock_audio_instance = MagicMock()
    mock_audio_instance.getall.return_value = [MagicMock(text=["Test Comment"])]
    mock_id3_class.return_value = mock_audio_instance
    
    result = mutagen_adapter.get_comment(Path("fake.mp3"))

    assert result == "Test Comment"
    mock_id3_class.assert_called_once_with(Path("fake.mp3"))
    mock_audio_instance.getall.assert_called_once_with('COMM')

@patch('pathlib.Path.exists', return_value=True)
@patch('adapters.mutagen_adapter.ID3')
def test_get_comment_no_comment_frame(mock_id3_class, mock_exists, mutagen_adapter):
    """
    Given an MP3 file without a comment frame,
    When get_comment is called,
    Then it should return None.
    """
    mock_audio_instance = MagicMock()
    mock_audio_instance.getall.return_value = []  # No comment frames
    mock_id3_class.return_value = mock_audio_instance

    result = mutagen_adapter.get_comment(Path("fake.mp3"))

    assert result is None

@patch('pathlib.Path.exists', return_value=True)
@patch('adapters.mutagen_adapter.ID3', side_effect=ID3NoHeaderError("No ID3 header"))
def test_get_comment_no_id3_header(mock_id3_class, mock_exists, mutagen_adapter, caplog):
    """
    Given a file without an ID3 header,
    When get_comment is called,
    Then it should return None and log a warning.
    """
    result = mutagen_adapter.get_comment(Path("fake_no_header.mp3"))

    assert result is None
    assert "does not have an ID3 header" in caplog.text

@patch('pathlib.Path.exists', return_value=True)
@patch('adapters.mutagen_adapter.ID3', side_effect=Exception("Generic Mutagen Error"))
def test_get_comment_generic_exception(mock_id3_class, mock_exists, mutagen_adapter, caplog):
    """
    Given a file that causes a generic exception in Mutagen,
    When get_comment is called,
    Then it should return None and log an error.
    """
    result = mutagen_adapter.get_comment(Path("fake_error.mp3"))

    assert result is None
    assert "Error reading comment" in caplog.text
    assert "Generic Mutagen Error" in caplog.text
