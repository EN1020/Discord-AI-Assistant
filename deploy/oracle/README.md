# Oracle Cloud Always Free Deployment

This guide deploys the Discord bot to an Oracle Cloud Always Free VM so it can keep running after your local computer shuts down.

## Recommended VM

Use an Ubuntu image and one of these Always Free shapes:

- Best choice: `VM.Standard.A1.Flex` with 1 OCPU and 6 GB RAM, or 2 OCPUs and 12 GB RAM if available.
- Smaller fallback: `VM.Standard.E2.1.Micro`, but it has only 1 GB RAM and can be tight for Docker builds.

The bot does not need inbound HTTP ports. It only needs outbound internet access to Discord and OpenAI. Keep SSH open only to your own IP when possible.

Oracle notes that idle Always Free compute instances can be reclaimed if they remain very idle for a 7-day period. For a hobby Discord bot this is usually acceptable, but it is still a free-tier risk.

## Create the VM

1. Sign in to Oracle Cloud.
2. Create an Always Free Ubuntu VM.
3. Save the private SSH key.
4. Connect by SSH:

```bash
ssh ubuntu@YOUR_VM_PUBLIC_IP
```

Some Oracle Linux images use `opc` instead of `ubuntu`, but this guide assumes Ubuntu.

## Install Docker

On the VM:

```bash
curl -fsSL https://raw.githubusercontent.com/EN1020/Discord-AI-Assistant/main/deploy/oracle/bootstrap_ubuntu.sh -o bootstrap_ubuntu.sh
chmod +x bootstrap_ubuntu.sh
./bootstrap_ubuntu.sh
```

Log out and back in after bootstrap so Docker group membership takes effect:

```bash
exit
ssh ubuntu@YOUR_VM_PUBLIC_IP
```

## Deploy the bot

```bash
curl -fsSL https://raw.githubusercontent.com/EN1020/Discord-AI-Assistant/main/deploy/oracle/deploy_bot.sh -o deploy_bot.sh
chmod +x deploy_bot.sh
./deploy_bot.sh
```

The first run creates `.env` and stops. Edit it:

```bash
nano ~/discord-ai-assistant/.env
```

Fill in:

```env
DISCORD_TOKEN=...
OPENAI_API_KEY=...
```

Then rerun:

```bash
./deploy_bot.sh
```

## Check status

```bash
cd ~/discord-ai-assistant
docker compose ps
docker compose logs -f bot
```

## Update later

```bash
cd ~/discord-ai-assistant
git pull
docker compose up -d --build bot
```

If you changed files in `docs/`, rebuild the RAG index:

```bash
docker compose --profile tools build indexer
docker compose --profile tools run --rm indexer
docker compose restart bot
```

## Stop

```bash
cd ~/discord-ai-assistant
docker compose down
```
