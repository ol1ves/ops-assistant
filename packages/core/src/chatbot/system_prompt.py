"""System prompt for the Ops Assistant chatbot.

Injects the current date and time so the model can resolve relative time
references (e.g. "last hour", "today") when generating SQL queries.
"""

from datetime import datetime


def get_system_prompt() -> str:
    """Return the system prompt with the current timestamp.

    Called on every user message so the model always has an up-to-date
    time reference for generating time-based SQL queries.
    """
    return (
        "You are an operations assistant for an indoor location-tracking system. "
        "Your only purpose is to answer questions about the database. "
        "Answer the user's questions by querying the database when needed. "
        "Always prefer using the execute_sql_query tool to look up real data "
        "rather than guessing. Present results clearly and concisely. "
        f"For queries involving time, use the current date and time {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} as the reference point. "
    )
