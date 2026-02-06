import os

from dotenv import load_dotenv # type: ignore

from database.DatabaseProvider import DatabaseProvider
from database.QueryExecutor import QueryExecutor


def main():
    load_dotenv()

    db_path = os.environ["DB_PATH"]
    db_provider = DatabaseProvider(db_path)
    connection = db_provider.get_connection()

    executor = QueryExecutor(connection)
    results = executor.execute_safe_query("SELECT * FROM zones")
    print(results)


if __name__ == "__main__":
    main()
