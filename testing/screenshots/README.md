# README screenshots

Reusable harness that regenerates the product screenshots in `docs/images/` by
driving the **real** TrinoHub UI. It reuses the end-to-end test harness
(`testing/harness.py`), so it launches a genuine `TrinoHubApp` backed by an
in-memory fake AWS and a fake Trino engine — **no cloud resources, no real
coordinator, no API keys.**

## Usage

```bash
# Capture every view into testing/screenshots/out/ (staging, git-ignored):
.venv/bin/python testing/screenshots/capture.py

# Capture a subset (substring match on the capture names):
.venv/bin/python testing/screenshots/capture.py clusters sql-editor notebook

# Sanity-check the seed data without a browser:
.venv/bin/python testing/screenshots/seed.py
```

Review the PNGs in `out/`, then copy the good ones into `docs/images/` and
update the gallery in the top-level `README.md`.

## Files

- `seed.py` — builds and fully seeds the demo control plane (clusters, catalogs,
  query history, a notebook, scheduled jobs, users) and returns richer,
  presentation-quality result sets for a few demo queries.
- `capture.py` — serves the seeded app under uvicorn and drives Google Chrome
  via Playwright at a retina 1440×900 viewport (2880×1800 output).
- `out/` — staging output; not committed.

## Requirements

- The project virtualenv with `playwright` installed (`.venv/bin/python`).
- Google Chrome at `/usr/bin/google-chrome` (Playwright launches with
  `channel="chrome"`).

## Notes

- **Ask Trino** (`12-ask-trino.png`) is not regenerated here: it needs a live
  LLM key (`OPENROUTER_API_KEY`) to produce SQL. Capture it manually against a
  configured instance when the UI changes.
- The demo uses only the two instance types the harness enables
  (`r7i.xlarge`, `r7i.2xlarge`); adjust `seed.py` if you enable more.
