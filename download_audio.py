

import yt_dlp
import os

# Créez le dossier de téléchargement s'il n'existe pas
output_folder = 'downloads'
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# --- Votre liste de vidéos YouTube ---
# Remplacez ces URLs par celles que vous souhaitez télécharger
urls_a_telecharger = [
    'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    'https://www.youtube.com/watch?v=3_yD_cEKo9s'
    # Ajoutez autant d'URLs que vous voulez ici
]

# --- Configuration de yt-dlp ---
# Documentation des options : https://github.com/yt-dlp/yt-dlp#embedding-yt-dlp
ydl_opts = {
    # Format : 'bestaudio/best' télécharge le meilleur flux audio.
    # Si aucun flux audio seul n'est disponible, il prend la meilleure vidéo et en extrait l'audio.
    'format': 'bestaudio/best',
    
    # Post-processeurs : opérations à effectuer après le téléchargement.
    'postprocessors': [{
        # Clé pour l'extraction audio avec FFmpeg.
        'key': 'FFmpegExtractAudio',
        # Codec de sortie souhaité.
        'preferredcodec': 'mp3',
        # Qualité audio en kbps.
        'preferredquality': '192',
    }],
    
    # Modèle pour le nom du fichier de sortie.
    # %(title)s sera remplacé par le titre de la vidéo.
    # %(ext)s sera remplacé par l'extension du fichier (mp3 dans notre cas).
    'outtmpl': os.path.join(output_folder, '%(title)s.%(ext)s'),
}

# --- Lancement du téléchargement ---
print(f"Lancement du téléchargement pour {len(urls_a_telecharger)} vidéo(s)...")

# Crée une instance de YoutubeDL avec les options configurées
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    # La méthode download accepte une liste d'URLs
    ydl.download(urls_a_telecharger)

print("\nTerminé ! Tous les fichiers ont été téléchargés dans le dossier 'downloads'.")

