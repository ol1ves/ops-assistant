"""FastAPI application entry point."""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from chatbot.ChatBot import ChatBot
from database.DatabaseProvider import DatabaseProvider
from database.QueryExecutor import QueryExecutor

from api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Set up and tear down application-wide resources."""
    load_dotenv()

    db_path = os.environ["DB_PATH"]
    api_key = os.environ["OPENAI_API_KEY"]

    db_provider = DatabaseProvider(db_path)
    connection = db_provider.get_connection()
    executor = QueryExecutor(connection)

    app.state.bot = ChatBot(executor, api_key)

    yield

    connection.close()


app = FastAPI(
    title="Ops Assistant API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
    ],
)

app.include_router(router)


def serve() -> None:
    """Start the uvicorn server using environment configuration."""
    host = os.environ.get("API_HOST", "0.0.0.0")
    port = int(os.environ.get("API_PORT", "3000"))
    uvicorn.run("api.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    serve()
