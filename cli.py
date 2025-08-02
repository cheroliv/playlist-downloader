import typer
import logging
from rich.console import Console
import re
import yaml
from pathlib import Path
import yt_dlp
from typing import Optional

# App-specific imports
from auth import get_credentials
from youtube_api import (
    create_playlist as api_create_playlist,
    delete_playlist as api_delete_playlist,
    get_playlist_url as api_get_playlist_url
)
import logger_config
from domain.models import Playlist
from adapters.ytdlp_adapter import YTDLPAdapter
from domain.errors import AppError, DownloaderError
from pymonad.either import Either, Left
from i18n import get_message, set_lang, get_default_lang

# Initialization
console = Console()
logger = logging.getLogger(__name__)
downloader = YTDLPAdapter()

# Create the Typer app object
app = typer.Typer(
    name="playlist-manager",
    help="A CLI tool to manage YouTube playlists.",
    add_completion=False,
)

# --- State and Callbacks ---

state = {"lang": get_default_lang()}
set_lang(state["lang"])

@app.callback()
def main_callback(
    lang: Optional[str] = typer.Option(
        None,
        "--lang",
        help="Set the language for output messages (e.g., 'en' or 'fr').",
        show_default=False,
    )
):
    """Manage YouTube playlists from the command line."""
    if lang:
        set_lang(lang)
        state["lang"] = lang
        logger.info(f"Language explicitly set to: {lang}")

# --- Helper Functions ---

def _handle_error(error: AppError):
    """Displays a formatted error message and exits the application."""
    error_obj, _ = error
    console.print(f"[bold red]Error:[/bold red] {error_obj.message}")
    raise typer.Exit(code=1)

def _handle_auth_flow() -> Either[AppError, any]:
    """Handles the authentication flow and displays messages."""
    console.print(f"🔐 {get_message('auth_attempt')}")
    return get_credentials().map(
        lambda creds: (
            console.print(f"[bold green]✓ {get_message('auth_success')}[/bold green]"),
            creds
        )
    ).catch(
        lambda err: _handle_error(Left((AppError(get_message('auth_error', error=err[0].message)), False)))
    )

# --- CLI Commands ---

@app.command(name="create")
def create_playlist(
    name: str = typer.Option(..., "--name", "-n", help=get_message("help_create_name")),
    description: str = typer.Option("", "--description", "-d", help=get_message("help_create_description")),
    public: bool = typer.Option(False, "--public", help=get_message("help_create_public")),
):
    """Creates a new YouTube playlist."""
    logger.info("Command 'create' initiated.")
    _handle_auth_flow().bind(
        lambda creds: (
            console.print(f"📡 {get_message('creating_playlist', name=name)}..."),
            api_create_playlist(creds, name, description, not public)
        )
    ).map(
        lambda url: console.print(f"[bold green]✓ {get_message('playlist_created', name=name, url=url)}[/bold green]")
    ).catch(_handle_error)


@app.command(name="download")
def download_playlist(
    url: str = typer.Argument(..., help=get_message("help_download_url")),
    output_dir: str = typer.Option("downloads", "--output", "-o", help=get_message("help_import_output")),
    quality: str = typer.Option("192", "--quality", "-q", help=get_message("help_import_quality")),
    green: bool = typer.Option(False, "--green", help=get_message("help_green")),
):
    """Downloads a YouTube playlist as MP3 files."""
    logger.info(f"Command 'download' initiated for URL: {url}")
    console.print(f"📥 {get_message('preparing_download')}...")

    playlist_id_match = re.search(r"list=([\w-]+)", url)
    if not playlist_id_match:
        _handle_error(Left((AppError("Invalid playlist URL."), False)))

    playlist_id = playlist_id_match.group(1)
    playlist = Playlist(playlist_id=playlist_id, title=f"Playlist {playlist_id}", url=url)

    downloader.download_playlist(playlist, output_dir, quality, green).map(
        lambda success_msg: console.print(f"[bold green]✓ {success_msg}[/bold green]")
    ).catch(_handle_error)


@app.command(name="update")
def update_playlist(
    url: str = typer.Argument(..., help="URL of the playlist to synchronize."),
    local_dir: Path = typer.Argument(..., help="The local directory to synchronize.", exists=True, file_okay=False, dir_okay=True, readable=True),
    quality: int = typer.Option(0, "--quality", "-q", min=0, max=9, help="Audio quality (0=best, 9=worst)."),
    delete: bool = typer.Option(False, "--delete", help="Delete local files no longer in the playlist."),
):
    """Synchronizes a local folder with a YouTube playlist."""
    logger.info(f"Command 'update' initiated for URL: {url}")
    console.print(f"🔄 {get_message('preparing_sync')}...")

    try:
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "extract_flat": True}) as ydl:
            info = ydl.extract_info(url, download=False)
            remote_videos = {re.sub(r'[^A-Za-z0-9_]', '', entry['title']): entry['url'] for entry in info['entries']}
    except Exception as e:
        _handle_error(Left((AppError(f"Could not fetch playlist info: {e}"), False)))

    console.print(f"📡 {get_message('remote_playlist_info', count=len(remote_videos), title=info.get('title'))}")

    local_files = {f.stem: f for f in local_dir.glob("*.mp3")}
    sanitized_local_files = {re.sub(r'[^A-Za-z0-9_]', '', k): v for k, v in local_files.items()}
    console.print(f"📁 {get_message('local_folder_info', count=len(local_files))}")

    videos_to_download = {k: v for k, v in remote_videos.items() if k not in sanitized_local_files}
    console.print(f"📥 {get_message('files_to_download', count=len(videos_to_download))}")

    if videos_to_download:
        console.print(f"\n[bold]🚀 {get_message('starting_download')}...[/bold]")
        for stem, video_url in videos_to_download.items():
            downloader.download_tune(video_url, str(local_dir), str(quality), green=True).map(
                lambda msg: console.print(f"  - [bold green]✓[/bold green] {msg}")
            ).catch(lambda err: console.print(f"  - [bold red]✗[/bold red] {err[0].message}"))

    if delete:
        files_to_delete = {k: v for k, v in sanitized_local_files.items() if k not in remote_videos}
        console.print(f"🔥 {get_message('files_to_delete', count=len(files_to_delete))}")
        if files_to_delete:
            console.print(f"\n[bold]🗑️ {get_message('starting_deletion')}...[/bold]")
            for stem, path in files_to_delete.items():
                try:
                    path.unlink()
                    console.print(f"  - [bold green]✓ {get_message('file_deleted', name=path.name)}[/bold green]")
                except OSError as e:
                    console.print(f"  - [bold red]✗ {get_message('file_deletion_error', name=path.name, error=e)}[/bold red]")

    console.print(f"\n[bold green]✨ {get_message('sync_completed')}![/bold green]")


@app.command(name="delete")
def delete_playlist(
    name: str = typer.Argument(..., help=get_message("help_delete_name")),
):
    """Deletes a YouTube playlist."""
    logger.info(f"Command 'delete' initiated for playlist: {name}")
    _handle_auth_flow().bind(
        lambda creds: (
            console.print(f"🔥 {get_message('deleting_playlist', name=name)}..."),
            api_delete_playlist(creds, name)
        )
    ).map(
        lambda _: console.print(f"[bold green]✓ {get_message('playlist_deleted', name=name)}[/bold green]")
    ).catch(_handle_error)


@app.command(name="share")
def share_playlist(
    name: str = typer.Argument(..., help=get_message("help_share_name")),
):
    """Gets the shareable URL of a YouTube playlist."""
    logger.info(f"Command 'share' initiated for playlist: {name}")
    _handle_auth_flow().bind(
        lambda creds: (
            console.print(f"🔗 {get_message('getting_url', name=name)}..."),
            api_get_playlist_url(creds, name)
        )
    ).map(
        lambda url: console.print(f"[bold green]✓ {get_message('playlist_shared', name=name, url=url)}[/bold green]")
    ).catch(_handle_error)


@app.command(name="import", help="Import and download tracks from a YAML file or direct URLs.")
def import_tunes(
    ctx: typer.Context,
    file_path: Path = typer.Argument(None, help=get_message("help_import_file"), exists=True, file_okay=True, dir_okay=False, readable=True, resolve_path=True),
    tunes: list[str] = typer.Option(None, "--tune", "-t", help="URL of a track to download. Can be used multiple times."),
    playlists: list[str] = typer.Option(None, "--playlist", "-p", help="URL of a playlist to download. Can be used multiple times."),
    output_dir: Path = typer.Option(Path("downloads"), "--output-dir", "-o", help=get_message("help_import_output"), file_okay=False, dir_okay=True, writable=True, resolve_path=True),
    quality: int = typer.Option(0, "--quality", "-q", min=0, max=9, help=get_message("help_import_quality")),
    flat: bool = typer.Option(False, "--flat", "-f", help=get_message("help_import_flat")),
    green: bool = typer.Option(False, "--green", help=get_message("help_green")),
):
    """Command to import and download tracks."""
    if not file_path and not tunes and not playlists:
        console.print(f"[bold red]Error:[/bold red] {get_message('import_source_missing')}")
        raise typer.Exit(code=1)

    logger.info(f"Output directory: {output_dir}, Quality: {quality}, Green mode: {green}")
    output_dir.mkdir(parents=True, exist_ok=True)

    def handle_download_result(result: Either[DownloaderError, str], url: str):
        if result.is_right():
            msg = result.value
            console.print(f"  [bold green]✓[/bold green] {Path(url).name}: {msg}")
        else:
            # The monad from the adapter already contains the error object
            err_obj = result.value
            console.print(f"  [bold red]✗[/bold red] {Path(url).name}: {err_obj.message}")

    if file_path:
        logger.info(f"Starting import from file: {file_path}, Flat structure: {flat}")
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                data = yaml.safe_load(file)
            artists = data.get("artists", [])
            for artist in artists:
                artist_name = artist.get("name")
                console.print(f"Processing artist: {artist_name}")
                final_output_dir = output_dir if flat else output_dir / artist_name
                final_output_dir.mkdir(parents=True, exist_ok=True)
                
                for tune_url in artist.get("tunes", []):
                    download_result = downloader.download_tune(tune_url, str(final_output_dir), str(quality), green)
                    handle_download_result(download_result, tune_url)
                for playlist_url in artist.get("playlists", []):
                    playlist = Playlist(playlist_id="N/A", title="N/A", url=playlist_url)
                    download_result = downloader.download_playlist(playlist, str(final_output_dir), str(quality), green)
                    handle_download_result(download_result, playlist_url)
        except (yaml.YAMLError, IOError) as e:
            _handle_error(Left(AppError(get_message("import_error", yaml_file=file_path, error=e))))

    if tunes or playlists:
        logger.info("Starting import from CLI options.")
        for tune_url in tunes or []:
            download_result = downloader.download_tune(tune_url, str(output_dir), str(quality), green)
            handle_download_result(download_result, tune_url)
        for playlist_url in playlists or []:
            playlist = Playlist(playlist_id="N/A", title="N/A", url=playlist_url)
            download_result = downloader.download_playlist(playlist, str(output_dir), str(quality), green)
            handle_download_result(download_result, playlist_url)

    console.print(f"\n[bold green]✨ {get_message('import_completed', yaml_file=file_path if file_path else 'CLI options')}![/bold green]")


if __name__ == "__main__":
    app()