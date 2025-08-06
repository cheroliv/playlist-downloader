from unittest.mock import MagicMock
from auth import get_credentials
from domain.errors import AuthenticationError


# Scenario 1: client_secret.json file is missing
def test_get_credentials_no_secret_file(mocker, caplog):
    """
    Checks that the function returns an error if client_secret.json is not found.
    LDD: Verifies that the error log is emitted correctly.
    """
    # The first call (token) returns False, the second (secret) also returns False.
    mocker.patch("os.path.exists", side_effect=[False, False])

    result = get_credentials(client_secrets_file="fake_secrets.json")

    assert result.is_left()
    # We extract the value from the monad for the check
    error_value, _ = result.monoid
    assert isinstance(error_value, AuthenticationError)
    assert "not found" in error_value.message
    # Log verification
    assert "Secrets file 'fake_secrets.json' not found." in caplog.text


# Scenario 2: Full authentication successful (no existing token)
def test_get_credentials_full_flow_success(mocker, caplog):
    """
    Simulates the complete authentication flow and verifies success.
    LDD: Verifies the info logs for the flow and saving process.
    """
    # Mock external dependencies
    mocker.patch(
        "os.path.exists", side_effect=[False, True]
    )  # token does not exist, secret exists
    mock_creds = MagicMock()
    mock_creds.to_json.return_value = '{"token": "mock"}'

    mock_flow = MagicMock()
    mock_flow.run_local_server.return_value = mock_creds
    mocker.patch(
        "google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file",
        return_value=mock_flow,
    )

    # Mock file writing
    mocker.patch("builtins.open", mocker.mock_open())

    result = get_credentials()

    assert result.is_right()
    assert result.value == mock_creds
    # Log verification
    assert "No valid token found" in caplog.text
    assert "Authentication successful via local flow" in caplog.text
    assert "Token saved to 'token.json'" in caplog.text


# Scenario 3: Existing and valid token
def test_get_credentials_valid_token_exists(mocker, caplog):
    """
    Checks that credentials are loaded from an existing and valid token.
    LDD: Verifies the success log.
    """
    mocker.patch("os.path.exists", return_value=True)
    mock_creds = MagicMock()
    mock_creds.valid = True
    mocker.patch(
        "google.oauth2.credentials.Credentials.from_authorized_user_file",
        return_value=mock_creds,
    )

    result = get_credentials()

    assert result.is_right()
    assert result.value == mock_creds
    assert "Valid credentials obtained" in caplog.text
    assert "Token file 'token.json' found" in caplog.text


# Scenario 4: Expired token but successful refresh
def test_get_credentials_expired_token_refresh_success(mocker, caplog):
    """
    Checks that the token is refreshed successfully.
    LDD: Verifies the refresh logs.
    """
    mocker.patch("os.path.exists", return_value=True)
    mock_creds = MagicMock()
    mock_creds.valid = False
    mock_creds.expired = True
    mock_creds.refresh_token = "fake_refresh_token"

    # The refresh method returns nothing, it modifies the object in place
    mock_creds.refresh.return_value = None
    mocker.patch(
        "google.oauth2.credentials.Credentials.from_authorized_user_file",
        return_value=mock_creds,
    )
    mocker.patch("builtins.open", mocker.mock_open())

    result = get_credentials()

    assert result.is_right()
    mock_creds.refresh.assert_called_once()
    assert "Token expired, attempting refresh..." in caplog.text
    assert "Token refreshed successfully." in caplog.text
    assert "Token saved" in caplog.text
