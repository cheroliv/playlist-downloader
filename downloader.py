
import yaml
import subprocess
import os
from pathlib import Path

def download_music(yaml_file, output_dir, audio_quality):
    """
    Downloads music from a YAML file.

    Args:
        yaml_file (str): Path to the YAML file.
        output_dir (str): Directory to save the downloaded music.
        audio_quality (int): Audio quality for the download (0 for best).
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    with open(yaml_file, 'r') as f:
        data = yaml.safe_load(f)

    for artiste in data.get('artistes', []):
        artiste_name = artiste.get('name')
        if not artiste_name:
            continue

        artiste_dir = output_path / artiste_name
        artiste_dir.mkdir(parents=True, exist_ok=True)

        for tune in artiste.get('tunes', []):
            print(f"Téléchargement de : {tune} pour l'artiste {artiste_name}")
            command = [
                'yt-dlp',
                '-x',
                '--audio-format', 'mp3',
                '--audio-quality', str(audio_quality),
                '-o', f'{artiste_dir}/%(title)s.%(ext)s',
                tune
            ]
            subprocess.run(command, check=True)

if __name__ == '__main__':
    # To load the YAML file, you need to install PyYAML
    # pip install PyYAML
    download_music('musics.yml', 'downloads/usb_stick', 0)
