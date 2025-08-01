import yaml
import os
from rich.console import Console

from playlist_downloader.adapters.ytdlp_adapter import YTDLPAdapter
from playlist_downloader.domain.models import Playlist

console = Console()

def download_from_yaml(file_path: str, output_dir: str):
    """
    Charge les morceaux depuis un fichier YAML et les télécharge.
    """
    try:
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        console.print(f"[bold red]Erreur : Le fichier '{file_path}' est introuvable.[/bold red]")
        return
    except yaml.YAMLError as e:
        console.print(f"[bold red]Erreur lors de la lecture du fichier YAML : {e}[/bold red]")
        return

    downloader = YTDLPAdapter()
    
    for artist in data.get('artistes', []):
        artist_name = artist.get('name')
        tunes = artist.get('tunes')

        if not artist_name or not tunes:
            console.print(f"[yellow]Artiste '{artist_name or 'Inconnu'}' ignoré (pas de morceaux).[/yellow]")
            continue

        artist_dir = os.path.join(output_dir, artist_name)
        os.makedirs(artist_dir, exist_ok=True)
        
        console.print(f"\n[bold cyan]Téléchargement pour l'artiste : {artist_name}[/bold cyan]")
        
        for i, tune_url in enumerate(tunes):
            console.print(f"  ({i+1}/{len(tunes)}) Téléchargement de : {tune_url}")
            # Nous créons un objet Playlist factice car l'adaptateur l'exige.
            playlist = Playlist(playlist_id=f"tune_{i}", title=f"Tune {i}", url=tune_url)
            
            result = downloader.download_playlist(playlist, artist_dir)
            
            if result.is_right():
                console.print(f"  [green]✓ {result.value}[/green]")
            else:
                # La valeur d'erreur est dans result.monoid[0]
                error_obj, _ = result.monoid
                console.print(f"  [bold red]✗ Erreur : {error_obj.message}[/bold red]")

if __name__ == "__main__":
    download_from_yaml('musics.yml', 'downloads')
