"""All prompts for the Ops Assistant chatbot.

Injects the current date and time where needed so the model can resolve
relative time references (e.g. "last hour", "today") when generating SQL.
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


def get_reasoning_prompt() -> str:
    """Return the prompt used for the reasoning/planning phase.

    Instructs the model to reason step-by-step about the user's question
    and to use execute_sql_query when it needs data.
    """
    return (
        "Reason step-by-step about what you need to do to answer the user's question. "
        "If you need data from the database to answer, use the execute_sql_query tool. "
        "Output your reasoning clearly; you may call the tool zero or more times as needed."
    )


def get_interpretation_prompt() -> str:
    """Return the prompt used after tool results for the interpretation phase.

    Instructs the model to interpret the query results and provide a
    clear final answer to the user.
    """
    return (
        "Using the query results above, interpret the data and provide a clear, "
        "concise final answer to the user's question. Do not call any tools."
    )
