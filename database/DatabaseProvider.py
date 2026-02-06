import sqlite3
from pathlib import Path


class DatabaseProvider:
    def __init__(self, db_path: str) -> None:
        try:
            resolved = Path(db_path).resolve(strict=True)
        except OSError as e:
            raise FileNotFoundError(
                f"Could not resolve database path '{db_path}': {e}"
            ) from e

        try:
            self.connection = sqlite3.connect(str(resolved))
        except sqlite3.Error as e:
            raise ConnectionError(
                f"Failed to connect to database at '{resolved}': {e}"
            ) from e

    def get_connection(self) -> sqlite3.Connection:
        return self.connection
