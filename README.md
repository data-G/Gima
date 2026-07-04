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

## Gima Control Center

For the current build order, capability gates, and next sprint, see
[`docs/GIMA_IMPROVEMENT_PLAN.md`](/Users/gimhangunarathne/Documents/Gima/docs/GIMA_IMPROVEMENT_PLAN.md).

### Easiest macOS start

Double-click **`Start Gima.command`** in the Gima folder. It starts Gima in the
background when needed and opens the upgraded interface at
`http://127.0.0.1:8787/`. Double-clicking it again safely reuses the running
server.

The equivalent Terminal command is:

```bash
cd /Users/gimhangunarathne/Documents/Gima
./Start\ Gima.command
```

Use the short `gima` command after installing the package, or run it immediately
from this folder with `python3 -m human_ai.gima`.

```bash
python3 -m human_ai.gima status
python3 -m human_ai.gima start
python3 -m human_ai.gima talk "Hello Gima"
python3 -m human_ai.gima remember "My goal" "Build Gima into my number one personal AI"
python3 -m human_ai.gima search "personal AI"
python3 -m human_ai.gima stop
```

Direct voice conversation:

```bash
printf 'GRANT MICROPHONE\n' | python3 -m human_ai.cli --config config.local.json permission-grant --scope microphone --minutes 10
python3 -m human_ai.gima talk --voice --turns 20
```

To learn from local files or approved public URLs:

```bash
printf 'GRANT FILES\n' | python3 -m human_ai.cli --config config.local.json permission-grant --scope files --minutes 10
python3 -m human_ai.gima learn README.md
python3 -m human_ai.gima search "wake word"
```

To learn from internet search results:

```bash
printf 'GRANT WEB\n' | python3 -m human_ai.cli --config config.local.json permission-grant --scope web --minutes 10
python3 -m human_ai.gima learn-web "local LLM memory systems"
python3 -m human_ai.gima search "local LLM memory"
```

In voice mode, say `learn from internet about local LLM memory systems`, or say
`learn from internet` followed by a direct public URL.

Language learning shortcut:

```bash
printf 'GRANT WEB\n' | python3 -m human_ai.cli --config config.local.json permission-grant --scope web --minutes 10
python3 -m human_ai.gima learn-language sinhala
python3 -m human_ai.gima search "Sinhala alphabet"
```

In voice mode, say `learn Sinhala`. Gima saves the gathered knowledge to
`.human-ai/brain/sinhala.md` and indexes it as `language/sinhala` memory.

Research learning shortcut for improving Gima:

```bash
printf 'GRANT WEB\n' | python3 -m human_ai.cli --config config.local.json permission-grant --scope web --minutes 10
python3 -m human_ai.gima learn-research ai-human-systems
python3 -m human_ai.gima learn-research video-generation
python3 -m human_ai.gima search "agent memory tool use" --category research
```

In voice mode, say `learn AI-human systems papers to improve Gima`. Gima saves
the gathered papers and references to `.human-ai/brain/ai-human-systems.md` and
indexes them as `research/ai-human-systems` memory.

In voice mode, say `learn video generation`. Gima saves public papers and model
references to `.human-ai/brain/video-generation.md` and indexes them as
`research/video-generation` memory.

Parent review of learned sources:

```bash
python3 -m human_ai.gima reviews
python3 -m human_ai.gima approve review_RECORD_ID --notes "checked against source"
python3 -m human_ai.gima reject review_RECORD_ID --notes "source was not useful"
```

Gima stores source judgments in `.human-ai/csv/source_reviews.csv` and parent
approval events in `.human-ai/csv/parent_approvals.csv`. The parent approval
password is stored only as a SHA-256 hash in private `config.local.json`; it is
for approving learned knowledge, not for unlimited machine access.

For scripts, set `GIMA_PARENT_PASSWORD` in the environment instead of typing at
the prompt.

## Heart Policies

Gima stores non-violable policies in `.human-ai/heart/`. Active policies are
written to `.human-ai/heart/active_policies.md`, and the review ledger is
`.human-ai/heart/policies.csv`.

Heart access is parent-password gated. Policy candidates are reviewed one at a
time; approve to add a rule to Gima's heart, or skip to keep it out.

```bash
python3 -m human_ai.gima heart-sources
python3 -m human_ai.gima heart-list --status active
python3 -m human_ai.gima heart-next
python3 -m human_ai.gima heart-review
python3 -m human_ai.gima heart-approve openai-human-review-safeguards --notes "good for Gima"
python3 -m human_ai.gima heart-skip ibm-trust-transparency-human-augmentation --notes "not for now"
```

For scripts:

```bash
export GIMA_PARENT_PASSWORD="..."
python3 -m human_ai.gima heart-review
```

Initial external policy candidates are summarized from public AI safety sources:
OpenAI safety best practices and Preparedness Framework, Anthropic Responsible
Scaling Policy, Google AI Principles, Microsoft Responsible AI principles, and
IBM AI ethics/trust guidance. These summaries are pending until the parent user
approves them.

Heart violation attempts are blocked, logged under `.human-ai/violations/`, and
can be emailed to the configured parent address:

```bash
python3 -m human_ai.gima violation-report "heart bypass attempt" "someone tried to ignore policies"
```

The default recipient is `gimkan@gmail.com`; email delivery uses the macOS Mail
app and does not store an email password.

Teacher model knowledge transfer:

```bash
python3 -m human_ai.gima teacher-setup --provider all
printf 'GRANT WEB\n' | python3 -m human_ai.cli --config config.local.json permission-grant --scope web --minutes 10
python3 -m human_ai.gima teacher chatgpt "What should Gima learn about agent memory?"
python3 -m human_ai.gima teacher gemini "How should Gima interact with camera observations?"
python3 -m human_ai.gima transfer-knowledge "Give Gima five design lessons for safer personal AI assistants"
```

Teacher answers are saved as `teacher/chatgpt` or `teacher/gemini` review memory,
appended to `.human-ai/brain/teacher-learnings/<provider>.md`, and listed in
`.human-ai/csv/source_reviews.csv` for parent approval. In voice mode, say
`ask ChatGPT ...` or `ask Gemini ...`.

Permanent learning rule: Gima may learn only through human natural-language
explanations. Executable code, shell commands, binary payloads, encoded
instructions, and hidden machine instructions are not stored as learned
knowledge. If technical material is useful, Gima stores a plain-language summary
for review instead.

List all AI providers configured in Gima:

```bash
python3 -m human_ai.gima ai-list
```

`teacher-setup` stores keys in `.human-ai/secrets.env`, which is local runtime
state ignored by git. Gima loads this private file automatically before
checking providers or running teacher learning.

Run one bounded daily learning session from the available providers:

```bash
printf 'GRANT WEB\n' | python3 -m human_ai.cli --config config.local.json permission-grant --scope web --minutes 10
python3 -m human_ai.gima daily-learn --minutes 60
```

Install the daily macOS schedule:

```bash
python3 -m human_ai.gima schedule-daily-learning --hour 2 --minute 0 --minutes 60 --provider all
```

The schedule uses LaunchAgent `com.gima.daily-ai-learning`, appends each learned
lesson to `.human-ai/brain/teacher-learnings/`, and writes logs under
`.human-ai/logs/`. It loads API keys from your shell files and from
`.human-ai/secrets.env`, so `teacher-setup` is enough for scheduled
ChatGPT/Gemini learning to run unattended.

### Safe continuous cycle

The upgraded macOS installation uses `com.gima.continuous-cycle` at 02:00 each
day. Each bounded cycle:

- asks the working Gemini teacher for one natural-language improvement lesson;
- stores the lesson as review knowledge and rebuilds `brain.csv`;
- creates a source recovery archive and a knowledge/continuous-state snapshot;
- runs focused memory and artifact smoke tests;
- retains the latest 14 source and state snapshots.

Run or reinstall it manually:

```bash
python3 scripts/gima_continuous_cycle.py --provider gemini --rounds 1 --retention 14
python3 scripts/install_gima_continuous_cycle.py
```

Continuous learning never modifies live source code. Upgrade suggestions remain
review-only knowledge. Code upgrades still use the isolated `self-code` copy,
tests, backup, and parent-approved `self-update-sync` workflow below.

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

No spoken phrase or password grants unlimited machine ownership. A phrase such
as `Gima@3152` should not be used as a master unlock. Use scoped terminal grants
for specific abilities such as `web`, `files`, `camera`, `microphone`, and
`tools`; every grant expires and is recorded in audit memory.

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

One-prompt lip-sync project planning:

```bash
python3 -m human_ai.cli lip-sync-plan song.mp3 --face consented_face.jpg --prompt "cinematic close-up, sing naturally with warm stage lighting" --consent
```

This creates a project under `.human-ai/media/lip_sync/` with `manifest.json`,
`prompt.txt`, and `safety.txt`. It does not impersonate anyone or generate the
final video by itself; connect a consent-safe lip-sync generator later using the
manifest.

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

To skip wake-word detection and start talking immediately:

```bash
printf 'GRANT MICROPHONE\\n' | python3 -m human_ai.cli --config config.local.json permission-grant --scope microphone --minutes 10
python3 -m human_ai.cli --config config.local.json assistant-chat --model ~/.local/share/gima/models/ggml-tiny.bin --conversation-turns 20
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
  brain/
    sinhala.md
  csv/
    knowledge.csv
    conversations.csv
    source_reviews.csv
    parent_approvals.csv
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

## Self-Update Workflow

When you ask for a new Gima feature, prepare a separate backed-up working copy:

```bash
python3 -m human_ai.gima self-update-prepare "add the feature description here"
```

This creates:

- a backup archive under `.human-ai/self_updates/backups/`
- a working copy under `.human-ai/self_updates/requests/<update_id>/working_copy`
- a plan file for the requested feature

Edit and test the working copy first. When it is ready:

```bash
python3 -m human_ai.gima self-update-ready <update_id> --notes "tests passed"
```

Sync into the live Gima only after parent approval:

```bash
python3 -m human_ai.gima self-update-sync <update_id> --restart
```

Gima can also implement a requested change inside the backed-up working copy by
using the locally installed Codex coding runtime, then run the test suite and
save a reviewable patch and logs:

```bash
python3 -m human_ai.gima self-code "add the feature description here"
```

The live workspace is not changed by `self-code`. Review the generated working
copy, patch, `coding.log`, and `tests.log`, then use `self-update-ready` and the
parent-approved `self-update-sync` workflow. The web interface exposes the same
flow as **Implement in Isolated Copy** under Coding.

`self-update-sync` asks for the parent password, creates another backup before
copying, and refuses to overwrite a dirty live git workspace unless `--force` is
provided.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

Run the live product audit against the currently running web UI:

```bash
python3 scripts/gima_world_test.py --base-url http://127.0.0.1:8787 --workspace /Users/gimhangunarathne/Documents/Gima
```

The audit checks the real server, core API contracts, brain search, chat,
artifact generation, upload/download, blocked unsafe downloads, service worker
version, and response-time budgets. Reports are written to
`.human-ai/hands/out/test_reports/`.
