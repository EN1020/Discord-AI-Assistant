#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-}"
ZONE="${ZONE:-us-west1-b}"
INSTANCE_NAME="${INSTANCE_NAME:-discord-ai-bot}"

if [ -z "$PROJECT_ID" ]; then
  echo "Set PROJECT_ID first, for example:" >&2
  echo "  export PROJECT_ID=your-google-cloud-project-id" >&2
  exit 1
fi

gcloud config set project "$PROJECT_ID"

gcloud compute instances create "$INSTANCE_NAME" \
  --zone="$ZONE" \
  --machine-type=e2-micro \
  --image-family=ubuntu-2404-lts-amd64 \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=30GB \
  --boot-disk-type=pd-standard \
  --maintenance-policy=MIGRATE \
  --provisioning-model=STANDARD \
  --scopes=https://www.googleapis.com/auth/cloud-platform

echo "VM created. Connect with:"
echo "  gcloud compute ssh $INSTANCE_NAME --zone=$ZONE"
