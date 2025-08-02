import pytest
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock
from pathlib import Path

from cli import app

runner = CliRunner()

@pytest.fixture
def mock_youtube_dl():
    """Fixture pour mocker yt_dlp.YoutubeDL."""
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

# --- Tests pour le mode Fichier YAML ---

def test_import_yaml_playlists_and_tunes(tmp_path, mock_youtube_dl):
    """Vérifie l'importation réussie d'un mix de playlists et de morceaux via YAML."""
    yaml_content = """
artistes:
  - name: "Artist With Playlist"
    playlists: ["https://playlist1"]
  - name: "Artist With Tune"
    tunes: ["https://tune1"]
"""
    config_file = tmp_path / "config.yml"
    config_file.write_text(yaml_content)
    result = runner.invoke(app, ["importer", str(config_file), "-o", str(tmp_path)])
    assert result.exit_code == 0, result.stdout
    assert "Traitement de l'artiste : Artist With Playlist" in result.stdout
    # 1 call for the playlist, 1 call for the tune
    assert mock_youtube_dl.download.call_count == 2

@patch('pathlib.Path.exists', return_value=True)
def test_import_yaml_skips_existing_with_green_flag(mock_exists, tmp_path, mock_youtube_dl):
    """Vérifie que les fichiers existants sont ignorés en mode YAML avec --green."""
    yaml_content = 'artistes:\n  - name: "Test Artist"\n    tunes: ["https://tune1"]'
    config_file = tmp_path / "config.yml"
    config_file.write_text(yaml_content)
    
    # Run with --green flag
    result = runner.invoke(app, ["importer", str(config_file), "-o", str(tmp_path), "--green"])
    
    assert result.exit_code == 0, result.stdout
    assert "déjà présent" in result.stdout
    mock_youtube_dl.download.assert_not_called()

def test_import_yaml_invalid_file(tmp_path):
    """Vérifie la gestion d'un fichier YAML invalide."""
    config_file = tmp_path / "invalid.yml"
    config_file.write_text("artistes: - name: 'Artiste 1'")
    result = runner.invoke(app, ["importer", str(config_file)])
    assert result.exit_code == 1
    assert "Impossible de lire ou d'analyser le fichier YAML" in result.stdout

# --- Tests pour le mode CLI direct (sans YAML) ---

def test_import_cli_single_tune(tmp_path, mock_youtube_dl):
    """Vérifie le téléchargement d'un seul morceau via les options CLI."""
    result = runner.invoke(app, ["importer", "--tune", "https://tune1", "-o", str(tmp_path)])
    assert result.exit_code == 0, result.stdout
    assert "Traitement du morceau : https://tune1" in result.stdout
    mock_youtube_dl.download.assert_called_once()

def test_import_cli_single_playlist(tmp_path, mock_youtube_dl):
    """Vérifie le téléchargement d'une seule playlist via les options CLI."""
    result = runner.invoke(app, ["importer", "--playlist", "https://playlist1", "-o", str(tmp_path)])
    assert result.exit_code == 0, result.stdout
    assert "Traitement de la playlist : https://playlist1" in result.stdout
    mock_youtube_dl.download.assert_called_once()

def test_import_cli_multiple_sources(tmp_path, mock_youtube_dl):
    """Vérifie le téléchargement depuis plusieurs options --tune and --playlist."""
    result = runner.invoke(app, [
        "importer",
        "--tune", "https://tune1",
        "--playlist", "https://playlist1",
        "--tune", "https://tune2",
        "-o", str(tmp_path)
    ])
    assert result.exit_code == 0, result.stdout
    # 1 call for tune1, 1 for playlist1, 1 for tune2
    assert mock_youtube_dl.download.call_count == 3

@patch('pathlib.Path.exists', return_value=True)
def test_import_cli_skips_existing_with_green_flag(mock_exists, tmp_path, mock_youtube_dl):
    """Vérifie que les fichiers existants sont ignorés en mode CLI avec --green."""
    result = runner.invoke(app, ["importer", "--tune", "https://tune1", "-o", str(tmp_path), "--green"])
    assert result.exit_code == 0, result.stdout
    assert "déjà présent" in result.stdout
    mock_youtube_dl.download.assert_not_called()


# --- Tests Généraux ---

def test_import_no_input_fails():
    """Vérifie que la commande échoue si aucune source n'est fournie."""
    result = runner.invoke(app, ["importer"])
    assert result.exit_code == 1
    assert "Vous devez fournir un fichier YAML ou au moins une URL" in result.stdout

def test_import_yaml_and_cli_uses_both(tmp_path, mock_youtube_dl):
    """Vérifie que si un fichier et des options CLI sont fournis, les deux sont traités."""
    yaml_content = 'artistes:\n  - name: "YAML Artist"\n    tunes: ["https://tune_yaml"]'
    config_file = tmp_path / "config.yml"
    config_file.write_text(yaml_content)
    result = runner.invoke(app, [
        "importer", str(config_file),
        "--tune", "https://tune_cli",
        "-o", str(tmp_path)
    ])
    assert result.exit_code == 0, result.stdout
    assert "Traitement de l'artiste : YAML Artist" in result.stdout
    assert "Traitement du morceau : https://tune_cli" in result.stdout
    # 1 call for yaml tune, 1 for cli tune
    assert mock_youtube_dl.download.call_count == 2
