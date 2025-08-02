# src/playlist_downloader/adapters/ytdlp_adapter.py
import logging
import yt_dlp
import re
from pathlib import Path
from pymonad.either import Left, Right, Either

from domain.models import Playlist
from domain.ports import MusicDownloader
from domain.errors import DownloaderError

logger = logging.getLogger(__name__)


class YTDLPAdapter(MusicDownloader):
    def _get_ydl_opts(self, destination: str, quality: str, no_overwrites: bool, is_playlist: bool):
        """Crée les options de base pour yt-dlp."""
        audio_quality = '0' if quality == 'best' else quality
        return {
            'format': 'bestaudio/best',
            'outtmpl': f'{destination}/%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': audio_quality,
            }],
            'ignoreerrors': True,
            'verbose': False,
            'no_overwrites': no_overwrites,
            'noplaylist': not is_playlist,
        }

    def download_tune(self, tune_url: str, destination: str, quality: str = "192", green: bool = False) -> Either[DownloaderError, str]:
        """
        Downloads a single audio track from a YouTube URL.
        If green is True, it checks if the file exists before downloading.
        """
        logger.info(f"Tentative de téléchargement du morceau : {tune_url}")
        
        try:
            # 1. Get video info without downloading
            with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
                info = ydl.extract_info(tune_url, download=False)
                title = info.get('title', 'unknown_title')
                video_id = info.get('id', 'unknown_id')
                # Clean title for file path
                safe_title = re.sub(r'[^\w\s-]', '', title).strip()
                expected_file = Path(destination) / f"{safe_title}.mp3"

            # 2. Check if file exists if green mode is on
            if green and expected_file.exists():
                message = f"Morceau '{title}' déjà présent. Téléchargement ignoré."
                logger.info(message)
                return Right(message)

            # 3. Download the tune
            ydl_opts = self._get_ydl_opts(destination, quality, green, is_playlist=False)
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # We use the specific video_id to avoid playlist downloads
                result_code = ydl.download([f"https://www.youtube.com/watch?v={video_id}"])

            if result_code == 0:
                success_message = f"Morceau '{title}' téléchargé avec succès dans '{destination}'."
                logger.info(success_message)
                return Right(success_message)
            else:
                error_message = f"Erreur lors du téléchargement du morceau '{title}'."
                logger.error(f"Échec du téléchargement du morceau '{title}' avec le code {result_code}")
                return Left(DownloaderError(error_message))

        except Exception as e:
            error_message = f"Une erreur inattendue est survenue : {e}"
            logger.critical(f"Erreur critique lors du téléchargement : {e}", exc_info=True)
            return Left(DownloaderError(error_message))

    def download_playlist(self, playlist: Playlist, destination: str, quality: str = "192", green: bool = False) -> Either[DownloaderError, str]:
        """
        Downloads all audio tracks from a YouTube playlist to a specified local directory.
        """
        logger.info(f"Début du téléchargement de la playlist '{playlist.title}'...")
        
        ydl_opts = self._get_ydl_opts(destination, quality, green, is_playlist=True)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                result_code = ydl.download([playlist.url])

            if result_code == 0:
                success_message = f"Playlist '{playlist.title}' téléchargée avec succès dans '{destination}'."
                logger.info(f"Playlist '{playlist.title}' téléchargée avec succès.")
                return Right(success_message)
            else:
                error_message = f"Erreur lors du téléchargement de la playlist '{playlist.title}'."
                logger.error(f"Échec du téléchargement de la playlist '{playlist.title}' avec le code de sortie {result_code}")
                return Left(DownloaderError(error_message))

        except Exception as e:
            error_message = f"Une erreur inattendue est survenue : {e}"
            logger.critical(f"Erreur critique lors du téléchargement : {e}", exc_info=True)
            return Left(DownloaderError(error_message))
