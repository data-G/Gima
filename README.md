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
python3 -m human_ai.cli ingest README.md
python3 -m human_ai.cli search "multimodal memory"
python3 -m human_ai.cli chat "What do you remember about this project?"
python3 -m human_ai.cli speak "Local speech is working"
```

CSV memory is stored under `.human-ai/csv/`. The SQLite file
`.human-ai/index.sqlite3` is only a generated search cache. Delete it and run
`python3 -m human_ai.cli rebuild` at any time.

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

## Media Commands

Media processing activates automatically when the corresponding native tool is
available:

```bash
python3 -m human_ai.cli screen-capture
python3 -m human_ai.cli camera-capture
python3 -m human_ai.cli camera-monitor --frames 12 --interval 5
python3 -m human_ai.cli video-analyze recording.mp4 --seconds 10
python3 -m human_ai.cli transcribe recording.wav --model /path/to/ggml-base.en.bin
```

The monitor is deliberately bounded. Continuous background observation should
be added later with visible recording status, retention rules, and an event
detector that discards unchanged frames.

## Wake Word

The `wake` command recognizes the configured word `Gima` inside a Unicode speech
transcript, greets the enrolled local profile, and optionally captures one local
photo:

```bash
python3 -m human_ai.cli wake "こんにちは Gima"
python3 -m human_ai.cli wake "Hello Gima" --capture-photo
python3 -m human_ai.cli wake-listen --model /path/to/ggml-base.bin --cycles 15
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
