import logging
from pymonad.either import Left, Right
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from . import logger_config
from .domain.errors import YouTubeApiError

logger = logging.getLogger(__name__)

def create_playlist(credentials, title: str, description: str, private: bool):
    """
    Crée une playlist sur YouTube en utilisant les credentials fournis.

    Args:
        credentials: L'objet credentials obtenu via le flux OAuth.
        title: Le titre de la playlist.
        description: La description de la playlist.
        private: Si True, la playlist sera privée, sinon publique.

    Returns:
        Either: Un Right(playlist_id) en cas de succès, ou un Left(YouTubeApiError).
    """
    try:
        logger.info(f"Construction du service YouTube avec les credentials.")
        youtube = build('youtube', 'v3', credentials=credentials)

        privacy_status = 'private' if private else 'public'
        
        request_body = {
            'snippet': {
                'title': title,
                'description': description
            },
            'status': {
                'privacyStatus': privacy_status
            }
        }

        logger.info(f"Envoi de la requête de création de playlist '{title}'.")
        response = youtube.playlists().insert(
            part='snippet,status',
            body=request_body
        ).execute()

        playlist_id = response['id']
        logger.info(f"Playlist '{playlist_id}' créée avec succès.")
        return Right(playlist_id)

    except HttpError as e:
        error_message = f"Erreur API lors de la création de la playlist: {e.content.decode('utf-8')}"
        logger.error(f"Échec de la création de la playlist '{title}': {error_message}")
        return Left(YouTubeApiError(error_message))
    except Exception as e:
        logger.error(f"Une erreur inattendue est survenue: {e}")
        return Left(YouTubeApiError(f"Une erreur inattendue est survenue: {e}"))

def delete_playlist(credentials, playlist_id: str):
    """
    Supprime une playlist YouTube.

    Args:
        credentials: L'objet credentials obtenu via le flux OAuth.
        playlist_id: L'ID de la playlist à supprimer.

    Returns:
        Either: Un Right(success_message) en cas de succès, ou un Left(YouTubeApiError).
    """
    try:
        logger.info(f"Construction du service YouTube pour la suppression.")
        youtube = build('youtube', 'v3', credentials=credentials)

        logger.info(f"Envoi de la requête de suppression pour la playlist '{playlist_id}'.")
        youtube.playlists().delete(id=playlist_id).execute()

        success_message = f"Playlist '{playlist_id}' supprimée avec succès."
        logger.info(success_message)
        return Right(success_message)

    except HttpError as e:
        error_message = f"Erreur API lors de la suppression: {e.content.decode('utf-8')}"
        logger.error(f"Échec de la suppression de la playlist '{playlist_id}': {error_message}")
        return Left(YouTubeApiError(error_message))
    except Exception as e:
        logger.error(f"Une erreur inattendue est survenue lors de la suppression: {e}")
        return Left(YouTubeApiError(f"Une erreur inattendue est survenue: {e}"))