# Gima Music and Video API Integrations

## Purpose

Gima is local-first by default, then uses approved cloud APIs only when the user explicitly enables cloud access.

## Music Generation

### Local fallback

- Tool: `LocalSongSketcher`
- Output: rough offline WAV sketch in `hands/out/song_sketch`
- Use when speed, privacy, or offline work matters.

### Open-source API path

- Tool: `ExternalMusicApiGenerator`
- Provider id: `huggingface_musicgen`
- Default endpoint: `https://api-inference.huggingface.co/models/facebook/musicgen-small`
- Environment:
  - `CLOUD_ALLOWED=true`
  - `HUGGINGFACE_API_KEY` or `HF_TOKEN`
  - Optional `GIMA_MUSICGEN_ENDPOINT_URL`

### Suno-compatible path

- Tool: `ExternalMusicApiGenerator`
- Provider id: `suno_compatible`
- Environment:
  - `CLOUD_ALLOWED=true`
  - `GIMA_SUNO_API_BASE_URL`
  - `SUNO_API_KEY` or `GIMA_MUSIC_API_KEY`
  - Optional `GIMA_SUNO_GENERATE_PATH`, default `/api/generate`

Safety rule: use only official, partner, or otherwise authorized music API gateways. Gima must not use browser-token scraping, CAPTCHA bypass, payment bypass, rate-limit bypass, or credential extraction.

### WAIvePulse local open-source path

- Tool: `ExternalMusicApiGenerator`
- Provider id: `waivepulse_local`
- Source: `https://github.com/weellio/waivepulse`
- Backend: WAIvePulse FastAPI server on port `7861`
- Environment:
  - Optional `GIMA_WAIVEPULSE_URL`, default `http://127.0.0.1:7861`
- Notes:
  - WAIvePulse uses HeartMuLa 3B and exposes `POST /generate`, `GET /status/{job_id}`, and `GET /model-status`.
  - It requires lyrics with section markers such as `[Verse]` and `[Chorus]`.
  - The upstream README says HeartMuLa generation requires Windows/Linux with NVIDIA CUDA and about 12 GB VRAM. macOS cannot run the generator locally, but Gima can control a WAIvePulse server running on another compatible machine.
  - The project license is MIT plus Commons Clause, so review the license before commercial redistribution of the software itself.

## Video Generation

### Local/open-source video

- Tool: `OpenSourceVideoApiRenderer`
- Backend: ComfyUI API workflow
- Environment:
  - Optional `GIMA_COMFYUI_URL`, default `http://127.0.0.1:8188`
- Use with API-format workflows for open video model stacks such as Wan, HunyuanVideo, AnimateDiff, Mochi, or LTX-style workflows, according to each model license.

### WAN555 Hugging Face Space path

- Provider id: `wan555_huggingface_space`
- Source: `https://huggingface.co/spaces/kulkas2pintu/wan555/agents.md`
- Backend: Hugging Face Space / Gradio queue API
- Purpose: animated video from a single image
- Environment:
  - `CLOUD_ALLOWED=true`
  - `HF_TOKEN`
- Endpoints:
  - `GET https://kulkas2pintu-wan555.hf.space/gradio_api/info`
  - `GET https://kulkas2pintu-wan555.hf.space/config`
  - `POST https://kulkas2pintu-wan555.hf.space/gradio_api/upload`
  - `POST https://kulkas2pintu-wan555.hf.space/gradio_api/queue/join`
  - `GET https://kulkas2pintu-wan555.hf.space/gradio_api/queue/data?session_hash=<same-uuid>`
- Safety: this is third-party cloud processing. Gima must ask before upload and must not bypass login, queues, quotas, CAPTCHA, rate limits, payment, or API restrictions.

### OpenRouter/Veo-style cloud video

- Tool: `OpenRouterVideoGenerator`
- Default model: `google/veo-3.1`
- Environment:
  - `CLOUD_ALLOWED=true`
  - `OPENROUTER_API_KEY`
- Uses OpenRouter async video generation endpoints and stores the MP4 plus a provenance manifest in `hands/out/openrouter_video`.

## Required User Consent

Cloud music/video generation requires:

1. `CLOUD_ALLOWED=true`
2. an API key in the environment or saved binding
3. explicit request consent from the UI/backend payload
4. rights-safe prompts, lyrics, images, voices, likenesses, and songs
