# WAN555 Hugging Face Space Video API

Source: https://huggingface.co/spaces/kulkas2pintu/wan555/agents.md

## Purpose

WAN555 is a Hugging Face Space described as generating animated video from a single image. Gima may use this as an optional cloud video backend only when the user explicitly allows cloud processing.

## Safety Gate

Before Gima uploads an image, prompt, audio file, face image, or likeness to this service, all of these must be true:

- `CLOUD_ALLOWED=true`
- `HF_TOKEN` is available in the environment or authorized secret store
- the user explicitly asks to use the Hugging Face WAN555 Space
- the user confirms they own or have permission to use the input image, likeness, prompt, and output
- Gima does not bypass login, payment, rate limits, CAPTCHA, queues, or API restrictions

## API Notes From `agents.md`

- API schema: `GET https://kulkas2pintu-wan555.hf.space/gradio_api/info`
- Config / function index: `GET https://kulkas2pintu-wan555.hf.space/config`, then find `dependencies[i].id` where `api_name` matches the API schema endpoint
- Upload files: `POST https://kulkas2pintu-wan555.hf.space/gradio_api/upload -F "files=@file.ext"`
- Uploaded file input shape: `{"path": "<returned-path>", "meta": {"_type": "gradio.FileData"}, "orig_name": "file.ext"}`
- Join queue: `POST https://kulkas2pintu-wan555.hf.space/gradio_api/queue/join`
- Queue body: `{"data": [...], "fn_index": <from-config>, "session_hash": "<random-uuid>"}`
- Stream results: `GET https://kulkas2pintu-wan555.hf.space/gradio_api/queue/data?session_hash=<same-uuid>`
- Auth: `Bearer $HF_TOKEN`

## Gima Integration Plan

1. Add provider id `wan555_huggingface_space` to Gima's open video target catalog.
2. Keep execution disabled unless `CLOUD_ALLOWED=true` and explicit consent are present.
3. Inspect `/gradio_api/info` and `/config` at runtime, because Gradio function indexes can change.
4. Upload only user-approved files.
5. Save a local manifest with source URL, endpoint, prompt, input filenames, queue id/session hash, output path, and safety confirmations.
6. Add a repair loop for queue errors and timeout handling.

## User-Facing Prompt

When the user asks for this backend, Gima should say:

`WAN555 is a third-party Hugging Face Space. I can use it only if CLOUD_ALLOWED=true and you confirm this image/prompt is yours or authorized for cloud upload. Should I proceed?`
