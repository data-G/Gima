# LinkedIn Sharing Guide for the Gima White Paper

## Recommended document title

**Gima: A Local-First, Review-Gated Personal AI Workspace**

## Ready-to-post caption

I have been building Gima, an experimental local-first personal AI workspace.

The project explores a simple but important question: can a personal AI keep durable memory, create useful files and media, learn continuously, and improve its software while the user remains in control?

The new white paper documents the architecture behind Gima:

- readable local memory and retrieval;
- a local 4B model with optional online AI teachers;
- deterministic spreadsheet, document, media, and coding workflows;
- AI engineering, OSINT research architecture, privacy engineering, and full-stack product capabilities;
- bounded daily learning with versioned continuity snapshots;
- isolated self-update copies, tests, approval, and rollback; and
- the current evidence, limitations, and roadmap.

This is an engineering work in progress, not a claim of consciousness or unrestricted autonomy. My focus is practical capability with visible data, measurable tests, and human-controlled upgrades.

Repository: https://github.com/data-G/Gima

I would value feedback from people working on local-first software, AI agents, retrieval systems, OSINT research, privacy engineering, multimodal tools, and responsible full-stack AI products.

#GimaAI #AIEngineer #OSINT #ResearchArchitecture #PrivacyEngineering #FullStackAI #AIEngineering #LocalFirst #ResponsibleAI #Python #BuildInPublic

## How to publish it

First, authenticate and sync the prepared source branch from Terminal:

```bash
cd /Users/gimhangunarathne/Documents/Gima
gh auth login
./scripts/github_sync_gima.sh
```

1. Open LinkedIn and select **Start a post**.
2. Choose **More**, then **Add a document**.
3. Upload `Gima_Local_First_AI_White_Paper.pdf`.
4. Use the recommended document title above.
5. Paste the caption, personalize the opening sentence if desired, and preview every page.
6. Confirm the repository is ready for public visitors, then publish.

LinkedIn currently supports PDF, DOC/DOCX, PPT/PPTX document posts up to 100 MB and 300 pages. LinkedIn recommends PDF for upload quality, a clear document title, consistent page sizes, flattened layers, and secure hyperlinks: https://www.linkedin.com/help/linkedin/answer/a518909/upload-and-share-documents-on-linkedin

## Before publishing

- Add a software license if you want others to reuse or contribute code. A public repository without a license is visible, but reuse rights are not automatically granted.
- Confirm no private keys, personal files, runtime memory, faces, or copyrighted media are committed.
- Make sure the GitHub pull request is merged, or link directly to the published branch/PR while it is under review.
- Review the PDF once more because LinkedIn does not let you replace the document inside an existing post.
