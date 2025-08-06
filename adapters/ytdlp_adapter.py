import logging
import yt_dlp
import re
from pathlib import Path
from pymonad.either import Left, Right, Either

from adapters.mutagen_adapter import MutagenAdapter
from domain.models import Playlist
from domain.ports import MusicDownloader
from domain.errors import DownloaderError

logger = logging.getLogger(__name__)


class YTDLPAdapter(MusicDownloader):
    def __init__(self, mutagen_adapter: MutagenAdapter = MutagenAdapter()):
        self._mutagen_adapter = mutagen_adapter

    def _is_tune_already_present(self, tune_url: str, destination: str) -> bool:
        """Checks if a tune with the same URL is already in the destination."""
        dest_path = Path(destination)
        if not dest_path.is_dir():
            return False

        for file_path in dest_path.glob('*.mp3'):
            existing_url = self._mutagen_adapter.get_comment(file_path)
            if existing_url and existing_url.strip() == tune_url.strip():
                return True
        return False

    def _get_ydl_opts(self, destination: str, quality: str, no_overwrites: bool, is_playlist: bool):
        """Creates the base options for yt-dlp."""
        audio_quality = '0' if quality == 'best' else quality
        return {
            'format': 'bestaudio/best',
            'outtmpl': f'{destination}/%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': audio_quality,
            }, {
                'key': 'EmbedThumbnail',
            }, {
                'key': 'FFmpegMetadata',
                'add_metadata': True,
            }, {
                'key': 'ModifyTags',
                'tags': {
                    'comment': '%(webpage_url)s'
                }
            }],
            'ignoreerrors': True,
            'verbose': False,
            'no_overwrites': no_overwrites,
            'noplaylist': not is_playlist,
        }

    def download_tune(self, tune_url: str, destination: str, quality: str = "192", green: bool = False) -> Either[DownloaderError, str]:
        """
        Downloads a single audio track from a YouTube URL.
        If green is True, it checks if a file with the same source URL exists before downloading.
        """
        logger.info(f"Attempting to download tune: {tune_url}")

        try:
            # 1. Check if file exists if green mode is on
            if green and self._is_tune_already_present(tune_url, destination):
                message = f"Track from URL '{tune_url}' already exists. Skipping download."
                logger.info(message)
                return Right(message)

            # 2. Get video info for download
            with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
                info = ydl.extract_info(tune_url, download=False)
                title = info.get('title', 'unknown_title')
                video_id = info.get('id', 'unknown_id')

            # 3. Download the tune
            # We set no_overwrites to False here because our green check is now metadata-based.
            # The original check was filename-based, which is less reliable.
            ydl_opts = self._get_ydl_opts(destination, quality, no_overwrites=False, is_playlist=False)

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                result_code = ydl.download([f"https://www.youtube.com/watch?v={video_id}"])

            if result_code == 0:
                success_message = f"Track '{title}' downloaded successfully to '{destination}'."
                logger.info(success_message)
                return Right(success_message)
            else:
                error_message = f"Error downloading track '{title}'."
                logger.error(f"Failed to download track '{title}' with exit code {result_code}")
                return Left(DownloaderError(error_message))

        except Exception as e:
            error_message = f"An unexpected error occurred: {e}"
            logger.critical(f"Critical error during download: {e}", exc_info=True)
            return Left(DownloaderError(error_message))


    def download_playlist(self, playlist: Playlist, destination: str, quality: str = "192", green: bool = False) -> Either[DownloaderError, str]:
        """
        Downloads all audio tracks from a YouTube playlist to a specified local directory.
        """
        logger.info(f"Starting download of playlist '{playlist.title}'...")
        
        ydl_opts = self._get_ydl_opts(destination, quality, green, is_playlist=True)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                result_code = ydl.download([playlist.url])

            if result_code == 0:
                success_message = f"Playlist '{playlist.title}' downloaded successfully to '{destination}'."
                logger.info(f"Playlist '{playlist.title}' downloaded successfully.")
                return Right(success_message)
            else:
                error_message = f"Error downloading playlist '{playlist.title}'."
                logger.error(f"Failed to download playlist '{playlist.title}' with exit code {result_code}")
                return Left(DownloaderError(error_message))

        except Exception as e:
            error_message = f"An unexpected error occurred: {e}"
            logger.critical(f"Critical error during download: {e}", exc_info=True)
            return Left(DownloaderError(error_message))
