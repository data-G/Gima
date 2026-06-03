# Human AI Local

`human-ai-local` is a local-first foundation for a personal multimodal agent. It
uses readable CSV files as durable memory and a disposable SQLite FTS5 index for
fast recall. The initial release is intentionally modular: it works on a basic
Mac immediately and activates richer media features when optional native tools
are installed.

It is not an autonomous human mind. It is a controlled assistant framework with
memory, retrieval, file ingestion, optional local-model chat, explicit web
imports, local speech output, screen capture, camera adapters, and an allowlisted
tool runner.

## Quick Start

Python 3.9 or newer is sufficient for the core:

```bash
cd /Users/gimhangunarathne/Documents/Gima
python3 -m human_ai.cli init
python3 -m human_ai.cli doctor
printf 'GRANT CAMERA,MICROPHONE\\n' | python3 -m human_ai.cli permission-grant --scope camera --scope microphone --minutes 10
python3 -m human_ai.cli permission-status
python3 -m human_ai.cli ingest README.md
python3 -m human_ai.cli search "multimodal memory"
python3 -m human_ai.cli chat "What do you remember about this project?"
python3 -m human_ai.cli conversation-history "project"
python3 -m human_ai.cli speak "Local speech is working"
```

CSV memory is stored under `.human-ai/csv/`. The SQLite file
`.human-ai/index.sqlite3` is only a generated search cache. Delete it and run
`python3 -m human_ai.cli rebuild` at any time.

Typed chat, wake transcripts, and assistant wake responses are appended to
`.human-ai/csv/conversations.csv`. Search recent conversation history locally:

```bash
python3 -m human_ai.cli conversation-history
python3 -m human_ai.cli conversation-history "umbrella"
python3 -m human_ai.cli conversation-history --session-id SESSION_ID
```

## Capabilities

| Capability | Available now | Optional enhancement |
| --- | --- | --- |
| CSV long-term memory | Yes | Miller and csvkit maintenance commands |
| Fast categorized recall | SQLite FTS5 | DuckDB analytics for large archives |
| Text, code, JSON, CSV ingestion | Yes | Add specialized readers as needed |
| Images | Metadata | Tesseract OCR |
| PDF files | Metadata fallback | `pdftotext` extraction |
| Video and audio | Metadata | FFmpeg and `ffprobe` |
| Voice output | macOS `say` | Piper voices |
| Voice input | Adapter-ready | `whisper.cpp` |
| Screen capture | macOS `screencapture` | Periodic event detector |
| Camera capture | Adapter-ready | `imagesnap` or FFmpeg |
| Anonymous people count | Local detector adapter | Small COCO-compatible detector |
| Bounded camera monitor | Adapter-ready | `imagesnap` or FFmpeg |
| Video frame sampling | Adapter-ready | FFmpeg |
| Audio and video transcription | Adapter-ready | `whisper.cpp` |
| Multilingual transcript wake word | Yes | Continuous microphone adapter |
| Web research | Explicit URL import | Configure approved domains |
| Local reasoning | Retrieval fallback | `llama.cpp` OpenAI-compatible server |
| Code and shell tools | Disabled by default | Enable allowlisted tools explicitly |

Use `python3 -m human_ai.cli doctor` to see which optional tools are installed.

## Configuration

Copy `config.example.json` to a private local file such as `config.local.json`.
Pass it using `--config config.local.json`. Local model chat expects an
OpenAI-compatible endpoint such as a `llama-server` process on
`http://127.0.0.1:8080/v1`.

Web import accepts public HTTP and HTTPS addresses only. Set `web.allowed_domains`
to restrict imports further. Imported pages enter memory with `review` status
instead of immediately becoming trusted facts.

```bash
python3 -m human_ai.cli web-import https://example.com
python3 -m human_ai.cli memory-review
python3 -m human_ai.cli memory-approve kb_RECORD_ID
```

Tool execution is disabled by default. When enabled, the runner accepts only
configured executable names, uses the configured workspace as its working
directory, captures output, enforces a timeout, and writes an audit event.

## Local Brain

Gima can use a local `llama.cpp` model as its ChatGPT-style language brain. This
keeps the conversation on this Mac and exposes the model through an
OpenAI-compatible local server at `http://127.0.0.1:8080/v1`.

Create a private `config.local.json`, enable the model, and point it at a GGUF
file:

```json
{
  "model": {
    "enabled": true,
    "base_url": "http://127.0.0.1:8080/v1",
    "model": "gima-local-qwen2.5-1.5b",
    "model_path": "~/.local/share/gima/models/qwen2.5-1.5b-instruct-q4_k_m.gguf",
    "context_size": 4096,
    "host": "127.0.0.1",
    "port": 8080,
    "device": "none",
    "gpu_layers": 0,
    "warmup": false
  }
}
```

Then run:

```bash
python3 -m human_ai.cli --config config.local.json brain-start
python3 -m human_ai.cli --config config.local.json brain-status
python3 -m human_ai.cli --config config.local.json chat "Talk to me like Gima"
python3 -m human_ai.cli --config config.local.json brain-stop
```

This is not the same scale as ChatGPT or Gemini. The local model is smaller, but
it can answer conversationally, use retrieved CSV memory, and run without paying
for a cloud API.

## Scoped Permissions

The agent never accepts a spoken password as authorization for full machine
access. Speech can be replayed or misheard. It also never bypasses macOS privacy
prompts, requests root privileges, or disables operating-system security.

Start a short local permission session from the terminal instead:

```bash
python3 -m human_ai.cli permission-grant --scope camera --scope microphone --minutes 10
python3 -m human_ai.cli permission-status
python3 -m human_ai.cli permission-revoke
```

The terminal asks for an exact confirmation. Available scopes are `camera`,
`files`, `microphone`, `tools`, and `web`. Grants expire automatically, are
stored only under `.human-ai/`, and are recorded in the local audit CSV. The
default maximum lifetime is 30 minutes.

## Daily Source Summary

Create a local source-code attachment and Git summary:

```bash
python3 -m human_ai.cli daily-summary
python3 -m human_ai.cli daily-summary-email --to gimkan@gmail.com
```

The ZIP contains every Git-tracked program file plus a summary of commits and
uncommitted changes since midnight. Private runtime data under `.human-ai/`,
including conversation history and camera media, is excluded. Email delivery
uses the macOS Mail app and its configured account; the program does not store
an email password.

## Media Commands

Media processing activates automatically when the corresponding native tool is
available:

```bash
python3 -m human_ai.cli screen-capture
python3 -m human_ai.cli camera-capture
python3 -m human_ai.cli camera-monitor --frames 12 --interval 5
python3 -m human_ai.cli camera-observe --device 0
python3 -m human_ai.cli scene-observe /path/to/frame.jpg
python3 -m human_ai.cli video-analyze recording.mp4 --seconds 10
python3 -m human_ai.cli transcribe recording.wav --model /path/to/ggml-base.en.bin
```

The monitor is deliberately bounded. Continuous background observation should
be added later with visible recording status, retention rules, and an event
detector that discards unchanged frames.

### Multiple People And Cameras

The vision adapter supports zero, one, or many visible people. It stores
anonymous scene events such as `4 people are visible near front_camera`. It does
not infer names, search faces on the web, or claim that a detected person is the
profile owner.

Configure a local COCO-style object detector separately. Its command receives
the image path in place of `{image}` and must print JSON:

```json
{
  "vision": {
    "camera_id": "front_camera",
    "camera_device": "0",
    "detect_people_on_wake": true,
    "detector_command": ["local-detector", "--image", "{image}", "--json"],
    "minimum_confidence": 0.5
  }
}
```

Expected detector output:

```json
{
  "detections": [
    {"label": "person", "confidence": 0.91, "box": [10, 20, 100, 220]},
    {"label": "person", "confidence": 0.86, "box": [140, 18, 250, 225]}
  ]
}
```

Run one process per configured camera when monitoring multiple local or network
cameras. Keep recording status visible and apply retention rules for saved
frames.

## Wake Word

The `wake` command recognizes the configured word `Gima` inside a Unicode speech
transcript, greets the enrolled local profile, and optionally captures one local
photo:

```bash
python3 -m human_ai.cli wake "こんにちは Gima"
python3 -m human_ai.cli wake "Hello Gima" --capture-photo
python3 -m human_ai.cli wake-listen --model /path/to/ggml-base.bin --cycles 15
python3 -m human_ai.cli assistant-run --model ~/.local/share/gima/models/ggml-tiny.bin
python3 -m human_ai.cli assistant-command "what time is it"
```

Photo capture requires `imagesnap` or FFmpeg. It is disabled unless requested
with `--capture-photo` or enabled in a private configuration file:

```json
{
  "wake": {
    "word": "Gima",
    "aliases": [],
    "camera_on_wake": true,
    "speak_on_wake": true,
    "profile_name": "Gima",
    "profile_about": "Add an approved local profile summary here.",
    "profile_sources": ["https://example.com/approved-profile"]
  }
}
```

The photo remains local. This project does not upload camera images for face
search or infer a person's identity from an image. Add known profile details and
approved public URLs explicitly, then use `web-import` when you want to index a
specific source.

## Voice Assistant

`assistant-run` waits for the wake word, says it is listening, then keeps a
conversation open until it hears `End Game`. It answers through the Mac speaker,
logs the exchange, and performs only bounded local actions. Supported built-in
actions include time/status answers, camera photo, screenshot, daily summary
creation, and local memory search. Actions still require active scoped
permissions.

Example:

```bash
printf 'GRANT MICROPHONE,CAMERA\\n' | python3 -m human_ai.cli permission-grant --scope microphone --scope camera --minutes 10
python3 -m human_ai.cli assistant-run --model ~/.local/share/gima/models/ggml-tiny.bin --cycles 20 --conversation-turns 20
```

For a visible 24/7-style loop, run:

```bash
python3 -m human_ai.cli assistant-run --model ~/.local/share/gima/models/ggml-tiny.bin --forever --cycles 999999 --conversation-turns 999999
```

Kill phrase: say `End Game`. In normal mode that stops the process. In
`--forever` mode it ends the current conversation and returns to waiting for
`Gima`.

## Memory Layout

```text
.human-ai/
  csv/
    knowledge.csv
    conversations.csv
    audit.csv
  media/
  index.sqlite3
```

`knowledge.csv` uses a stable schema:

```csv
id,category,subcategory,kind,title,content,keywords,source,media_path,created_at,updated_at,confidence,status,checksum
```

Media stays on disk; CSV stores searchable metadata and paths. File records are
split into chunks so recall remains focused and responsive.

## Suggested Optional Tools

Install only what you need:

```bash
brew install ffmpeg tesseract poppler miller csvkit
```

For speech recognition and local models, build or install `whisper.cpp` and
`llama.cpp` separately, then select small quantized models suitable for an Intel
Mac with 16 GB RAM.

## Safety Model

Camera use, screen capture, web imports, and tool execution are explicit or
configured opt-in commands. The foundation does not silently watch the camera,
crawl the internet, upload biometric images, rewrite its own code, delete files,
or publish anything. Those behaviors should remain visible, permissioned
workflows as the system grows.

## Tests

```bash
python3 -m unittest discover -s tests -v
```
