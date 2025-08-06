import os
import logging
from pymonad.either import Left, Right
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from domain.errors import AuthenticationError

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]


def get_credentials(
    token_file: str = "token.json", client_secrets_file: str = "client_secret.json"
):
    creds = None

    if os.path.exists(token_file):
        logger.info(f"Token file '{token_file}' found.")
        try:
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)
        except Exception as e:
            logger.error(f"Error reading token file: {e}")
            return Left(AuthenticationError(f"Corrupt or invalid token file: {e}"))

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Token expired, attempting refresh...")
            try:
                creds.refresh(Request())
                logger.info("Token refreshed successfully.")
            except Exception as e:
                logger.error(f"Token refresh failed: {e}. Starting full flow.")
                creds = None

        if not creds:
            logger.info("No valid token found, starting new authentication flow.")
            if not os.path.exists(client_secrets_file):
                logger.error(f"Secrets file '{client_secrets_file}' not found.")
                return Left(
                    AuthenticationError(
                        f"File '{client_secrets_file}' not found. "
                        "Please download it from the Google Cloud Console."
                    )
                )

            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    client_secrets_file, SCOPES
                )
                creds = flow.run_local_server(port=0)
                logger.info("Authentication successful via local flow.")
            except Exception as e:
                logger.error(f"Authentication flow failed: {e}")
                return Left(AuthenticationError(f"Authentication flow failed: {e}"))

        try:
            with open(token_file, "w") as token:
                token.write(creds.to_json())
            logger.info(f"Token saved to '{token_file}'.")
        except Exception as e:
            logger.error(f"Could not save token: {e}")
            return Left(AuthenticationError(f"Could not save token: {e}"))

    logger.info("Valid credentials obtained.")
    return Right(creds)
