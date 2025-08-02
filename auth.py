
import os
import logging
from pymonad.either import Left, Right
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

import logger_config
from domain.errors import AuthenticationError

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']

def get_credentials(
    token_file: str = 'token.json',
    client_secrets_file: str = 'client_secret.json'
):
    creds = None

    if os.path.exists(token_file):
        logger.info(f"Fichier token '{token_file}' trouvé.")
        try:
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)
        except Exception as e:
            logger.error(f"Erreur lors de la lecture du fichier token : {e}")
            return Left(AuthenticationError(f"Fichier token corrompu ou invalide : {e}"))

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Token expiré, tentative de rafraîchissement...")
            try:
                creds.refresh(Request())
                logger.info("Token rafraîchi avec succès.")
            except Exception as e:
                logger.error(f"Échec du rafraîchissement du token : {e}. Lancement du flux complet.")
                creds = None
        
        if not creds:
            logger.info("Aucun token valide trouvé, lancement du nouveau flux d'authentification.")
            if not os.path.exists(client_secrets_file):
                logger.error(f"Fichier secrets '{client_secrets_file}' introuvable.")
                return Left(
                    AuthenticationError(
                        f"Fichier '{client_secrets_file}' introuvable. "
                        "Veuillez le télécharger depuis la Google Cloud Console."
                    )
                )
            
            try:
                flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)
                creds = flow.run_local_server(port=0)
                logger.info("Authentification réussie via le flux local.")
            except Exception as e:
                logger.error(f"Échec du flux d'authentification : {e}")
                return Left(AuthenticationError(f"Échec du flux d'authentification : {e}"))

        try:
            with open(token_file, 'w') as token:
                token.write(creds.to_json())
            logger.info(f"Token sauvegardé dans '{token_file}'.")
        except Exception as e:
            logger.error(f"Impossible de sauvegarder le token : {e}")
            return Left(AuthenticationError(f"Impossible de sauvegarder le token : {e}"))

    logger.info("Credentials valides obtenus.")
    return Right(creds)
