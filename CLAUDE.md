# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Litterbot-wrapped is a "Spotify Wrapped"-style visualization for Litter-Robot data. It shows weekly stats about your cat's litter box usage in a fun, interactive slideshow format.

## Architecture

The site uses a **decoupled data/presentation** architecture:

- **`fetch_data.py`** - Fetches data from Litter-Robot API, computes stats, saves to `site/data.json`
- **`site/index.html`** - Static HTML template that fetches `data.json` at runtime and renders via JavaScript
- **`build_serve.py`** - Local dev helper: fetches data and serves the site (use `--build-only` to skip serving)

### Automated Data Updates

GitHub Actions runs `fetch_data.py` every 4 hours and commits updated `data.json` to main. Netlify auto-deploys when the repo changes.

## Development Commands

```bash
# Install dependencies
uv sync

# Local development (fetches data, opens browser, serves site)
uv run python build_serve.py

# Build only (fetch data, no server)
uv run python build_serve.py --build-only

# Fetch data only (used by CI)
uv run python fetch_data.py
```

## Environment Variables

Required secrets (set in `.env` locally, GitHub Secrets for CI):
- `LITTERBOT_USERNAME` - Litter-Robot account email
- `LITTERBOT_PASSWORD` - Litter-Robot account password
- `CAT_NAME` - Your cat's name (optional, defaults to "Kitty")

## Dependencies

- Python 3.13+
- pylitterbot (>=2025.0.0) - async library for Litter-Robot API interaction
- Uses uv for package management
