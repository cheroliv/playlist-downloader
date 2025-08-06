import logging
import sys


def setup_logger():
    """Configure le logger racine pour l'application."""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Créer un handler pour la sortie console
    handler = logging.StreamHandler(sys.stdout)

    # Créer un formateur et l'ajouter au handler
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)

    # Ajouter le handler au logger (s'il n'en a pas déjà un)
    if not logger.handlers:
        logger.addHandler(handler)


# Appeler la configuration au moment de l'import
setup_logger()
