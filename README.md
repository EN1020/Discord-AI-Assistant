# Discord AI Assistant

OpenAI-powered Discord bot with persistent per-user context, local RAG over files in `docs/`, and optional web search for current information.

![Demo](assets/demo.gif)
![Architecture](assets/architecture.png)

## Project Highlights

- Built a Discord AI assistant that supports slash commands, mentions, DMs, local document RAG, and web-grounded answers.
- Implemented scoped conversation memory per `(server, channel, user)` so follow-up questions preserve context without mixing users.
- Added OpenAI Responses API integration with optional web search to reduce stale or unsupported answers.
- Built a lightweight NumPy vector retrieval pipeline for TXT, PDF, JSON, JSONL, and CSV knowledge files.
- Containerized the bot with Docker Compose and deployed it to a Google Cloud Free Tier VM for 24/7 operation.
- Added CI, unit tests, Docker deployment scripts, and cloud deployment documentation.

## Features

- `/ask`: conversational AI with recent context memory.
- `/web`: forces OpenAI web search for fresh facts and source-backed answers.
- `/rag`: answers from your local `docs/` knowledge base.
- `/sources`: shows the most relevant local RAG sources for a query.
- `/summarize`: summarizes your recent conversation with the bot.
- `/forget`: clears your memory for the current channel.
- `/reload_rag`: reloads an already-built RAG index without restarting the bot.
- Mention or DM the bot to ask naturally.

## Project Structure

```text
.
├── bot.py                  # Discord entrypoint
├── rag_index.py            # RAG index build entrypoint
├── rag_module.py           # Backward-compatible RAG import wrapper
├── discord_ai_bot/
│   ├── config.py           # Environment settings
│   ├── indexing.py         # Document loading, chunking, embedding
│   ├── memory.py           # Per-user conversation memory
│   ├── openai_service.py   # OpenAI Responses API and web search
│   ├── rag.py              # Local vector retrieval and grounded answers
│   └── discord_utils.py    # Discord formatting helpers
├── docs/                   # TXT, PDF, JSON, JSONL, CSV knowledge files
├── rag_store/              # Generated vectors and metadata
├── tests/                  # Offline unit tests
├── deploy/                 # Google, Oracle, and cloud deployment scripts
├── portfolio/              # Resume and portfolio-ready project copy
└── assets/                 # Demo media
```

## Setup

1. Create a Discord app and bot in the Discord Developer Portal.
2. Enable `Message Content Intent` for mention/DM support.
3. Invite the bot with `bot` and `applications.commands` scopes.
4. Copy `.env.example` to `.env` and fill in your secrets.

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Environment

```env
DISCORD_TOKEN=YOUR_DISCORD_TOKEN
OPENAI_API_KEY=YOUR_OPENAI_KEY

OPENAI_CHAT_MODEL=gpt-4o-mini
OPENAI_WEB_MODEL=gpt-4o-mini
OPENAI_EMBED_MODEL=text-embedding-3-small

WEB_SEARCH_MODE=auto
WEB_SEARCH_LIVE=true
USER_LOCATION_COUNTRY=TW
USER_LOCATION_TIMEZONE=Asia/Taipei

RAG_INDEX_DIR=./rag_store
DOCS_DIR=./docs
SYSTEM_PROMPT=You are a helpful assistant.
```

`WEB_SEARCH_MODE` can be:

- `auto`: `/ask` gives the model access to web search and lets it decide when needed.
- `always`: all `/ask` answers can use web search.
- `off`: disables web search except `/web`, which still forces it.

Optional web filters:

```env
WEB_SEARCH_ALLOWED_DOMAINS=
WEB_SEARCH_BLOCKED_DOMAINS=reddit.com,quora.com
```

## Build RAG Index

Put files into `docs/`, then run:

```powershell
python rag_index.py
```

The indexer supports `.txt`, `.pdf`, `.json`, `.jsonl`, and `.csv`. It writes normalized vectors to `rag_store/vectors.npy` and metadata to `rag_store/meta.json` plus `meta.pkl` for compatibility.

## Run

```powershell
python bot.py
```

## Docker

```powershell
docker build -t discord-ai-assistant .
docker run --env-file .env discord-ai-assistant
```

`.dockerignore` excludes `.env`, virtual environments, caches, and generated RAG indexes from the build context.

For a background process that restarts automatically while the host is online:

```powershell
docker compose up -d --build bot
docker compose logs -f bot
```

Rebuild the RAG index inside Docker:

```powershell
docker compose --profile tools build indexer
docker compose --profile tools run --rm indexer
docker compose restart bot
```

To keep the bot online when your own computer is shut down, deploy the same Compose setup to an always-on host. For a free VM path, use Google Cloud Free Tier; see [deploy/google/README.md](deploy/google/README.md) and [DEPLOYMENT.md](DEPLOYMENT.md).

This repo also includes `render.yaml` for deploying as a Render Background Worker.

## How Context Works

Discord does not automatically give the bot previous messages as model context. The bot must store and resend the relevant history itself.

This project now keeps a short memory per `(server, channel, user)`, so one user's follow-up questions do not leak into another user's context. `/ask`, `/web`, `/rag`, mentions, and DMs all share the same memory path.

## Testing

Offline checks:

```powershell
python -m py_compile bot.py rag_index.py rag_module.py discord_ai_bot\*.py
python -m unittest discover -s tests
```

Optional developer tools:

```powershell
pip install -r requirements-dev.txt
pytest -q
ruff check .
```

GitHub Actions is configured in `.github/workflows/ci.yml` to run ruff, compile checks, and tests on push and pull requests.

## Resume / Portfolio

Resume-ready project descriptions are available in [portfolio/discord-ai-assistant.md](portfolio/discord-ai-assistant.md).

## Notes

- Keep `.env` private. Do not commit real Discord or OpenAI keys.
- `rag_store/` is generated output and should not be committed.
- Web search can increase API cost, especially when `WEB_SEARCH_MODE=always`.
- For factual questions, the bot is instructed to cite web sources when web search is used and to say when information is uncertain.
