import typer
import logging
from rich.console import Console
import re
import yaml
from pathlib import Path
import yt_dlp

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
from pymonad.either import Right, Left

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
    quality: str = typer.Option("192", "--quality", "-q", help="Qualité audio (ex: '192', '320', 'best')."),
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
    
    downloader.download_playlist(playlist, output_dir, quality).map(
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

@app.command(name="importer", help="Importe et télécharge des morceaux depuis un fichier YAML ou des URLs directes.")
def import_tunes(
    ctx: typer.Context,
    file_path: Path = typer.Argument(
        None,  # Rend l'argument optionnel
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Chemin vers le fichier YAML contenant les artistes et les morceaux.",
    ),
    tunes: list[str] = typer.Option(
        None, "--tune", "-t", help="URL d'un morceau à télécharger. Peut être utilisé plusieurs fois."
    ),
    playlists: list[str] = typer.Option(
        None, "--playlist", "-p", help="URL d'une playlist à télécharger. Peut être utilisé plusieurs fois."
    ),
    output_dir: Path = typer.Option(
        Path("downloads"),
        "--output-dir",
        "-o",
        help="Dossier de destination pour les téléchargements.",
        file_okay=False,
        dir_okay=True,
        writable=True,
        resolve_path=True,
    ),
    audio_quality: int = typer.Option(
        0,
        "--audio-quality",
        "-q",
        min=0,
        max=9,
        help="Qualité audio (0 pour la meilleure, 9 pour la moins bonne).",
    ),
    flat: bool = typer.Option(
        False,
        "--flat",
        "-f",
        help="Télécharger tous les morceaux dans le dossier de sortie sans créer de sous-dossiers par artiste (utilisé uniquement avec un fichier YAML).",
    ),
):
    """
    Commande pour importer et télécharger des morceaux.
    """
    if not file_path and not tunes and not playlists:
        console.print("[bold red]Erreur :[/bold red] Vous devez fournir un fichier YAML ou au moins une URL via --tune ou --playlist.")
        raise typer.Exit(code=1)

    logger.info(f"Dossier de sortie : {output_dir}")
    logger.info(f"Qualité audio sélectionnée : {audio_quality}")

    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Le dossier de sortie '{output_dir}' est prêt.")

    if file_path:
        logger.info(f"Démarrage de l'importation depuis le fichier : {file_path}")
        logger.info(f"Structure de dossiers plate : {flat}")
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                data = yaml.safe_load(file)
                artists = data.get("artistes", [])
                logger.info(f"{len(artists)} artistes trouvés dans le fichier.")

            for artist in artists:
                artist_name = artist.get("name")
                yaml_tunes = artist.get("tunes", [])
                yaml_playlists = artist.get("playlists", [])

                if not artist_name or (not yaml_tunes and not yaml_playlists):
                    logger.warning(
                        f"Artiste ignoré car le nom ou les listes de contenus sont manquants : {artist}"
                    )
                    continue

                console.print(f"🎤 Traitement de l'artiste : [bold cyan]{artist_name}[/bold cyan]")
                
                final_output_dir = output_dir if flat else output_dir / artist_name
                final_output_dir.mkdir(parents=True, exist_ok=True)

                for tune_url in yaml_tunes:
                    console.print(f"  - Traitement du morceau : [blue]{tune_url}[/blue]")
                    _download_with_check(tune_url, final_output_dir, audio_quality, is_playlist=False)

                for playlist_url in yaml_playlists:
                    console.print(f"  - Traitement de la playlist : [blue]{playlist_url}[/blue]")
                    _download_with_check(playlist_url, final_output_dir, audio_quality, is_playlist=True)

        except (yaml.YAMLError, IOError) as e:
            logger.error(
                f"Erreur lors de la lecture ou de l'analyse du fichier YAML : {e}",
                exc_info=True,
            )
            console.print(f"[bold red]Erreur :[/bold red] Impossible de lire ou d'analyser le fichier YAML : {e}")
            raise typer.Exit(code=1)
    
    if tunes or playlists:
        logger.info("Démarrage de l'importation depuis les options CLI.")
        # En mode CLI, on télécharge tout dans le dossier de sortie (équivalent de --flat)
        for tune_url in tunes or []:
            console.print(f"  - Traitement du morceau : [blue]{tune_url}[/blue]")
            _download_with_check(tune_url, output_dir, audio_quality, is_playlist=False)
        
        for playlist_url in playlists or []:
            console.print(f"  - Traitement de la playlist : [blue]{playlist_url}[/blue]")
            _download_with_check(playlist_url, output_dir, audio_quality, is_playlist=True)


    console.print("\n[bold green]✨ Importation et téléchargement terminés ![/bold green]")


def _download_with_check(url: str, output_dir: Path, audio_quality: int, is_playlist: bool):
    """
    Vérifie si le contenu doit être téléchargé et lance le téléchargement.
    """
    ydl_opts_base = {
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": str(audio_quality),
            }
        ],
        "quiet": True,
        "no_warnings": True,
        "noplaylist": not is_playlist,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts_base) as ydl:
            # Récupérer les informations sans télécharger
            info = ydl.extract_info(url, download=False)
            
            if is_playlist:
                entries = info.get("entries", [])
                console.print(f"    [dim]Playlist '{info.get('title')}' contenant {len(entries)} morceaux.[/dim]")
                for entry in entries:
                    _process_entry(entry, output_dir, ydl_opts_base)
            else:
                _process_entry(info, output_dir, ydl_opts_base)

    except Exception as e:
        logger.error(
            f"Erreur lors de la récupération des informations pour {url}: {e}",
            exc_info=True,
        )
        console.print(f"  [bold red]✗ Échec de la récupération des informations.[/bold red]")


def _process_entry(entry_info: dict, output_dir: Path, ydl_opts: dict):
    """
    Traite et télécharge une seule entrée (morceau).
    """
    title = entry_info.get("title", "N/A")
    video_id = entry_info.get("id", "N/A")
    # Nettoyer le titre pour créer un nom de fichier valide
    safe_title = re.sub(r'[^A-Za-z0-9_]', '', title)
    expected_filename = output_dir / f"{safe_title}.mp3"

    console.print(f"    - [dim]Vérification de '{title}'...[/dim]")

    if expected_filename.exists():
        console.print(f"    [bold yellow]✓ Ignoré (déjà présent).[/bold yellow]")
        return

    download_path_template = output_dir / "%(title)s.%(ext)s"
    ydl_opts["outtmpl"] = str(download_path_template)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f"https://www.youtube.com/watch?v={video_id}"])
        console.print(f"    [bold green]✓ Téléchargement réussi.[/bold green]")
    except Exception as e:
        logger.error(
            f"Erreur lors du téléchargement de {title}: {e}",
            exc_info=True,
        )
        console.print(f"    [bold red]✗ Échec du téléchargement.[/bold red]")


if __name__ == "__main__":
    app()
