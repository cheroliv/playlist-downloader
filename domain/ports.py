from abc import ABC, abstractmethod
from pymonad.either import Either
from .models import Playlist


class MusicDownloader(ABC):
    """
    Port defining the contract for a music downloading service.
    """

    @abstractmethod
    def download_playlist(self, playlist: Playlist, destination: str) -> Either[str, str]:
        """
        Takes a playlist and a destination and downloads it.

        Returns:
            Either: A Right(success_message) or a Left(error_message).
        """
        pass