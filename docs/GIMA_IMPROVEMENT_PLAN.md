# Gima Improvement Plan

Version 1.1 | 1 July 2026

This plan turns Gima's broad AI roadmap into an implementation order. The goal is not to claim that Gima already matches frontier systems. The goal is to make each upgrade testable, visible in the interface, stored in memory, and safe enough to keep improving.

## North Star

Gima should become a local-first AI workspace that can:

- answer from durable local memory with citations;
- research the internet when current facts are needed;
- operate as an OSINT-style public research assistant with source registers, contradiction notes, and exportable evidence;
- run authorized research and security-audit workflows only for public sources, open-source code, or user-owned/permitted systems with confirmed scope;
- create real downloadable artifacts such as Excel, JPG, PDF, code, audio, and video;
- use optional teacher APIs without making them the system of record;
- plan and render media only with consent, provenance, and quality checks;
- support AI engineering and full-stack development through backups, tests, review, GitHub synchronization, and deployment preparation;
- enforce privacy engineering through local-first storage, masked secrets, explicit cloud gates, and audit trails; and
- show its limits honestly instead of producing placeholder work.

## Professional Capability Tracks

| Track | Practical Meaning | Near-Term Proof |
|---|---|---|
| Gima AI Engineer | Build, route, test, and evaluate local and cloud-assisted AI workflows. | Model-routing tests, provider fallback tests, capability dashboard, upgrade reports. |
| OSINT Research Architect | Turn public-source and authorized-scope research into cited tables, dossiers, source registers, and uncertainty notes. | Research report with sources, authorization gate, contradiction flags, CSV/PDF export, citation validation. |
| Privacy Engineer | Keep user data local by default and make cloud/network use explicit, auditable, and reversible. | `CLOUD_ALLOWED` gate, masked secrets, protected downloads, permission logs. |
| Full-Stack AI Builder | Connect backend services, browser UI, files, artifacts, APIs, GitHub, and deployment workflows into one usable product. | Working web UI, generated files, tested routes, GitHub sync, launch documentation. |

## Build Order

| Phase | Priority | Outcome | Main Work | Done When |
|---|---:|---|---|---|
| 1. Reliability Core | P0 | Gima starts, answers, and reports health clearly | Fix stale web process handling, brain readiness, launcher status, model timeout messages, provider health | `/api/status`, chat, brain search, and launcher pass repeatable smoke tests |
| 2. Real Artifact Engine | P0 | Tables and reports contain real data or ask for missing source | Source-aware table router, costing workbook builder, chart/JPG/PDF export, no fake placeholder tables | Ambiguous prompts ask clarifying data; researched prompts produce files with source register |
| 3. Memory and Learning | P0 | Gima continuously learns but keeps review control | Brain index refresh, source review queue, teacher cache, duplicate detection, stale memory correction | New learnings have source, status, timestamp, and can be approved/rejected |
| 4. GitHub and Recovery | P0 | Work can be safely shared and restored | GitHub auth guide, branch/commit/push helper, backup restore test, license/contribution docs | `confirm GitHub sync` creates a branch/PR after auth and backups restore cleanly |
| 5. Deep Research | P1 | Gima can produce cited research dossiers | Resumable research jobs, trusted-source ranking, claim-to-source mapping, contradiction notes, export bundle | A research request creates Markdown/PDF/CSV with citations and uncertainty flags |
| 5A. Authorized Research & Security Audit | P1 | Gima can help with safe public research and user-owned security review | Authorization gate, scope form, prohibited-action filter, responsible report template, private-report default | Security/reverse-engineering-style prompts ask the five gate questions before deeper work |
| 6. Advanced Sheets and Costing | P1 | Gima can do business-grade estimating | Editable assumptions, supplier quote fields, formulas, scenario tabs, charts, margins, taxes, sensitivity | Chicken sandwich and custom costing examples export correct Excel/JPG/PDF |
| 7. Image Power | P1 | Gima can understand, edit, and generate images through approved backends | Provider/local adapter, input/output manifest, prompt history, before/after previews, rights checks | Image edit request returns downloadable output and provenance manifest |
| 8. Video Song Director | P1 | Gima can make polished local music videos from images/audio | Beat/pitch analysis, scene planner, camera moves, emotion map, lyric captions, ffmpeg render templates, approved MusicGen/Suno-compatible/OpenRouter/ComfyUI API bridges | Image + MP3 request creates MP4, storyboard, timing map, eval report, and media API provenance when cloud is used |
| 9. Lip-Sync Rendering | P1 | Gima can plan and optionally render consented lip-sync | Consent gate, face/audio validation, segmenting, Wav2Lip/SadTalker-class adapter, drift eval | Lip-sync job creates render or explicit install instructions, never silent fake output |
| 10. Agent Workbench | P2 | Gima can manage multi-step goals safely | Plan/act/observe trace, task ledger, pause/resume, tool permissions, progress UI, completion tests | Long task survives restart and finishes only when tests pass |
| 11. Multimodal Understanding | P2 | Gima can reason over image, audio, video, and documents | VLM/video frame captioner, audio transcription timeline, document page citations, long-context chunking | Upload bundle QA cites exact file/page/frame/time |
| 12. Future Frontier Lab | P3 | Gima tracks future AI capabilities without overclaiming | Capability registry, frontier feature map, periodic public-source refresh, eval dashboard | UI shows capability status: done, started, planned, missing, with next action |
| 13. Growth Mode | P3 | Gima helps fund better hardware safely | Find useful paid work, build proposals, quote services, track upgrade fund, compare hardware | Gima prepares plans and files; user approves every public, financial, or purchase action |

## Immediate Sprint

The next sprint should be small and hard-edged:

1. Restart and verify the live web process so the interface uses the newest capability API.
2. Add a "System Doctor" button that runs health checks for brain, model, API keys, ffmpeg, ffprobe, GitHub CLI, and artifact folders.
3. Add an "Open Output Folder" action to every generated artifact card.
4. Make table/report prompts choose one of three paths: researched with sources, user-provided data, or clarification needed.
5. Add source registers to all generated Excel/PDF/JPG reports.
6. Add media manifests for every image, video, audio, and lip-sync output.
7. Run focused tests after each route change and store the result in `.human-ai/continuous/`.

## Capability Rules

Gima should use these labels consistently:

| Label | Meaning |
|---|---|
| Done | Implemented locally and covered by tests or a live smoke check |
| Started | Partial workflow exists, but quality, backend, or UI is incomplete |
| Planned | Design is stored, but no production workflow exists |
| Missing | Required local dependency, model, provider, permission, or auth is absent |

Never label a capability as done only because a prompt can describe it. File-producing and media features are done only when the generated file exists, downloads correctly, has a manifest, and passes a basic quality check.

## Evaluation Gates

Before claiming an upgrade, Gima should pass:

| Gate | Check |
|---|---|
| Health | Server starts, `/api/status` works, local model readiness is accurate |
| Truth | Current facts use internet or uploaded source data, not memory guesses |
| Artifact | Output files exist, open, and include provenance |
| Safety | Secrets are masked, paths are constrained, consent is recorded for people/voices/music |
| Recovery | Source backup and state snapshot exist before risky changes |
| Tests | Focused unit/API tests pass and failures are shown to the user |
| UX | Chat answer includes what was created, where it is, and what is still limited |

## Product Shape

The interface should make advanced AI feel practical:

- **Chat** for normal requests.
- **Tools** for explicit workflows: Research, Tables, Images, Audio Video, Lip-Sync, Coding, GitHub, Doctor.
- **Outputs** for generated files with Open, Download, Copy path, and Show manifest.
- **Memory** for search, source review, approval, deletion, and correction.
- **Capabilities** for the roadmap dashboard, not marketing claims.
- **Logs** for task traces, errors, and continuous learning history.

## Safe Self-Improvement

Gima can learn continuously. Gima should not silently modify live code continuously.

Code upgrades must follow this order:

1. Create source backup.
2. Create isolated working copy or branch.
3. Write plan and candidate files.
4. Apply patch.
5. Run focused tests.
6. Show diff and test result.
7. Ask for explicit sync/push approval.
8. Commit and push only after GitHub auth is healthy.

This keeps Gima improving without turning the local machine into an uncontrolled experiment.

## Growth Mode

Gima may help the project earn money and upgrade hardware, but only as an assistant. It can research opportunities, prepare quotes, create portfolio artifacts, draft LinkedIn posts, compare hardware, and maintain an upgrade-fund ledger.

Gima must not spend money, apply for credit, trade assets, subscribe to paid services, contact customers, post publicly, or order hardware without explicit user approval. This makes growth practical while keeping legal, financial, and identity decisions under human control.

See [`docs/GIMA_LEGAL_EARNING_PLAYBOOK.md`](/Users/gimhangunarathne/Documents/Gima/docs/GIMA_LEGAL_EARNING_PLAYBOOK.md) for the legal earning checklist, first service offers, and approval boundaries.

## Daily World-Class Loop

Every day Gima should produce a saved plan under `.human-ai/continuous/daily_plans/` with six tracks:

1. Reliability: doctor/status and hidden-error check.
2. Knowledge: one source-backed learning and brain rebuild.
3. Artifact: one real output bundle in `hands/out`.
4. Legal earning: one truthful, rights-safe earning asset.
5. Evaluation: focused tests or live smoke check.
6. Safe self-improvement: backup, copied work, diff, tests, approval.

The command is:

```bash
python3 -m human_ai.gima --config config.local.json daily-improvement-plan
```

The standard is simple: if Gima did not learn, build, test, log, and choose a next priority, it did not improve that day.

## First Success Demo

A strong public demo should be:

> "Create a researched costing table for 2,000 chicken sandwiches. Give me Excel, JPG, PDF, sources, assumptions, and a LinkedIn-ready summary."

Expected output:

- editable Excel workbook with formulas and assumptions;
- JPG preview of the table/chart;
- PDF report;
- source register;
- clear caveat that supplier quotes must be confirmed;
- output folder link in chat; and
- memory entry recording what was produced.

This demo is better than a vague "make Gima powerful" demo because it proves the full loop: request, research, calculation, file generation, provenance, memory, and shareable result.
