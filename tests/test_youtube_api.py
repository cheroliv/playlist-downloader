import pytest
from unittest.mock import MagicMock, patch
from youtube_api import create_playlist, delete_playlist, get_playlist_url
from domain.errors import YouTubeApiError
from googleapiclient.errors import HttpError
from io import BytesIO

# Scénario 1: Création de playlist réussie
def test_create_playlist_success(mocker, caplog):
    """
    Vérifie que la création de playlist appelle l'API avec les bons paramètres
    et retourne un Right(playlist_id) en cas de succès.
    LDD: Vérifie les logs d'info.
    """
    mock_credentials = MagicMock()
    mock_credentials.universe_domain = "googleapis.com"
    
    # Simuler la chaîne d'appels de l'API
    mock_insert = MagicMock()
    api_response = {'id': 'PL123456789', 'snippet': {'title': 'Ma Playlist de Test'}}
    mock_insert.execute.return_value = api_response
    
    mock_playlists = MagicMock()
    mock_playlists.insert.return_value = mock_insert
    
    mock_youtube_service = MagicMock()
    mock_youtube_service.playlists.return_value = mock_playlists
    
    mocker.patch('youtube_api.build', return_value=mock_youtube_service)

    result = create_playlist(mock_credentials, "Titre Test", "Description Test", private=True)

    assert result.is_right()
    assert result.value == "PL123456789"
    
    # Vérifier que l'API a été appelée correctement
    mock_playlists.insert.assert_called_once_with(
        part='snippet,status',
        body={
            'snippet': {
                'title': 'Titre Test',
                'description': 'Description Test'
            },
            'status': {
                'privacyStatus': 'private'
            }
        }
    )
    assert "Playlist 'PL123456789' créée avec succès." in caplog.text

# Scénario 2: Échec de la création de playlist (erreur API)
def test_create_playlist_api_error(mocker, caplog):
    """
    Vérifie que la fonction retourne un Left en cas d'erreur de l'API.
    LDD: Vérifie les logs d'erreur.
    """
    mock_credentials = MagicMock()
    mock_credentials.universe_domain = "googleapis.com"

    # Simuler une réponse d'erreur HTTP réaliste
    mock_http_resp = MagicMock()
    mock_http_resp.status = 403
    mock_http_resp.reason = "Forbidden"
    
    http_error = HttpError(
        resp=mock_http_resp,
        content=b'Permission denied'
    )
    
    mock_youtube_service = MagicMock()
    mock_youtube_service.playlists().insert().execute.side_effect = http_error
    
    mocker.patch('youtube_api.build', return_value=mock_youtube_service)

    result = create_playlist(mock_credentials, "Titre", "Description", private=False)

    assert result.is_left()
    error_value, _ = result.monoid
    assert isinstance(error_value, YouTubeApiError)
    assert "Permission denied" in error_value.message
    assert "Échec de la création de la playlist" in caplog.text
    assert "Permission denied" in caplog.text

# Scénario 3: Suppression de playlist réussie
def test_delete_playlist_success(mocker, caplog):
    """
    Vérifie que la suppression de playlist appelle l'API avec le bon ID
    et retourne un Right avec un message de succès.
    LDD: Vérifie les logs d'info.
    """
    mock_credentials = MagicMock()
    mock_credentials.universe_domain = "googleapis.com"
    playlist_id = "PL123456789"

    mock_delete_execute = MagicMock(return_value=None) # La suppression ne retourne rien
    mock_delete = MagicMock()
    mock_delete.execute = mock_delete_execute

    mock_playlists = MagicMock()
    mock_playlists.delete.return_value = mock_delete

    mock_youtube_service = MagicMock()
    mock_youtube_service.playlists.return_value = mock_playlists

    mocker.patch('youtube_api.build', return_value=mock_youtube_service)

    result = delete_playlist(mock_credentials, playlist_id)

    assert result.is_right()
    assert result.value == f"Playlist '{playlist_id}' supprimée avec succès."
    mock_playlists.delete.assert_called_once_with(id=playlist_id)
    assert f"Playlist '{playlist_id}' supprimée avec succès." in caplog.text

# Scénario 4: Échec de la suppression (playlist non trouvée)
def test_delete_playlist_not_found_error(mocker, caplog):
    """
    Vérifie que la fonction retourne un Left(YouTubeApiError) si la playlist n'existe pas.
    LDD: Vérifie les logs d'erreur.
    """
    mock_credentials = MagicMock()
    mock_credentials.universe_domain = "googleapis.com"
    playlist_id = "PL_NON_EXISTENT"

    mock_http_resp = MagicMock()
    mock_http_resp.status = 404
    mock_http_resp.reason = "Not Found"
    
    http_error = HttpError(
        resp=mock_http_resp,
        content=b'Playlist not found.'
    )
    
    mock_youtube_service = MagicMock()
    mock_youtube_service.playlists().delete().execute.side_effect = http_error
    
    mocker.patch('youtube_api.build', return_value=mock_youtube_service)

    result = delete_playlist(mock_credentials, playlist_id)

    assert result.is_left()
    error_value, _ = result.monoid
    assert isinstance(error_value, YouTubeApiError)
    assert "Playlist not found" in error_value.message
    assert f"Échec de la suppression de la playlist '{playlist_id}'" in caplog.text

# Scénario 6: Obtenir l'URL de partage avec succès
def test_get_playlist_url_success(mocker, caplog):
    """
    Vérifie que la fonction retourne un Right avec l'URL de la playlist.
    LDD: Vérifie les logs d'info.
    """
    mock_credentials = MagicMock()
    mock_credentials.universe_domain = "googleapis.com"
    playlist_id = "PL123456789"
    expected_url = f"https://www.youtube.com/playlist?list={playlist_id}"

    # Simuler la réponse de l'API (même si nous ne l'utilisons pas directement)
    mock_list_execute = MagicMock(return_value={'items': [{'id': playlist_id}]})
    mock_list = MagicMock()
    mock_list.execute = mock_list_execute

    mock_playlists = MagicMock()
    mock_playlists.list.return_value = mock_list

    mock_youtube_service = MagicMock()
    mock_youtube_service.playlists.return_value = mock_playlists

    mocker.patch('youtube_api.build', return_value=mock_youtube_service)
    
    # Importer la fonction ici pour éviter les problèmes de circular dependency
    from youtube_api import get_playlist_url

    result = get_playlist_url(mock_credentials, playlist_id)

    assert result.is_right()
    assert result.value == expected_url
    assert f"URL de la playlist '{playlist_id}' récupérée avec succès." in caplog.text
    mock_playlists.list.assert_called_once_with(part='id', id=playlist_id)

# Scénario 7: Échec de l'obtention de l'URL (playlist non trouvée)
def test_get_playlist_url_not_found(mocker, caplog):
    """
    Vérifie que la fonction retourne un Left si la playlist n'existe pas.
    LDD: Vérifie les logs d'erreur.
    """
    mock_credentials = MagicMock()
    mock_credentials.universe_domain = "googleapis.com"
    playlist_id = "PL_NON_EXISTENT"

    # Simuler une réponse vide de l'API
    mock_list_execute = MagicMock(return_value={'items': []})
    mock_list = MagicMock()
    mock_list.execute = mock_list_execute

    mock_playlists = MagicMock()
    mock_playlists.list.return_value = mock_list

    mock_youtube_service = MagicMock()
    mock_youtube_service.playlists.return_value = mock_playlists

    mocker.patch('youtube_api.build', return_value=mock_youtube_service)

    result = get_playlist_url(mock_credentials, playlist_id)

    assert result.is_left()
    error_value, _ = result.monoid
    assert isinstance(error_value, YouTubeApiError)
    assert "introuvable" in error_value.message
    assert f"Échec de la récupération de l'URL" in caplog.text