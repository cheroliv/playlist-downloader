import typer
import logging
from rich.console import Console
import re
import yaml
import os

# Correction des imports pour la nouvelle structure
from .auth import get_credentials
from .youtube_api import (
    create_playlist as api_create_playlist, 
    delete_playlist as api_delete_playlist,
    get_playlist_url as api_get_playlist_url
)
from . import logger_config # Important pour initialiser le logger

# Import des nouveaux éléments d'architecture
from .domain.models import Playlist
from .adapters.ytdlp_adapter import YTDLPAdapter
from .domain.errors import AppError, DownloaderError

# Initialisation
app = typer.Typer(
    name="playlist-downloader",
    help="Un outil CLI pour gérer les playlists YouTube.",
    add_completion=False,
)
console = Console()
logger = logging.getLogger(__name__)

def _handle_error(error: AppError):
    """Affiche un message d'erreur formaté et quitte l'application."""
    # The monad returns a tuple (value, has_value), we only need the value
    error_obj, _ = error
    console.print(f"[bold red]Erreur :[/bold red] {error_obj.message}")
    raise typer.Exit(code=1)


@app.command(name="creer")
def create_playlist(
    titre: str = typer.Option(..., "--titre", "-t", help="Le titre de la nouvelle playlist."),
    description: str = typer.Option("", "--description", "-d", help="La description de la playlist."),
    public: bool = typer.Option(False, "--public", help="Rendre la playlist publique."),
):
    """
    Crée une nouvelle playlist YouTube.
    """
    logger.info("Commande 'creer' initiée.")
    console.print("🔐 Tentative d'authentification auprès de Google...")
    
    get_credentials().map(
        lambda creds: (
            console.print("[bold green]✓ Authentification réussie ![/bold green]"),
            creds
        )
    ).bind(
        lambda creds: (
            console.print(f"📡 Création de la playlist '{titre}' en cours..."),
            api_create_playlist(creds, titre, description, not public)
        )
    ).map(
        lambda playlist_id: (
            console.print(f"[bold green]✓ Playlist créée avec succès ![/bold green]"),
            console.print(f"  ✨ ID: {playlist_id}"),
            console.print(f"  🔗 URL: https://www.youtube.com/playlist?list={playlist_id}")
        )
    ).catch(
        _handle_error
    )


@app.command(name="telecharger")
def download_playlist(
    url: str = typer.Argument(..., help="L'URL de la playlist à télécharger."),
    output_dir: str = typer.Option("downloads", "--output", "-o", help="Le dossier de destination."),
):
    """
    Télécharge une playlist YouTube en fichiers MP3.
    """
    logger.info(f"Commande 'telecharger' initiée pour l'URL : {url}")
    console.print(f"📥 Préparation du téléchargement de la playlist...")

    playlist_id_match = re.search(r"list=([\w-]+)", url)
    if not playlist_id_match:
        _handle_error(AppError("URL de playlist invalide."))
    
    playlist_id = playlist_id_match.group(1)
    playlist = Playlist(playlist_id=playlist_id, title=f"Playlist {playlist_id}", url=url)

    downloader = YTDLPAdapter()
    
    downloader.download_playlist(playlist, output_dir).map(
        lambda success_msg: console.print(f"[bold green]✓ {success_msg}[/bold green]")
    ).catch(
        _handle_error
    )

@app.command(name="detruire")
def delete_playlist_command(
    playlist_id: str = typer.Argument(..., help="L'ID de la playlist à supprimer."),
):
    """
    Supprime une playlist YouTube.
    """
    logger.info(f"Commande 'detruire' initiée pour la playlist ID : {playlist_id}")
    
    console.print("🔐 Tentative d'authentification auprès de Google...")
    get_credentials().map(
        lambda creds: (
            console.print("[bold green]✓ Authentification réussie ![/bold green]"),
            creds
        )
    ).bind(
        lambda creds: (
            console.print(f"🔥 Suppression de la playlist '{playlist_id}' en cours..."),
            api_delete_playlist(creds, playlist_id)
        )
    ).map(
        lambda success_msg: console.print(f"[bold green]✓ {success_msg}[/bold green]")
    ).catch(
        _handle_error
    )

@app.command(name="partager")
def share_playlist(
    playlist_id: str = typer.Argument(..., help="L'ID de la playlist à partager."),
):
    """
    Récupère l'URL de partage d'une playlist YouTube.
    """
    logger.info(f"Commande 'partager' initiée pour la playlist ID : {playlist_id}")
    
    console.print("🔐 Tentative d'authentification auprès de Google...")
    get_credentials().map(
        lambda creds: (
            console.print("[bold green]✓ Authentification réussie ![/bold green]"),
            creds
        )
    ).bind(
        lambda creds: (
            console.print(f"🔗 Récupération de l'URL pour la playlist '{playlist_id}'..."),
            api_get_playlist_url(creds, playlist_id)
        )
    ).map(
        lambda url: (
            console.print(f"[bold green]✓ URL récupérée avec succès ![/bold green]"),
            console.print(f"  🔗 {url}")
        )
    ).catch(
        _handle_error
    )

@app.command(name="importer")
def import_from_yaml(
    file_path: str = typer.Argument("musics.yml", help="Le chemin vers le fichier YAML à importer."),
    output_dir: str = typer.Option("downloads", "--output", "-o", help="Le dossier de destination principal."),
):
    """
    Importe et télécharge des morceaux depuis un fichier YAML.
    """
    logger.info(f"Commande 'importer' initiée pour le fichier : {file_path}")
    
    try:
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        _handle_error((DownloaderError(f"Le fichier '{file_path}' est introuvable."), None))
    except yaml.YAMLError as e:
        _handle_error((DownloaderError(f"Erreur de syntaxe dans le fichier YAML : {e}"), None))

    downloader = YTDLPAdapter()
    
    for artist in data.get('artistes', []):
        artist_name = artist.get('name')
        tunes = artist.get('tunes')

        if not artist_name or not tunes:
            console.print(f"[yellow]Artiste '{artist_name or 'Inconnu'}' ignoré (pas de morceaux ou nom manquant).[/yellow]")
            continue

        artist_dir = os.path.join(output_dir, artist_name)
        os.makedirs(artist_dir, exist_ok=True)
        
        console.print(f"\n[bold cyan]Téléchargement pour l'artiste : {artist_name}[/bold cyan]")
        
        for i, tune_url in enumerate(tunes):
            console.print(f"  ({i+1}/{len(tunes)}) Téléchargement de : {tune_url}")
            # Nous créons un objet Playlist factice car l'adaptateur l'exige.
            playlist = Playlist(playlist_id=f"tune_{i}", title=f"Tune {i}", url=tune_url)
            
            result = downloader.download_playlist(playlist, artist_dir)
            
            if result.is_right():
                console.print(f"  [green]✓ {result.value}[/green]")
            else:
                # La valeur d'erreur est dans result.monoid[0]
                error_obj, _ = result.monoid
                console.print(f"  [bold red]✗ Erreur : {error_obj.message}[/bold red]")


if __name__ == "__main__":
    app()
