"""Safe, read-only SQL query executor with multi-step validation.

All queries pass through a validation pipeline that enforces SELECT-only
execution, blocks dangerous keywords, and rejects SQL injection patterns
before any statement reaches the database.
"""

import re
import sqlite3


class QueryExecutor:
    """Executes validated read-only SQL queries against an SQLite connection.

    Provides an application-level security layer that ensures only SELECT
    statements are executed, with input sanitization against SQL injection.
    """

    # Write/DDL keywords that must never appear in a query.
    # Matched with word boundaries to avoid false positives on column names.
    _BLOCKED_KEYWORDS = [
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "ALTER",
        "CREATE",
        "ATTACH",
        "DETACH",
        "PRAGMA",
        "GRANT",
        "REVOKE",
    ]

    _BLOCKED_PATTERN = re.compile(
        r"\b(" + "|".join(_BLOCKED_KEYWORDS) + r")\b",
        re.IGNORECASE,
    )

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def execute_safe_query(self, query: str) -> list[tuple]:
        """Validate and execute a read-only SQL query.

        Args:
            query: A SQL SELECT statement to execute.

        Returns:
            A list of result tuples from the query.

        Raises:
            ValueError: If the query fails validation.
            RuntimeError: If query execution fails.
        """
        # Normalize: allow single trailing semicolon (LLM often outputs it)
        normalized = query.strip()
        if normalized.endswith(";"):
            normalized = normalized[:-1].rstrip()
        self._validate_query(normalized)
        return self._execute_query(normalized)

    def _validate_query(self, query: str) -> None:
        """Sanitize and validate a SQL query string.

        Ensures the query is a read-only SELECT statement and does not
        contain patterns commonly used in SQL injection attacks.

        Raises:
            ValueError: If any validation check fails.
        """
        # 1. Non-empty check
        if not query or not query.strip():
            raise ValueError("Query must not be empty or whitespace-only.")

        stripped = query.strip()

        # 2. SELECT-only check
        if not stripped.upper().startswith("SELECT"):
            raise ValueError(
                "Only SELECT queries are allowed. "
                f"Received query starting with: '{stripped.split()[0]}'"
            )

        # 3. No statement stacking (semicolons)
        if ";" in stripped:
            raise ValueError(
                "Query must not contain semicolons. "
                "Multiple statements are not allowed."
            )

        # 4. Block write/DDL keywords
        match = self._BLOCKED_PATTERN.search(stripped)
        if match:
            raise ValueError(
                f"Query contains a blocked keyword: '{match.group()}'. "
                "Only read-only SELECT queries are permitted."
            )

        # 5. Block inline comments
        if "--" in stripped or "/*" in stripped:
            raise ValueError(
                "Query must not contain SQL comments (-- or /*). "
                "These are not allowed for security reasons."
            )

    def _execute_query(self, safe_query: str) -> list[tuple]:
        """Execute a pre-validated query and return all results.

        Args:
            safe_query: A query that has already passed validation.

        Returns:
            A list of result tuples.

        Raises:
            RuntimeError: If the database returns an error during execution.
        """
        cursor = self._connection.cursor()
        try:
            cursor.execute(safe_query)
            return cursor.fetchall()
        except sqlite3.Error as e:
            try:
                cursor.close()
            except Exception:
                pass
            raise RuntimeError(
                f"Query execution failed: {e}"
            ) from e
