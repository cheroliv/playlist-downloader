# src/playlist_downloader/adapters/ytdlp_adapter.py
import logging
import yt_dlp
from pymonad.either import Left, Right, Either

from playlist_downloader.domain.models import Playlist
from playlist_downloader.domain.ports import MusicDownloader
from playlist_downloader.domain.errors import DownloaderError

logger = logging.getLogger(__name__)


class YTDLPAdapter(MusicDownloader):
    def download_playlist(self, playlist: Playlist, destination: str, quality: str = "192") -> Either[DownloaderError, str]:
        """
        Downloads all audio tracks from a YouTube playlist to a specified local directory.

        Args:
            playlist (Playlist): The playlist to download.
            destination (str): The local path to save the audio files.
            quality (str): The desired audio quality ('best', '192', etc.).

        Returns:
            Either[DownloaderError, str]: Right with a success message or Left with an error message.
        """
        logger.info(f"Début du téléchargement de la playlist '{playlist.title}'...")

        # '0' is the best quality for yt-dlp
        audio_quality = '0' if quality == 'best' else quality

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{destination}/%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': audio_quality,
            }],
            'ignoreerrors': True,
            'verbose': False,
        }

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
