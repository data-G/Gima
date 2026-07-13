#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_ID="${1:-gima-$(date +%Y%m%d%H%M%S)}"
REGION="${GIMA_GCP_REGION:-asia-northeast1}"
SERVICE="${GIMA_CLOUD_RUN_SERVICE:-gima}"
BILLING_ACCOUNT="${GIMA_BILLING_ACCOUNT:-}"

cd "$ROOT_DIR"

if ! command -v gcloud >/dev/null 2>&1; then
  echo "gcloud is not installed."
  echo "Install Google Cloud CLI first: https://cloud.google.com/sdk/docs/install"
  exit 2
fi

if ! gcloud auth list --filter=status:ACTIVE --format='value(account)' | grep -q .; then
  echo "No active gcloud login found. Run: gcloud auth login"
  exit 2
fi

if ! gcloud projects describe "$PROJECT_ID" >/dev/null 2>&1; then
  echo "Creating GCP project: $PROJECT_ID"
  gcloud projects create "$PROJECT_ID" --name="Gima"
else
  echo "Using existing GCP project: $PROJECT_ID"
fi

gcloud config set project "$PROJECT_ID" >/dev/null

if [[ -n "$BILLING_ACCOUNT" ]]; then
  echo "Linking billing account: $BILLING_ACCOUNT"
  gcloud billing projects link "$PROJECT_ID" --billing-account "$BILLING_ACCOUNT"
else
  echo "No GIMA_BILLING_ACCOUNT set. If build/deploy fails, link billing in GCP Console or set it and rerun."
fi

echo "Enabling required APIs..."
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  containerregistry.googleapis.com \
  secretmanager.googleapis.com

echo "Submitting Cloud Build for Cloud Run deploy..."
gcloud builds submit \
  --config cloudbuild.yaml \
  --substitutions "_REGION=$REGION,_SERVICE=$SERVICE" \
  .

URL="$(gcloud run services describe "$SERVICE" --region "$REGION" --format='value(status.url)')"
echo
echo "Gima Cloud Run is live:"
echo "$URL"
echo
echo "Optional API keys via Secret Manager / env vars:"
echo "  OPENAI_API_KEY, GEMINI_API_KEY, ANTHROPIC_API_KEY, XAI_API_KEY, DEEPSEEK_API_KEY, OPENROUTER_API_KEY"
