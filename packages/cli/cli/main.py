"""Interactive command-line interface for the Ops Assistant chatbot."""

import os

from dotenv import load_dotenv  # type: ignore

from chatbot.ChatBot import ChatBot # type: ignore
from database.DatabaseProvider import DatabaseProvider # type: ignore
from database.QueryExecutor import QueryExecutor # type: ignore


def main():
    """Run the interactive chatbot REPL.

    Loads environment configuration, initializes the database and chatbot,
    then enters a read-eval-print loop where the user can ask questions
    about the location-tracking database.
    """
    load_dotenv()

    db_path = os.environ["DB_PATH"]
    api_key = os.environ["OPENAI_API_KEY"]

    db_provider = DatabaseProvider(db_path)
    connection = db_provider.get_connection()
    executor = QueryExecutor(connection)

    bot = ChatBot(executor, api_key)

    print("Ops Assistant (type 'quit' or 'exit' to stop)")
    print("-" * 48)

    conversation_id = None

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit"):
            print("Goodbye!")
            break

        print("\nThinking...")
        conversation_id, response = bot.process_message(
            user_input,
            conversation_id=conversation_id,
            on_tool_call=lambda sql: print(f"Executed Query: {sql}"),
        )
        print("\nThinking...")
        print(f"\nAssistant: {response}")


if __name__ == "__main__":
    main()
