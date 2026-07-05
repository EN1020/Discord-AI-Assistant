#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/EN1020/Discord-AI-Assistant.git}"
APP_DIR="${APP_DIR:-$HOME/discord-ai-assistant}"
BRANCH="${BRANCH:-main}"

if ! command -v git >/dev/null 2>&1; then
  echo "git is required. Run deploy/oracle/bootstrap_ubuntu.sh first." >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required. Run deploy/oracle/bootstrap_ubuntu.sh first." >&2
  exit 1
fi

if [ ! -d "$APP_DIR/.git" ]; then
  echo "Cloning $REPO_URL into $APP_DIR..."
  git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
else
  echo "Updating existing checkout in $APP_DIR..."
  git -C "$APP_DIR" fetch origin "$BRANCH"
  git -C "$APP_DIR" checkout "$BRANCH"
  git -C "$APP_DIR" pull --ff-only origin "$BRANCH"
fi

cd "$APP_DIR"

if [ ! -f ".env" ]; then
  cp .env.example .env
  cat <<'MSG'

Created .env from .env.example.
Edit .env on this Oracle VM and fill in:
  DISCORD_TOKEN
  OPENAI_API_KEY

Then rerun this script.
Example:
  nano .env

MSG
  exit 2
fi

if ! grep -q '^DISCORD_TOKEN=.\+' .env || grep -q '^DISCORD_TOKEN=YOUR_DISCORD_TOKEN' .env; then
  echo "DISCORD_TOKEN is missing in .env. Edit it and rerun this script." >&2
  exit 2
fi

if ! grep -q '^OPENAI_API_KEY=.\+' .env || grep -q '^OPENAI_API_KEY=YOUR_OPENAI_KEY' .env; then
  echo "OPENAI_API_KEY is missing in .env. Edit it and rerun this script." >&2
  exit 2
fi

mkdir -p docs rag_store

echo "Building RAG index inside Docker..."
docker compose --profile tools build indexer
docker compose --profile tools run --rm indexer

echo "Starting Discord bot..."
docker compose up -d --build bot

echo "Deployment complete. Follow logs with:"
echo "  cd $APP_DIR && docker compose logs -f bot"
