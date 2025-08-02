import logging
from pymonad.either import Left, Right
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import logger_config
from domain.errors import YouTubeApiError

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
        logger.info(f"Building YouTube service with credentials.")
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

        logger.info(f"Sending playlist creation request for '{title}'.")
        response = youtube.playlists().insert(
            part='snippet,status',
            body=request_body
        ).execute()

        playlist_id = response['id']
        logger.info(f"Playlist '{playlist_id}' created successfully.")
        return Right(playlist_id)

    except HttpError as e:
        error_message = f"API error during playlist creation: {e.content.decode('utf-8')}"
        logger.error(f"Failed to create playlist '{title}': {error_message}")
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
        logger.info(f"Building YouTube service for deletion.")
        youtube = build('youtube', 'v3', credentials=credentials)

        logger.info(f"Sending deletion request for playlist '{playlist_id}'.")
        youtube.playlists().delete(id=playlist_id).execute()

        success_message = f"Playlist '{playlist_id}' deleted successfully."
        logger.info(success_message)
        return Right(success_message)

    except HttpError as e:
        error_message = f"API error during deletion: {e.content.decode('utf-8')}"
        logger.error(f"Failed to delete playlist '{playlist_id}': {error_message}")
        return Left(YouTubeApiError(error_message))
    except Exception as e:
        logger.error(f"An unexpected error occurred during deletion: {e}")
        return Left(YouTubeApiError(f"An unexpected error occurred during deletion: {e}"))

def get_playlist_url(credentials, playlist_id: str):
    """
    Construit et retourne l'URL de partage d'une playlist YouTube.

    Args:
        credentials: L'objet credentials obtenu via le flux OAuth.
        playlist_id: L'ID de la playlist.

    Returns:
        Either: Un Right(playlist_url) en cas de succès, ou un Left(YouTubeApiError).
    """
    try:
        logger.info(f"Building YouTube service to retrieve URL.")
        youtube = build('youtube', 'v3', credentials=credentials)

        logger.info(f"Checking existence of playlist '{playlist_id}'.")
        request = youtube.playlists().list(
            part="id",
            id=playlist_id
        )
        response = request.execute()

        if not response.get('items'):
            error_message = f"Playlist '{playlist_id}' not found."
            logger.error(f"Failed to retrieve URL: {error_message}")
            return Left(YouTubeApiError(error_message))

        playlist_url = f"https://www.youtube.com/playlist?list={playlist_id}"
        logger.info(f"URL for playlist '{playlist_id}' retrieved successfully.")
        return Right(playlist_url)

    except HttpError as e:
        error_message = f"API error during URL retrieval: {e.content.decode('utf-8')}"
        logger.error(f"Failed to retrieve URL for playlist '{playlist_id}': {error_message}")
        return Left(YouTubeApiError(error_message))
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return Left(YouTubeApiError(f"An unexpected error occurred: {e}"))