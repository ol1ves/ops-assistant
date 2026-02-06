import os

from dotenv import load_dotenv

from database.DatabaseProvider import DatabaseProvider


def main():
    load_dotenv()

    db_path = os.environ["DB_PATH"]
    db_provider = DatabaseProvider(db_path)
    connection = db_provider.get_connection()
    print(connection.cursor().execute("SELECT * FROM zones").fetchall())


if __name__ == "__main__":
    main()
