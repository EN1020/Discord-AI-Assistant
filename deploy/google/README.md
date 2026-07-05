# Google Cloud Free Tier Deployment

This guide deploys the Discord bot to a Google Cloud Compute Engine VM that can keep running after your local computer shuts down.

## Free Tier shape

Google Cloud's Free Tier currently includes:

- 1 non-preemptible `e2-micro` VM per month.
- Eligible regions: `us-west1`, `us-central1`, or `us-east1`.
- 30 GB-months standard persistent disk.
- 1 GB outbound data transfer from North America to most destinations per month.

Use exactly this style of VM to stay inside the Free Tier:

- Machine type: `e2-micro`
- Region: `us-west1`, `us-central1`, or `us-east1`
- Boot disk: 30 GB or less, `pd-standard`
- OS: Ubuntu LTS
- No GPU, no static external IP, no extra disks

The bot does not need inbound HTTP ports. It only needs outbound internet access to Discord and OpenAI.

## Option A: Create the VM in the Google Cloud Console

1. Open Google Cloud Console.
2. Create or select a project.
3. Enable Compute Engine.
4. Create VM instance.
5. Choose one Free Tier region:
   - `us-west1` Oregon
   - `us-central1` Iowa
   - `us-east1` South Carolina
6. Machine type: `e2-micro`.
7. Boot disk: Ubuntu LTS, standard persistent disk, 30 GB or less.
8. Do not add GPU or extra disks.
9. Create the VM.
10. SSH into the VM from the console.

## Option B: Create the VM with gcloud

Install and sign in to the Google Cloud CLI, then:

```bash
export PROJECT_ID=your-google-cloud-project-id
export ZONE=us-west1-b
deploy/google/create_vm_gcloud.sh
```

Connect:

```bash
gcloud compute ssh discord-ai-bot --zone=us-west1-b
```

## Install Docker on the VM

On the VM:

```bash
curl -fsSL https://raw.githubusercontent.com/EN1020/Discord-AI-Assistant/main/deploy/google/bootstrap_ubuntu.sh -o bootstrap_ubuntu.sh
chmod +x bootstrap_ubuntu.sh
./bootstrap_ubuntu.sh
```

Log out and back in after bootstrap so Docker group membership takes effect.

## Deploy the bot

```bash
curl -fsSL https://raw.githubusercontent.com/EN1020/Discord-AI-Assistant/main/deploy/google/deploy_bot.sh -o deploy_bot.sh
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

## Cost safety

To stay close to free:

- Keep only one `e2-micro` VM running.
- Use only supported Free Tier regions.
- Keep the boot disk at or below 30 GB standard persistent disk.
- Avoid static external IPs, GPUs, snapshots, extra disks, and paid services.
- Create a billing budget alert in Google Cloud Billing.
