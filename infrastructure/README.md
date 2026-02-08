# Infrastructure

This folder contains a Docker Compose setup for hosting the API and web UI.

## Server setup

1. Clone the repo and enter it:

   git clone <repo-url>
   cd ops-assistant

2. Copy and edit env files:

   cp example.env .env
   cp packages/web/example.env packages/web/.env.local

3. Update .env with at least:

   DB_PATH=data/mock.db
   OPENAI_API_KEY=...
   API_KEYS=...

4. Update packages/web/.env.local with:

   NEXT_PUBLIC_API_URL=http://<server-host>:3000
   NEXT_PUBLIC_API_KEY=...

5. (Optional) Put your SQLite DB at data/mock.db or change DB_PATH.

6. Start services:

   docker compose -f infrastructure/docker-compose.yml up --build -d

## Notes

- The API runs on port 3000 and the web UI runs on port 8000.
- The database file is mounted from the repo's data folder.
