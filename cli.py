
import typer
from rich.console import Console

# Initialisation de Typer et de la console Rich pour de belles sorties
app = typer.Typer(
    name="playlist-downloader",
    help="Un outil CLI pour gérer les playlists YouTube.",
    add_completion=False,
)
console = Console()


@app.command(name="creer")
def create_playlist(
    titre: str = typer.Option(..., "--titre", "-t", help="Le titre de la nouvelle playlist."),
    description: str = typer.Option("", "--description", "-d", help="La description de la playlist."),
    public: bool = typer.Option(False, "--public", help="Rendre la playlist publique."),
):
    """
    Crée une nouvelle playlist YouTube.
    """
    console.print(f"🚧 Commande 'creer' en cours de construction...")
    console.print(f"Titre: {titre}")
    console.print(f"Description: {description}")
    console.print(f"Publique: {public}")


@app.command(name="telecharger")
def download_playlist(
    url: str = typer.Argument(..., help="L'URL de la playlist à télécharger."),
    output_dir: str = typer.Option("downloads", "--output", "-o", help="Le dossier de destination."),
):
    """
    Télécharge une playlist YouTube en fichiers MP3.
    """
    console.print(f"🚧 Commande 'telecharger' en cours de construction...")
    console.print(f"URL: {url}")
    console.print(f"Dossier de sortie: {output_dir}")


if __name__ == "__main__":
    app()
