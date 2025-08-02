# i18n.py
import locale

MESSAGES = {
    "en": {
        "playlist_created": "Playlist '{playlist_name}' created successfully. URL: {playlist_url}",
        "playlist_creation_error": "Could not create playlist '{playlist_name}'. Error: {error}",
        "playlist_deleted": "Playlist '{playlist_name}' deleted successfully.",
        "playlist_deletion_error": "Could not delete playlist '{playlist_name}'. Error: {error}",
        "playlist_shared": "Share URL for playlist '{playlist_name}': {playlist_url}",
        "playlist_sharing_error": "Could not get share URL for playlist '{playlist_name}'. Error: {error}",
        "playlist_downloaded": "Playlist '{playlist_url}' downloaded successfully to '{playlist_title}'.",
        "playlist_download_error": "Could not download playlist '{playlist_url}'. Error: {error}",
        "playlist_updated": "Playlist '{playlist_url}' updated successfully in '{playlist_title}'.",
        "playlist_update_error": "Could not update playlist '{playlist_url}'. Error: {error}",
        "import_started": "Importing music from '{yaml_file}'...",
        "import_completed": "Music import from '{yaml_file}' completed successfully.",
        "import_error": "An error occurred during import from '{yaml_file}': {error}",
        "auth_error": "Authentication failed: {error}",
        "auth_success": "Authentication successful.",
        "file_exists_skipping": "File '{file_path}' already exists, skipping download.",
        "help_create_name": "Name of the playlist to create.",
        "help_create_description": "Description of the playlist.",
        "help_create_public": "Make the playlist public.",
        "help_download_url": "URL of the playlist to download.",
        "help_delete_name": "Name of the playlist to delete.",
        "help_share_name": "Name of the playlist to share.",
        "help_import_file": "YAML file containing the music to import.",
        "help_import_quality": "Audio quality for the download (0=best, 9=worst).",
        "help_import_output": "Output directory for downloads.",
        "help_import_flat": "Do not create subdirectories per artist.",
        "help_green": "Enable green mode (skip existing files).",
        "help_lang": "Set the language for output messages (e.g., 'en' or 'fr').",
        "import_source_missing": "You must provide a YAML file or at least one URL via --tune or --playlist.",
        "auth_attempt": "Attempting to authenticate with Google...",
        "creating_playlist": "Creating playlist '{name}'...",
        "deleting_playlist": "Deleting playlist '{name}'...",
        "getting_url": "Getting URL for playlist '{name}'...",
        "preparing_download": "Preparing to download playlist...",
        "preparing_sync": "Preparing to synchronize playlist...",
        "remote_playlist_info": "Remote playlist '{title}' contains {count} tracks.",
        "local_folder_info": "Local directory contains {count} tracks.",
        "files_to_download": "{count} new tracks to download.",
        "files_to_delete": "{count} local tracks to delete.",
        "starting_download": "Starting download...",
        "starting_deletion": "Starting deletion...",
        "file_deleted": "Deleted: {name}",
        "file_deletion_error": "Failed to delete {name}: {error}",
        "sync_completed": "Synchronization complete"
    },
    "fr": {
        "playlist_created": "Playlist '{playlist_name}' créée avec succès. URL : {playlist_url}",
        "playlist_creation_error": "Impossible de créer la playlist '{playlist_name}'. Erreur : {error}",
        "playlist_deleted": "Playlist '{playlist_name}' supprimée avec succès.",
        "playlist_deletion_error": "Impossible de supprimer la playlist '{playlist_name}'. Erreur : {error}",
        "playlist_shared": "URL de partage pour la playlist '{playlist_name}' : {playlist_url}",
        "playlist_sharing_error": "Impossible d'obtenir l'URL de partage pour la playlist '{playlist_name}'. Erreur : {error}",
        "playlist_downloaded": "Playlist '{playlist_url}' téléchargée avec succès dans '{playlist_title}'.",
        "playlist_download_error": "Impossible de télécharger la playlist '{playlist_url}'. Erreur : {error}",
        "playlist_updated": "Playlist '{playlist_url}' mise à jour avec succès dans '{playlist_title}'.",
        "playlist_update_error": "Impossible de mettre à jour la playlist '{playlist_url}'. Erreur : {error}",
        "import_started": "Importation de la musique depuis '{yaml_file}'...",
        "import_completed": "Importation de la musique depuis '{yaml_file}' terminée avec succès.",
        "import_error": "Une erreur est survenue lors de l'importation depuis '{yaml_file}' : {error}",
        "auth_error": "Échec de l'authentification : {error}",
        "auth_success": "Authentification réussie.",
        "file_exists_skipping": "Le fichier '{file_path}' existe déjà, téléchargement ignoré.",
        "help_create_name": "Nom de la playlist à créer.",
        "help_create_description": "Description de la playlist.",
        "help_create_public": "Rendre la playlist publique.",
        "help_download_url": "URL de la playlist à télécharger.",
        "help_delete_name": "Nom de la playlist à supprimer.",
        "help_share_name": "Nom de la playlist à partager.",
        "help_import_file": "Fichier YAML contenant la musique à importer.",
        "help_import_quality": "Qualité audio pour le téléchargement (0=meilleure, 9=pire).",
        "help_import_output": "Dossier de sortie pour les téléchargements.",
        "help_import_flat": "Ne pas créer de sous-dossiers par artiste.",
        "help_green": "Activer le mode écologique (ignore les fichiers existants).",
        "help_lang": "Définit la langue des messages de sortie (ex: 'en' ou 'fr').",
        "import_source_missing": "Vous devez fournir un fichier YAML ou au moins une URL via --tune ou --playlist.",
        "auth_attempt": "Tentative d'authentification auprès de Google...",
        "creating_playlist": "Création de la playlist '{name}' en cours...",
        "deleting_playlist": "Suppression de la playlist '{name}' en cours...",
        "getting_url": "Récupération de l'URL pour la playlist '{name}'...",
        "preparing_download": "Préparation du téléchargement de la playlist...",
        "preparing_sync": "Préparation de la synchronisation de la playlist...",
        "remote_playlist_info": "La playlist distante '{title}' contient {count} morceaux.",
        "local_folder_info": "Le dossier local contient {count} morceaux.",
        "files_to_download": "{count} nouveaux morceaux à télécharger.",
        "files_to_delete": "{count} morceaux locaux à supprimer.",
        "starting_download": "Démarrage du téléchargement...",
        "starting_deletion": "Démarrage de la suppression...",
        "file_deleted": "Supprimé : {name}",
        "file_deletion_error": "Échec de la suppression de {name} : {error}",
        "sync_completed": "Synchronisation terminée"
    }
}

_current_lang = "en"

def get_default_lang():
    try:
        lang_code, _ = locale.getdefaultlocale()
        return "fr" if lang_code and lang_code.startswith("fr") else "en"
    except (ValueError, TypeError):
        return "en"

def set_lang(lang: str):
    global _current_lang
    _current_lang = lang if lang in MESSAGES else "en"

def get_message(key, **kwargs):
    lang = _current_lang
    if lang not in MESSAGES or key not in MESSAGES[lang]:
        # Fallback to English if key not found in current language
        lang = "en"
    
    message_template = MESSAGES[lang].get(key, f"Translation missing for key: {key}")
    
    try:
        return message_template.format(**kwargs)
    except KeyError as e:
        # This can happen if a placeholder is missing in kwargs
        return f"Formatting error for key '{key}': missing placeholder {e}"

# Initialize with default system language
set_lang(get_default_lang())
