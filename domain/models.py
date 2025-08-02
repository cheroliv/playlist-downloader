from dataclasses import dataclass


@dataclass(frozen=True)
class Playlist:
    """Represents a YouTube playlist."""
    playlist_id: str
    title: str
    url: str


@dataclass(frozen=True)
class DownloadTask:
    """DTO representing a playlist download task."""
    playlist_url: str
    output_path: str