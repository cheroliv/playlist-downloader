import typer
import logging
from rich.console import Console
import re
import yaml
from pathlib import Path
import yt_dlp

# Correction des imports pour la nouvelle structure
from auth import get_credentials
from youtube_api import (
    create_playlist as api_create_playlist, 
    delete_playlist as api_delete_playlist,
    get_playlist_url as api_get_playlist_url
)
import logger_config # Important pour initialiser le logger

# Import des nouveaux éléments d'architecture
from domain.models import Playlist
from adapters.ytdlp_adapter import YTDLPAdapter
from domain.errors import AppError, DownloaderError
from pymonad.either import Right, Left, Either

# Initialisation
app = typer.Typer(
    name="playlist-downloader",
    help="Un outil CLI pour gérer les playlists YouTube.",
    add_completion=False,
)
console = Console()
logger = logging.getLogger(__name__)
downloader = YTDLPAdapter()


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
    green: bool = typer.Option(False, "--green", help="Si activé, ne télécharge pas un morceau s'il existe déjà."),
):
    """
    Télécharge une playlist YouTube en fichiers MP3.
    """
    logger.info(f"Commande 'telecharger' initiée pour l'URL : {url}")
    console.print(f"📥 Préparation du téléchargement de la playlist...")

    playlist_id_match = re.search(r"list=([\w-]+)", url)
    if not playlist_id_match:
        _handle_error(Left((AppError("URL de playlist invalide."), False)))
    
    playlist_id = playlist_id_match.group(1)
    # TODO: Get playlist title from API
    playlist = Playlist(playlist_id=playlist_id, title=f"Playlist {playlist_id}", url=url)
    
    downloader.download_playlist(playlist, output_dir, quality, green).map(
        lambda success_msg: console.print(f"[bold green]✓ {success_msg}[/bold green]")
    ).catch(
        _handle_error
    )

@app.command(name="mettre-a-jour")
def update_playlist(
    url: str = typer.Argument(..., help="L'URL de la playlist à synchroniser."),
    local_dir: Path = typer.Argument(..., help="Le dossier local à synchroniser.", exists=True, file_okay=False, dir_okay=True, readable=True),
    audio_quality: int = typer.Option(
        0,
        "--audio-quality",
        "-q",
        min=0,
        max=9,
        help="Qualité audio (0 pour la meilleure, 9 pour la moins bonne).",
    ),
    delete: bool = typer.Option(False, "--delete", help="Supprimer les fichiers locaux qui ne sont plus dans la playlist."),
):
    """
    Synchronise un dossier local avec une playlist YouTube.
    """
    logger.info(f"Commande 'mettre-a-jour' initiée pour l'URL : {url}")
    logger.info(f"Dossier local : {local_dir}")
    logger.info(f"Option de suppression activée : {delete}")

    console.print(f"🔄 Préparation de la synchronisation de la playlist...")

    # 1. Get remote playlist video titles
    try:
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "extract_flat": True}) as ydl:
            info = ydl.extract_info(url, download=False)
            remote_videos = {re.sub(r'[^A-Za-z0-9_]', '', entry['title']): entry['url'] for entry in info['entries']}
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des informations de la playlist: {e}", exc_info=True)
        console.print(f"[bold red]Erreur :[/bold red] Impossible de récupérer les informations de la playlist.")
        raise typer.Exit(code=1)

    console.print(f"📡 Playlist distante '{info.get('title')}' contient {len(remote_videos)} morceaux.")

    # 2. Get local file names
    local_files = {f.stem: f for f in local_dir.glob("*.mp3")}
    sanitized_local_files = {re.sub(r'[^A-Za-z0-9_]', '', k): v for k, v in local_files.items()}

    console.print(f"📁 Le dossier local contient {len(local_files)} morceaux.")

    # 3. Find videos to download
    videos_to_download_stems = set(remote_videos.keys()) - set(sanitized_local_files.keys())
    console.print(f"📥 {len(videos_to_download_stems)} nouveaux morceaux à télécharger.")

    # 4. Find local files to delete
    files_to_delete_stems = set(sanitized_local_files.keys()) - set(remote_videos.keys())
    if delete:
        console.print(f"🔥 {len(files_to_delete_stems)} morceaux locaux à supprimer.")

    # 5. Download missing videos
    if videos_to_download_stems:
        console.print("\n[bold]🚀 Démarrage du téléchargement...[/bold]")
        for video_stem in videos_to_download_stems:
            video_url = remote_videos[video_stem]
            downloader.download_tune(video_url, str(local_dir), str(audio_quality), green=True).map(
                lambda msg: console.print(f"  - [bold green]✓[/bold green] {msg}")
            ).catch(
                lambda err: console.print(f"  - [bold red]✗[/bold red] {err[0].message}")
            )

    # 6. Delete extra local files
    if delete and files_to_delete_stems:
        console.print("\n[bold]🗑️ Démarrage de la suppression...[/bold]")
        for file_stem in files_to_delete_stems:
            file_path = sanitized_local_files[file_stem]
            try:
                file_path.unlink()
                console.print(f"  - [bold green]✓ Supprimé :[/bold green] {file_path.name}")
            except OSError as e:
                logger.error(f"Erreur lors de la suppression du fichier {file_path}: {e}", exc_info=True)
                console.print(f"  - [bold red]✗ Échec de la suppression :[/bold red] {file_path.name}")


    console.print("\n[bold green]✨ Synchronisation terminée ![/bold green]")


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
    green: bool = typer.Option(
        False, 
        "--green", 
        help="Si activé, ne télécharge pas un morceau s'il existe déjà."
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
    logger.info(f"Mode Green activé : {green}")

    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Le dossier de sortie '{output_dir}' est prêt.")

    def handle_download_result(result: Either[DownloaderError, str], url: str):
        if result.is_right():
            msg = result.value
            console.print(f"  [bold green]✓[/bold green] {Path(url).name}: {msg}")
        else:
            err, _ = result.monoid
            console.print(f"  [bold red]✗[/bold red] {Path(url).name}: {err.message}")

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
                    logger.warning(f"Artiste ignoré car le nom ou les listes de contenus sont manquants : {artist}")
                    continue

                console.print(f"🎤 Traitement de l'artiste : [bold cyan]{artist_name}[/bold cyan]")
                
                final_output_dir = output_dir if flat else output_dir / artist_name
                final_output_dir.mkdir(parents=True, exist_ok=True)

                for tune_url in yaml_tunes:
                    console.print(f"  - Traitement du morceau : [blue]{tune_url}[/blue]")
                    result = downloader.download_tune(tune_url, str(final_output_dir), str(audio_quality), green)
                    handle_download_result(result, tune_url)

                for playlist_url in yaml_playlists:
                    console.print(f"  - Traitement de la playlist : [blue]{playlist_url}[/blue]")
                    playlist_id_match = re.search(r"list=([\w-]+)", playlist_url)
                    playlist_id = playlist_id_match.group(1) if playlist_id_match else "unknown_playlist"
                    playlist = Playlist(playlist_id=playlist_id, title=f"Playlist {playlist_id}", url=playlist_url)
                    result = downloader.download_playlist(playlist, str(final_output_dir), str(audio_quality), green)
                    handle_download_result(result, playlist_url)

        except (yaml.YAMLError, IOError) as e:
            logger.error(f"Erreur lors de la lecture ou de l'analyse du fichier YAML : {e}", exc_info=True)
            _handle_error((AppError(f"Impossible de lire ou d'analyser le fichier YAML : {e}"), False))
    
    if tunes or playlists:
        logger.info("Démarrage de l'importation depuis les options CLI.")
        for tune_url in tunes or []:
            console.print(f"  - Traitement du morceau : [blue]{tune_url}[/blue]")
            result = downloader.download_tune(tune_url, str(output_dir), str(audio_quality), green)
            handle_download_result(result, tune_url)
        
        for playlist_url in playlists or []:
            console.print(f"  - Traitement de la playlist : [blue]{playlist_url}[/blue]")
            playlist_id_match = re.search(r"list=([\w-]+)", playlist_url)
            playlist_id = playlist_id_match.group(1) if playlist_id_match else "unknown_playlist"
            playlist = Playlist(playlist_id=playlist_id, title=f"Playlist {playlist_id}", url=playlist_url)
            result = downloader.download_playlist(playlist, str(output_dir), str(audio_quality), green)
            handle_download_result(result, playlist_url)

    console.print("\n[bold green]✨ Importation et téléchargement terminés ![/bold green]")


if __name__ == "__main__":
    app()
