# src/playlist_downloader/domain/errors.py
from dataclasses import dataclass

@dataclass(frozen=True)
class AppError:
    """Classe de base pour les erreurs de l'application."""
    message: str

@dataclass(frozen=True)
class AuthenticationError(AppError):
    """Erreur liée à l'authentification Google."""
    pass

@dataclass(frozen=True)
class YouTubeApiError(AppError):
    """Erreur lors de l'interaction avec l'API YouTube."""
    pass

@dataclass(frozen=True)
class DownloaderError(AppError):
    """Erreur liée au processus de téléchargement."""
    pass
