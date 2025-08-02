
import pytest
from unittest.mock import MagicMock, patch
from auth import get_credentials
from domain.errors import AuthenticationError

# Scénario 1: Le fichier client_secret est manquant
def test_get_credentials_no_secret_file(mocker, caplog):
    """
    Vérifie que la fonction retourne une erreur si client_secret.json est introuvable.
    LDD: Vérifie que le log d'erreur est bien émis.
    """
    # Le premier appel (token) retourne False, le second (secret) aussi.
    mocker.patch('os.path.exists', side_effect=[False, False])
    
    result = get_credentials(client_secrets_file='fake_secrets.json')
    
    assert result.is_left()
    # We extract the value from the monad for the check
    error_value, _ = result.monoid
    assert isinstance(error_value, AuthenticationError)
    assert "introuvable" in error_value.message
    # Vérification du log
    assert "Fichier secrets 'fake_secrets.json' introuvable." in caplog.text

# Scénario 2: Authentification complète réussie (pas de token existant)
def test_get_credentials_full_flow_success(mocker, caplog):
    """
    Simule le flux d'authentification complet et vérifie le succès.
    LDD: Vérifie les logs d'info pour le flux et la sauvegarde.
    """
    # Mocker les dépendances externes
    mocker.patch('os.path.exists', side_effect=[False, True]) # token n'existe pas, secret existe
    mock_creds = MagicMock()
    mock_creds.to_json.return_value = '{"token": "mock"}'
    
    mock_flow = MagicMock()
    mock_flow.run_local_server.return_value = mock_creds
    mocker.patch('google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file', return_value=mock_flow)
    
    # Mocker l'écriture du fichier
    mocker.patch('builtins.open', mocker.mock_open())

    result = get_credentials()

    assert result.is_right()
    assert result.value == mock_creds
    # Vérification des logs
    assert "Aucun token valide trouvé" in caplog.text
    assert "Authentification réussie via le flux local" in caplog.text
    assert "Token sauvegardé dans 'token.json'" in caplog.text

# Scénario 3: Token existant et valide
def test_get_credentials_valid_token_exists(mocker, caplog):
    """
    Vérifie que les credentials sont chargés depuis un token existant et valide.
    LDD: Vérifie le log de succès.
    """
    mocker.patch('os.path.exists', return_value=True)
    mock_creds = MagicMock()
    mock_creds.valid = True
    mocker.patch('google.oauth2.credentials.Credentials.from_authorized_user_file', return_value=mock_creds)

    result = get_credentials()

    assert result.is_right()
    assert result.value == mock_creds
    assert "Credentials valides obtenus" in caplog.text
    assert "Fichier token 'token.json' trouvé" in caplog.text

# Scénario 4: Token expiré mais rafraîchissement réussi
def test_get_credentials_expired_token_refresh_success(mocker, caplog):
    """
    Vérifie que le token est rafraîchi avec succès.
    LDD: Vérifie les logs de rafraîchissement.
    """
    mocker.patch('os.path.exists', return_value=True)
    mock_creds = MagicMock()
    mock_creds.valid = False
    mock_creds.expired = True
    mock_creds.refresh_token = "fake_refresh_token"
    
    # La méthode refresh ne retourne rien, elle modifie l'objet en place
    mock_creds.refresh.return_value = None
    mocker.patch('google.oauth2.credentials.Credentials.from_authorized_user_file', return_value=mock_creds)
    mocker.patch('builtins.open', mocker.mock_open())

    result = get_credentials()

    assert result.is_right()
    mock_creds.refresh.assert_called_once()
    assert "Token expiré, tentative de rafraîchissement..." in caplog.text
    assert "Token rafraîchi avec succès." in caplog.text
    assert "Token sauvegardé" in caplog.text
