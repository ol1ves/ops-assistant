"""SQLite database connection provider.

Opens a **read-only** connection to a SQLite database file, ensuring the
application can never accidentally modify production data.
"""

import sqlite3
from pathlib import Path


class DatabaseProvider:
    """Manage a single read-only SQLite connection.

    The connection is opened in URI mode with ``?mode=ro`` so all write
    operations are rejected at the driver level.
    """

    def __init__(self, db_path: str) -> None:
        """Open a read-only connection to the given database file.

        Args:
            db_path: Filesystem path to the SQLite database.

        Raises:
            FileNotFoundError: If the path cannot be resolved.
            ConnectionError: If SQLite cannot open the file.
        """
        try:
            resolved = Path(db_path).resolve(strict=True)
        except OSError as e:
            raise FileNotFoundError(
                f"Could not resolve database path '{db_path}': {e}"
            ) from e

        try:
            # Initialize a read-only connection to the database
            self._connection = sqlite3.connect(f"file:{resolved}?mode=ro", uri=True)
        except sqlite3.Error as e:
            raise ConnectionError(
                f"Failed to connect to database at '{resolved}': {e}"
            ) from e

    def get_connection(self) -> sqlite3.Connection:
        """Return the underlying read-only SQLite connection."""
        return self._connection
