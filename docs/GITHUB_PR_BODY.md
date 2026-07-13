## Summary

- expands Gima's local-first memory, research, artifact, media, and review-gated improvement workflows
- adds deployment and launcher support, safety controls, and broader regression coverage
- publishes the technical white paper source and LinkedIn sharing guide

## Verification

- 163 repository tests executed locally
- 149 passed inside the restricted workspace sandbox
- 13 localhost server tests were blocked by socket permissions
- 1 macOS `sandbox-exec` test was blocked by the host test environment
- DOCX and PDF white-paper exports rendered and visually inspected across nine pages

## Publishing Notes

- generated artifacts under `outputs/` are intentionally excluded from Git
- local API credentials, model files, memory, and runtime state remain excluded
- the repository is public but does not currently include a software license
