import logging
from pathlib import Path
from typing import Optional

from mutagen.id3 import ID3, ID3NoHeaderError

logger = logging.getLogger(__name__)


class MutagenAdapter:
    """
    Adapter for reading and writing MP3 metadata using Mutagen.
    """

    def get_comment(self, file_path: Path) -> Optional[str]:
        """
        Reads the comment tag from an MP3 file.

        Args:
            file_path: The path to the MP3 file.

        Returns:
            The content of the comment tag, or None if not found or on error.
        """
        if not file_path.exists():
            return None

        try:
            audio = ID3(file_path)
            comment_frames = audio.getall("COMM")
            if comment_frames:
                # Return the text of the first comment frame
                return comment_frames[0].text[0]
            return None
        except ID3NoHeaderError:
            logger.warning(
                f"File '{file_path}' does not have an ID3 header. Cannot read comment."
            )
            return None
        except Exception as e:
            logger.error(f"Error reading comment from '{file_path}': {e}")
            return None
