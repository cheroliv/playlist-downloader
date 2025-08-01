import pytest
from typer.testing import CliRunner
from unittest.mock import MagicMock, patch
from pymonad.either import Right, Left

from playlist_downloader.cli import app
from playlist_downloader.domain.errors import DownloaderError

runner = CliRunner()

@pytest.fixture
def mock_ytdlp_adapter(mocker):
    """Fixture pour mocker YTDLPAdapter."""
    mock_adapter_instance = MagicMock()
    mock_adapter_instance.download_playlist.return_value = Right("Téléchargement réussi")
    
    mock_adapter_class = MagicMock(return_value=mock_adapter_instance)
    mocker.patch('playlist_downloader.cli.YTDLPAdapter', mock_adapter_class)
    
    return mock_adapter_instance

def test_import_from_yaml_success(tmp_path, mock_ytdlp_adapter):
    """
    Vérifie que la commande 'importer' fonctionne avec un fichier YAML valide.
    """
    yaml_content = """
artistes:
  - name: "Artiste 1"
    tunes:
      - "url1"
      - "url2"
  - name: "Artiste 2"
    tunes:
      - "url3"
"""
    yaml_file = tmp_path / "musics.yml"
    yaml_file.write_text(yaml_content)

    result = runner.invoke(app, ["importer", str(yaml_file)])

    assert result.exit_code == 0
    assert "Téléchargement pour l'artiste : Artiste 1" in result.stdout
    assert "Téléchargement pour l'artiste : Artiste 2" in result.stdout
    assert mock_ytdlp_adapter.download_playlist.call_count == 3

def test_import_file_not_found():
    """
    Vérifie que la commande gère correctement un fichier non trouvé.
    """
    result = runner.invoke(app, ["importer", "non_existent_file.yml"])

    assert result.exit_code == 1
    assert "Erreur" in result.stdout
    assert "introuvable" in result.stdout

def test_import_invalid_yaml(tmp_path):
    """
    Vérifie la gestion d'un fichier YAML malformé.
    """
    invalid_yaml_content = "artistes: - name: 'Artiste 1'"
    yaml_file = tmp_path / "invalid.yml"
    yaml_file.write_text(invalid_yaml_content)

    result = runner.invoke(app, ["importer", str(yaml_file)])

    assert result.exit_code == 1
    assert "Erreur" in result.stdout
    assert "syntaxe" in result.stdout

def test_import_skips_incomplete_entries(tmp_path, mock_ytdlp_adapter):
    """
    Vérifie que les artistes avec des données manquantes sont ignorés.
    """
    yaml_content = """
artistes:
  - name: "Artiste Valide"
    tunes:
      - "url1"
  - name: "Artiste Sans Morceaux"
  - tunes: ["url2"] # Nom manquant
"""
    yaml_file = tmp_path / "musics.yml"
    yaml_file.write_text(yaml_content)

    result = runner.invoke(app, ["importer", str(yaml_file)])

    assert result.exit_code == 0
    assert "Artiste 'Artiste Sans Morceaux' ignoré" in result.stdout
    assert "Artiste 'Inconnu' ignoré" in result.stdout
    # S'assurer qu'on n'a appelé le téléchargement que pour l'artiste valide
    mock_ytdlp_adapter.download_playlist.assert_called_once()
