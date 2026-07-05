# Discord AI Assistant - Resume / Portfolio Copy

## One-line summary

Built and deployed a 24/7 Discord AI assistant using Python, Discord.py, OpenAI Responses API, local RAG, web search, Docker, and Google Cloud Free Tier.

## Chinese resume version

**Discord AI Assistant | Python, Discord.py, OpenAI API, RAG, Docker, Google Cloud**

- 開發可在 Discord 內使用的 AI 助理，支援 slash commands、mention、DM、對話上下文記憶、本地知識庫 RAG 與即時網路搜尋回答。
- 使用 OpenAI Responses API 整合文字生成與 web search，讓機器人能針對時效性問題查詢最新資料並附上來源，降低幻覺風險。
- 實作以 NumPy cosine similarity 為核心的輕量 RAG pipeline，支援 TXT、PDF、JSON、JSONL、CSV 文件索引與查詢。
- 設計以 `(server, channel, user)` 為範圍的對話記憶，避免不同使用者或頻道的上下文互相污染。
- 將專案容器化並以 Docker Compose 部署到 Google Cloud Free Tier VM，讓 Discord bot 在本機關機後仍可 24/7 運行。
- 建立 CI、單元測試、雲端部署腳本與部署文件，提升專案可維護性與可交付性。

## English resume version

**Discord AI Assistant | Python, Discord.py, OpenAI API, RAG, Docker, Google Cloud**

- Built a Discord AI assistant with slash commands, mentions, DMs, scoped conversation memory, local RAG, and optional web-grounded answers.
- Integrated the OpenAI Responses API with web search to answer time-sensitive questions with fresher context and source-backed responses.
- Implemented a lightweight NumPy cosine-similarity RAG pipeline supporting TXT, PDF, JSON, JSONL, and CSV knowledge files.
- Designed conversation memory scoped by `(server, channel, user)` to preserve follow-up context without leaking context across users.
- Containerized the bot with Docker Compose and deployed it to a Google Cloud Free Tier VM for 24/7 operation independent of the local machine.
- Added CI, unit tests, deployment scripts, and cloud deployment documentation to make the project easier to maintain and reproduce.

## Short portfolio description

This project is a production-style Discord AI assistant that combines conversational AI, retrieval-augmented generation, and web search in a real-time community environment. The bot can answer general questions, search local knowledge files, retrieve current web information, summarize recent conversations, and preserve context across follow-up messages. It is containerized with Docker Compose and deployed on a Google Cloud VM so it stays online even when the developer's local computer is shut down.

## Technical stack

- Python 3.11
- Discord.py
- OpenAI Responses API
- OpenAI Embeddings
- NumPy vector search
- Docker and Docker Compose
- Google Cloud Compute Engine
- GitHub Actions
- Pytest / unittest

## Interview talking points

- Discord does not automatically provide previous messages as LLM context, so the bot stores and resends scoped recent history.
- RAG indexes are generated artifacts and are intentionally excluded from Git to avoid committing binary vector stores.
- Web search is enabled as a controlled OpenAI tool path for current information, while local RAG remains available for private or project-specific documents.
- Deployment moved from local-only execution to an always-on Google Cloud VM using Docker Compose and restart policies.
