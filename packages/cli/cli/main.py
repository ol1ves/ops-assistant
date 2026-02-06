import os

from dotenv import load_dotenv  # type: ignore

from chatbot.ChatBot import ChatBot
from database.DatabaseProvider import DatabaseProvider
from database.QueryExecutor import QueryExecutor


def main():
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
