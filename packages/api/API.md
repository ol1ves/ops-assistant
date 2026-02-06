# Ops Assistant API

REST API for the Ops Assistant chatbot. Provides conversation management and chat functionality backed by OpenAI with SQL function-calling over a read-only SQLite database.

## Getting Started

### Environment Variables

Copy `example.env` to `.env` at the project root and fill in your values.

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `DB_PATH` | Yes | -- | Path to the SQLite database file |
| `OPENAI_API_KEY` | Yes | -- | OpenAI API key |
| `API_KEYS` | Yes | -- | Comma-separated list of valid API keys |
| `RATE_LIMIT_PER_HOUR` | No | `20` | Max chat requests per API key per hour |
| `API_HOST` | No | `0.0.0.0` | Host to bind the server to |
| `API_PORT` | No | `3000` | Port to bind the server to |

### Running the Server

```bash
uv run ops-api
```

Or directly with uvicorn:

```bash
uv run uvicorn api.main:app --host 0.0.0.0 --port 3000
```

Interactive docs are available at `http://localhost:3000/docs` when the server is running.

---

## Authentication

All endpoints except `/health` require an API key passed in the `Authorization` header.

```
Authorization: Bearer <your-api-key>
```

The key must match one of the comma-separated values in the `API_KEYS` environment variable.

**Error Responses:**

| Status | Condition |
| --- | --- |
| `401 Unauthorized` | Missing or invalid API key |
| `500 Internal Server Error` | No API keys configured on the server |

---

## Rate Limiting

The chat endpoint (`POST /conversations/{id}/chat`) is rate-limited per API key using a sliding one-hour window. The default limit is 20 requests per hour, configurable via `RATE_LIMIT_PER_HOUR`.

Rate limit info is returned in both response headers and the response body.

**Response Headers** (on chat responses and 429 errors):

| Header | Description |
| --- | --- |
| `X-RateLimit-Limit` | Max requests allowed per hour |
| `X-RateLimit-Remaining` | Requests remaining in the current window |
| `X-RateLimit-Reset` | ISO-8601 timestamp when the oldest request expires |

When the limit is exceeded, the server responds with `429 Too Many Requests`.

---

## Endpoints

### Health Check

#### `GET /health`

Basic liveness probe. No authentication required.

**Response** `200 OK`

```json
{
  "status": "ok"
}
```

---

### Create Conversation

#### `POST /conversations`

Create a new conversation. Must be called before sending chat messages.

**Response** `201 Created`

```json
{
  "id": "a1b2c3d4e5f6...",
  "created_at": "2026-02-06T12:00:00.000000",
  "last_message": "2026-02-06T12:00:00.000000"
}
```

---

### List Conversations

#### `GET /conversations`

Return all active conversations.

**Response** `200 OK`

```json
[
  {
    "id": "a1b2c3d4e5f6...",
    "created_at": "2026-02-06T12:00:00.000000",
    "last_message": "2026-02-06T12:05:00.000000"
  }
]
```

---

### Get Conversation

#### `GET /conversations/{conversation_id}`

Return a single conversation with its full message history. System messages are excluded.

**Path Parameters**

| Parameter | Type | Description |
| --- | --- | --- |
| `conversation_id` | string | The conversation ID |

**Response** `200 OK`

```json
{
  "id": "a1b2c3d4e5f6...",
  "created_at": "2026-02-06T12:00:00.000000",
  "last_message": "2026-02-06T12:05:00.000000",
  "messages": [
    {
      "role": "user",
      "content": "How many zones are there?",
      "timestamp": "2026-02-06T12:01:00.000000"
    },
    {
      "role": "assistant",
      "content": "There are 12 zones in the database.",
      "timestamp": "2026-02-06T12:01:02.000000"
    }
  ]
}
```

**Error Responses**

| Status | Condition |
| --- | --- |
| `404 Not Found` | Conversation does not exist |

---

### Delete Conversation

#### `DELETE /conversations/{conversation_id}`

Delete a conversation and all of its messages.

**Path Parameters**

| Parameter | Type | Description |
| --- | --- | --- |
| `conversation_id` | string | The conversation ID |

**Response** `204 No Content`

**Error Responses**

| Status | Condition |
| --- | --- |
| `404 Not Found` | Conversation does not exist |

---

### Chat

#### `POST /conversations/{conversation_id}/chat`

Send a user message and receive the assistant's reply. This endpoint is **rate-limited**.

**Path Parameters**

| Parameter | Type | Description |
| --- | --- | --- |
| `conversation_id` | string | The conversation ID |

**Request Body** `application/json`

```json
{
  "message": "How many entities were in Zone A last hour?"
}
```

**Response** `200 OK`

```json
{
  "conversation_id": "a1b2c3d4e5f6...",
  "response": "Based on the query results, there were 4 entities in Zone A during the last hour.",
  "remaining_requests": 18
}
```

**Error Responses**

| Status | Condition |
| --- | --- |
| `404 Not Found` | Conversation does not exist |
| `429 Too Many Requests` | Rate limit exceeded |

---

### Rate Limit Status

#### `GET /rate-limit`

Check the current rate-limit status for your API key without consuming a request.

**Response** `200 OK`

```json
{
  "limit": 20,
  "remaining": 18,
  "reset": "2026-02-06T13:01:00.000000+00:00"
}
```

---

## Typical Frontend Flow

```
1.  POST   /conversations                → Create a conversation, store the id
2.  POST   /conversations/{id}/chat      → Send messages, display responses
3.  GET    /conversations/{id}           → Reload message history if needed
4.  GET    /rate-limit                   → Show remaining requests in the UI
5.  DELETE /conversations/{id}           → Clean up when the user is done
```
