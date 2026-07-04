# Gima on Google Cloud Run

This deploys Gima's web UI to Google Cloud Run as service `gima`.

Cloud mode is different from the Mac mode:

- It uses `config.cloud.json`.
- It stores runtime CSV memory in `/tmp/gima-data`, which is temporary Cloud Run storage.
- The local LLM server is disabled by default.
- Online AI engines use API keys provided as environment variables or Secret Manager later.
- Free quota mode stays enabled.

## 1. Install and Login

Install Google Cloud CLI:

https://cloud.google.com/sdk/docs/install

Then:

```bash
gcloud auth login
gcloud auth application-default login
```

## 2. Deploy

From this repo:

```bash
cd /Users/gimhangunarathne/Documents/Gima
./scripts/gcp_deploy_gima.sh gima-YOUR_UNIQUE_ID
```

GCP project IDs are globally unique, so plain `gima` is probably already taken.
Use something like:

```bash
./scripts/gcp_deploy_gima.sh gima-gimhan-20260612
```

Region defaults to Tokyo:

```bash
GIMA_GCP_REGION=asia-northeast1 ./scripts/gcp_deploy_gima.sh gima-gimhan-20260612
```

If you need to link billing from the command line:

```bash
GIMA_BILLING_ACCOUNT=000000-000000-000000 ./scripts/gcp_deploy_gima.sh gima-gimhan-20260612
```

## 3. API Keys

After deploy, set provider keys as Cloud Run environment variables or Secret
Manager secrets:

- `GEMINI_API_KEY`
- `OPENROUTER_API_KEY`
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`
- `XAI_API_KEY`
- `DEEPSEEK_API_KEY`

For free-first use, start with Gemini and OpenRouter.

Example:

```bash
gcloud run services update gima \
  --region asia-northeast1 \
  --set-env-vars GEMINI_API_KEY=YOUR_KEY,OPENROUTER_API_KEY=YOUR_KEY
```

## 4. Important Persistence Note

Cloud Run `/tmp` storage is temporary. For durable cloud memory, the next upgrade
should mount Cloud Storage or use Firestore/Cloud SQL for:

- `.human-ai/csv/teacher_answer_cache.csv`
- `.human-ai/csv/knowledge.csv`
- `.human-ai/brain/brain.csv`
- generated files under `hands/out`

The current deployment proves the web app runs in cloud and keeps per-instance
memory during an active container lifetime.
