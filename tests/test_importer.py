import pytest
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock
from pathlib import Path

from playlist_downloader.cli import app

runner = CliRunner()

@pytest.fixture
def mock_youtube_dl():
    """Fixture pour mocker yt_dlp.YoutubeDL."""
    with patch('yt_dlp.YoutubeDL') as mock:
        mock_instance = MagicMock()
        mock.return_value.__enter__.return_value = mock_instance

        def side_effect(url, download=True):
            if "playlist" in url:
                return {"title": url, "entries": [{"id": f"v_{url}_1", "title": f"Song from {url} 1"}, {"id": f"v_{url}_2", "title": f"Song from {url} 2"}]}
            else:
                return {"id": url.replace("https://", ""), "title": f"Tune {url}"}
        
        mock_instance.extract_info.side_effect = side_effect
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
    assert result.exit_code == 0
    assert "Traitement de l'artiste : Artist With Playlist" in result.stdout
    assert mock_youtube_dl.download.call_count == 3  # 2 from playlist + 1 from tune

def test_import_yaml_skips_existing(tmp_path, mock_youtube_dl):
    """Vérifie que les fichiers existants sont ignorés en mode YAML."""
    artist_dir = tmp_path / "Test Artist"
    artist_dir.mkdir()
    # Appliquer la même logique de nettoyage que dans le CLI
    safe_title = "Songfromhttpsplaylist11"
    (artist_dir / f"{safe_title}.mp3").touch()

    mock_youtube_dl.extract_info.return_value = {
        "title": "playlist1", 
        "entries": [
            {"id": "v_playlist1_1", "title": "Song from https---playlist1 1"},
            {"id": "v_playlist1_2", "title": "Song from https---playlist1 2"}
        ]
    }

    yaml_content = 'artistes:\n  - name: "Test Artist"\n    playlists: ["https://playlist1"]'
    config_file = tmp_path / "config.yml"
    config_file.write_text(yaml_content)
    result = runner.invoke(app, ["importer", str(config_file), "-o", str(tmp_path)])
    
    assert result.exit_code == 0
    assert "Ignoré (déjà présent)" in result.stdout
    mock_youtube_dl.download.assert_called_once_with(['https://www.youtube.com/watch?v=v_https://playlist1_2'])

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
    assert result.exit_code == 0
    assert "Traitement du morceau : https://tune1" in result.stdout
    mock_youtube_dl.download.assert_called_once()

def test_import_cli_single_playlist(tmp_path, mock_youtube_dl):
    """Vérifie le téléchargement d'une seule playlist via les options CLI."""
    result = runner.invoke(app, ["importer", "--playlist", "https://playlist1", "-o", str(tmp_path)])
    assert result.exit_code == 0
    assert "Traitement de la playlist : https://playlist1" in result.stdout
    assert mock_youtube_dl.download.call_count == 2

def test_import_cli_multiple_sources(tmp_path, mock_youtube_dl):
    """Vérifie le téléchargement depuis plusieurs options --tune and --playlist."""
    result = runner.invoke(app, [
        "importer",
        "--tune", "https://tune1",
        "--playlist", "https://playlist1",
        "--tune", "https://tune2",
        "-o", str(tmp_path)
    ])
    assert result.exit_code == 0
    assert mock_youtube_dl.download.call_count == 4 # 1 (tune1) + 2 (playlist1) + 1 (tune2)

def test_import_cli_skips_existing(tmp_path, mock_youtube_dl):
    """Vérifie que les fichiers existants sont ignorés en mode CLI."""
    safe_title = "Tunehttpstune1"
    (tmp_path / f"{safe_title}.mp3").touch()
    mock_youtube_dl.extract_info.return_value = {"id": "tune1", "title": "Tune https---tune1"}
    result = runner.invoke(app, ["importer", "--tune", "https://tune1", "-o", str(tmp_path)])
    assert result.exit_code == 0
    assert "Ignoré (déjà présent)" in result.stdout
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
    assert result.exit_code == 0
    assert "Traitement de l'artiste : YAML Artist" in result.stdout
    assert "Traitement du morceau : https://tune_cli" in result.stdout
    assert mock_youtube_dl.download.call_count == 2
