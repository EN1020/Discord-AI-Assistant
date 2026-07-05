# Deployment

## Important limitation

If the bot runs only on your own computer, it will go offline when that computer is shut down. Docker can restart the bot after crashes or reboots, but Docker cannot keep a powered-off local machine online.

To keep the bot available while your local computer is off, run this project on an always-on machine, such as:

- A VPS or cloud VM.
- Google Cloud Free Tier VM.
- Oracle Cloud Always Free VM.
- Render Background Worker.
- A NAS or mini PC that stays powered on.
- A Raspberry Pi or small home server that stays powered on.

The same Docker Compose setup works in all of those places.

## Recommended free path: Google Cloud Free Tier

Google Cloud Free Tier is now the recommended free path for this project because Oracle signup can be painful. Use a Compute Engine `e2-micro` VM in an eligible US region and deploy with the scripts in `deploy/google/`.

Current notes checked on 2026-07-05:

- Google Cloud Free Tier requires an active billing account.
- Google says temporary card authorization is a hold, not an actual charge, often between `$0.00` and `$1.00 USD`.
- Compute Engine Free Tier includes one non-preemptible `e2-micro` VM per month in `us-west1`, `us-central1`, or `us-east1`.
- It also includes 30 GB-months standard persistent disk and 1 GB outbound data transfer from North America to most destinations.
- The Free Tier has no fixed end date, but Google can change limits with advance notice.

Quick path after you create a Google Cloud Ubuntu `e2-micro` VM:

```bash
curl -fsSL https://raw.githubusercontent.com/EN1020/Discord-AI-Assistant/main/deploy/google/bootstrap_ubuntu.sh -o bootstrap_ubuntu.sh
chmod +x bootstrap_ubuntu.sh
./bootstrap_ubuntu.sh
```

Log out and back in, then:

```bash
curl -fsSL https://raw.githubusercontent.com/EN1020/Discord-AI-Assistant/main/deploy/google/deploy_bot.sh -o deploy_bot.sh
chmod +x deploy_bot.sh
./deploy_bot.sh
```

The first deploy creates `.env`; edit it with your secrets, then rerun `./deploy_bot.sh`.

See [deploy/google/README.md](deploy/google/README.md) for the full Google Cloud walkthrough.

## Alternative free path: Oracle Cloud Always Free

Oracle Cloud Always Free can also run this bot, but signup and capacity can be frustrating. Use this path only if you already have an Oracle account working. Deploy with the scripts in `deploy/oracle/`.

Quick path after you create an Oracle Ubuntu VM:

```bash
curl -fsSL https://raw.githubusercontent.com/EN1020/Discord-AI-Assistant/main/deploy/oracle/bootstrap_ubuntu.sh -o bootstrap_ubuntu.sh
chmod +x bootstrap_ubuntu.sh
./bootstrap_ubuntu.sh
```

Log out and back in, then:

```bash
curl -fsSL https://raw.githubusercontent.com/EN1020/Discord-AI-Assistant/main/deploy/oracle/deploy_bot.sh -o deploy_bot.sh
chmod +x deploy_bot.sh
./deploy_bot.sh
```

The first deploy creates `.env`; edit it with your secrets, then rerun `./deploy_bot.sh`.

See [deploy/oracle/README.md](deploy/oracle/README.md) for the full Oracle walkthrough.

## Recommended path: Render Background Worker

Render Background Workers are a good fit for Discord bots because the process runs continuously and does not need inbound HTTP traffic. This repo includes `render.yaml`, so Render can create the worker from the repository.

Current notes checked on 2026-07-05:

- Render docs describe background workers as continuously running services with no incoming network traffic.
- Render pricing lists background workers under service compute; the starter instance is listed at `$7/month`.
- Render's Blueprint spec supports `type: worker`, `runtime: docker`, `dockerCommand`, and secret prompts using `sync: false`.

Steps:

1. Push this repo to GitHub.
2. In Render, create a new Blueprint from the GitHub repo.
3. Render will detect `render.yaml`.
4. Enter these secret values when Render prompts:
   - `DISCORD_TOKEN`
   - `OPENAI_API_KEY`
5. Keep the default `starter` plan or choose a larger instance if needed.
6. Deploy.
7. Open the Render logs and confirm the bot logs in.

The Blueprint sets:

- `region: singapore`, which is usually a reasonable default for Taiwan.
- `AUTO_BUILD_RAG_ON_START=true`, so the worker can build `rag_store` at startup when the generated index is missing.
- `DOCS_DIR=/app/docs` and `RAG_INDEX_DIR=/app/rag_store`, which are container-safe paths.

Because Render workers are not your local computer, your Discord bot can keep running after your local computer is shut down.

## Local always-on while the computer is on

Build the image and start the bot in the background:

```powershell
docker compose up -d --build bot
```

View logs:

```powershell
docker compose logs -f bot
```

Stop the bot:

```powershell
docker compose down
```

Rebuild the local RAG index inside Docker:

```powershell
docker compose --profile tools run --rm indexer
docker compose restart bot
```

`restart: unless-stopped` means Docker will restart the bot after a crash and after Docker starts again, unless you explicitly stop the container.

## Run on an always-on host

1. Install Docker and Docker Compose on the host.
2. Copy this project to the host.
3. Create a `.env` file on the host from `.env.example`.
4. Put documents in `docs/`.
5. Build the RAG index:

```bash
docker compose --profile tools run --rm indexer
```

6. Start the bot:

```bash
docker compose up -d --build bot
```

7. Check logs:

```bash
docker compose logs -f bot
```

After this, your local computer can shut down and the Discord bot will keep running as long as the always-on host remains online.

## Updating the bot on the host

```bash
git pull
docker compose up -d --build bot
```

If you changed files in `docs/`, rebuild the RAG index:

```bash
docker compose --profile tools build indexer
docker compose --profile tools run --rm indexer
docker compose restart bot
```

## Secrets

Do not commit `.env`. Keep `DISCORD_TOKEN` and `OPENAI_API_KEY` only on the machine that runs the bot.
