import pytest
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock
from pathlib import Path

# Make sure to use the anglicized and internationalized CLI app
from cli import app
from i18n import set_lang

runner = CliRunner()

@pytest.fixture(autouse=True)
def set_english_lang():
    """Fixture to ensure all tests run with English messages."""
    set_lang("en")

@pytest.fixture
def mock_youtube_dl():
    """Fixture to mock yt_dlp.YoutubeDL."""
    with patch('adapters.ytdlp_adapter.yt_dlp.YoutubeDL') as mock:
        mock_instance = MagicMock()
        mock.return_value.__enter__.return_value = mock_instance

        def extract_info_side_effect(url, download=True):
            if "playlist" in url:
                return {"title": url.replace("https://", ""), "entries": [{"id": f"v_{url}_1", "title": f"Song 1 from {url}"}, {"id": f"v_{url}_2", "title": f"Song 2 from {url}"}]}
            else:
                return {"id": url.replace("https://", ""), "title": f"Tune from {url}"}
        
        mock_instance.extract_info.side_effect = extract_info_side_effect
        mock_instance.download.return_value = 0
        yield mock_instance

# --- Tests for YAML File Mode ---

def test_import_yaml_playlists_and_tunes(tmp_path, mock_youtube_dl):
    """Checks successful import of a mix of playlists and tracks via YAML."""
    yaml_content = """
artists:
  - name: "Artist With Playlist"
    playlists: ["https://playlist1"]
  - name: "Artist With Tune"
    tunes: ["https://tune1"]
"""
    config_file = tmp_path / "config.yml"
    config_file.write_text(yaml_content)
    result = runner.invoke(app, ["--lang", "en", "import", str(config_file), "--output-dir", str(tmp_path)])
    assert result.exit_code == 0, result.stdout
    assert "Processing artist: Artist With Playlist" in result.stdout
    # 1 call for the playlist, 1 call for the tune
    assert mock_youtube_dl.download.call_count == 2

@patch('pathlib.Path.exists', return_value=True)
def test_import_yaml_skips_existing_with_green_flag(mock_exists, tmp_path, mock_youtube_dl):
    """Checks that existing files are skipped in YAML mode with --green flag."""
    yaml_content = 'artists:\n  - name: "Test Artist"\n    tunes: ["https://tune1"]'
    config_file = tmp_path / "config.yml"
    config_file.write_text(yaml_content)
    
    result = runner.invoke(app, ["--lang", "en", "import", str(config_file), "--output-dir", str(tmp_path), "--green"])
    
    assert result.exit_code == 0, result.stdout
    assert "already exists" in result.stdout
    mock_youtube_dl.download.assert_not_called()

def test_import_yaml_invalid_file(tmp_path):
    """Checks handling of an invalid YAML file."""
    config_file = tmp_path / "invalid.yml"
    config_file.write_text("artists: - name: 'Artist 1'") # Invalid YAML
    result = runner.invoke(app, ["--lang", "en", "import", str(config_file)])
    assert result.exit_code == 1, result.stdout
    


# --- Tests for Direct CLI Mode (No YAML) ---

def test_import_cli_single_tune(tmp_path, mock_youtube_dl):
    """Checks download of a single track via CLI options."""
    result = runner.invoke(app, ["--lang", "en", "import", "--tune", "https://tune1", "--output-dir", str(tmp_path)])
    assert result.exit_code == 0, result.stdout
    assert "tune1" in result.stdout
    mock_youtube_dl.download.assert_called_once()

def test_import_cli_single_playlist(tmp_path, mock_youtube_dl):
    """Checks download of a single playlist via CLI options."""
    result = runner.invoke(app, ["--lang", "en", "import", "--playlist", "https://playlist1", "--output-dir", str(tmp_path)])
    assert result.exit_code == 0, result.stdout
    assert "playlist1" in result.stdout
    mock_youtube_dl.download.assert_called_once()

def test_import_cli_multiple_sources(tmp_path, mock_youtube_dl):
    """Checks download from multiple --tune and --playlist options."""
    result = runner.invoke(app, [
        "--lang", "en",
        "import",
        "--tune", "https://tune1",
        "--playlist", "https://playlist1",
        "--tune", "https://tune2",
        "--output-dir", str(tmp_path)
    ])
    assert result.exit_code == 0, result.stdout
    # 1 call for tune1, 1 for playlist1, 1 for tune2
    assert mock_youtube_dl.download.call_count == 3

@patch('pathlib.Path.exists', return_value=True)
def test_import_cli_skips_existing_with_green_flag(mock_exists, tmp_path, mock_youtube_dl):
    """Checks that existing files are skipped in CLI mode with --green."""
    result = runner.invoke(app, ["--lang", "en", "import", "--tune", "https://tune1", "--output-dir", str(tmp_path), "--green"])
    assert result.exit_code == 0, result.stdout
    assert "already exists" in result.stdout
    mock_youtube_dl.download.assert_not_called()

# --- General Tests ---

def test_import_no_input_fails():
    """Checks that the command fails if no source is provided."""
    result = runner.invoke(app, ["--lang", "en", "import"])
    assert result.exit_code == 1, result.stdout
    assert "You must provide a YAML file or at least one URL" in result.stdout

def test_import_yaml_and_cli_uses_both(tmp_path, mock_youtube_dl):
    """Checks that if a file and CLI options are provided, both are processed."""
    yaml_content = 'artists:\n  - name: "YAML Artist"\n    tunes: ["https://tune_yaml"]'
    config_file = tmp_path / "config.yml"
    config_file.write_text(yaml_content)
    result = runner.invoke(app, [
        "--lang", "en",
        "import", str(config_file),
        "--tune", "https://tune_cli",
        "--output-dir", str(tmp_path)
    ])
    assert result.exit_code == 0, result.stdout
    assert "Processing artist: YAML Artist" in result.stdout
    assert "https://tune_cli" in result.stdout
    # 1 call for yaml tune, 1 for cli tune
    assert mock_youtube_dl.download.call_count == 2