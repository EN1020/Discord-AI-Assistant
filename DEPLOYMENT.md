# Deployment

## Important limitation

If the bot runs only on your own computer, it will go offline when that computer is shut down. Docker can restart the bot after crashes or reboots, but Docker cannot keep a powered-off local machine online.

To keep the bot available while your local computer is off, run this project on an always-on machine, such as:

- A VPS or cloud VM.
- Google Cloud Free Tier VM.
- A NAS or mini PC that stays powered on.
- A Raspberry Pi or small home server that stays powered on.

The same Docker Compose setup works in all of those places.

## Recommended free path: Google Cloud Free Tier

Google Cloud Free Tier is the recommended free cloud path for this project. Use a Compute Engine `e2-micro` VM in an eligible US region and deploy with the scripts in `deploy/google/`.

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
