# Litterbot Wrapped

A "Spotify Wrapped"-style dashboard for your Litter-Robot, displaying your cat's litter box activity stats, weight trends, and visit patterns. Includes a web dashboard and TRMNL e-ink display layouts.

## Overview

This project connects to the Litter-Robot API to fetch activity history and generates:
- A web-based dashboard with animated slides showing stats and charts
- TRMNL e-ink display layouts in multiple sizes for ambient monitoring

### Features

- **Visit tracking**: Daily visit counts, visits per day average, peak hours
- **Weight monitoring**: Average weight, min/max, trend detection (gaining/losing/stable)
- **Timing analysis**: Longest and shortest gaps between visits
- **Personality traits**: Fun categorizations like "Night Owl", "Early Bird", "Creature of Habit"
- **Charts**: Visual visit history and weight trends over time

## Architecture

The system uses a decoupled architecture separating data fetching from presentation:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  GitHub Actions │────▶│   Litter-Robot  │────▶│   site/data.json│
│  (scheduled)    │     │   API           │     │   (committed)   │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                        ┌────────────────────────────────┼────────────────────────────────┐
                        │                                │                                │
                        ▼                                ▼                                ▼
               ┌─────────────────┐              ┌─────────────────┐              ┌─────────────────┐
               │     Netlify     │              │      TRMNL      │              │   JSON Endpoint │
               │   Web Dashboard │              │  E-ink Display  │              │   (data feed)   │
               └─────────────────┘              └─────────────────┘              └─────────────────┘
```

### Services Used

#### GitHub Actions
- **Purpose**: Automated data fetching on a schedule
- **Schedule**: Runs every 4 hours via cron (`0 */4 * * *`)
- **Workflow**: `.github/workflows/fetch-data.yml`
- **Environment**: Uses `litterbot-fetch` environment for secrets
- **Process**:
  1. Checks out repository
  2. Installs Python 3.13 and dependencies via `uv`
  3. Runs `fetch_data.py` to pull data from Litter-Robot API
  4. Commits updated `site/data.json` if changed
  5. Triggers Netlify deploy via build hook

#### Netlify
- **Purpose**: Hosts the static web dashboard
- **Publish directory**: `site/`
- **Features**:
  - Static file hosting for `index.html` and assets
  - Serves `data.json` as a public JSON endpoint
  - Auto-deploys when triggered by GitHub Actions via build hook

#### TRMNL
- **Purpose**: E-ink dashboard display for ambient monitoring
- **Data source**: Fetches JSON from the Netlify-hosted `data.json` endpoint
- **Templating**: Uses Liquid templating to render data
- **Charts**: Highcharts via TRMNL's CDN for visit and weight visualizations

## Project Structure

```
litterbot-wrapped/
├── fetch_data.py              # Data fetching and stats computation
├── site/
│   ├── index.html             # Web dashboard (static HTML + JS)
│   ├── data.json              # Generated stats (auto-updated)
│   └── icon.png               # Site icon
├── trmnl/
│   ├── trmnl-full.html        # Full-size TRMNL layout (800x480)
│   ├── trmnl-half-horizontal.html  # Half-horizontal (800x240)
│   ├── trmnl-half-vertical.html    # Half-vertical (400x480)
│   └── trmnl-quad.html        # Quadrant size (400x240)
├── .github/
│   └── workflows/
│       └── fetch-data.yml     # GitHub Actions workflow
├── pyproject.toml             # Python dependencies
└── CLAUDE.md                  # Development instructions
```

## Setup

### Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) package manager
- Litter-Robot account with connected device
- GitHub repository
- Netlify account (for web hosting)
- TRMNL device (optional, for e-ink display)

### Local Development

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/litterbot-wrapped.git
   cd litterbot-wrapped
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

3. Create a `.env` file with your credentials:
   ```
   LITTERBOT_USERNAME=your-email@example.com
   LITTERBOT_PASSWORD=your-password
   CAT_NAME=YourCatsName
   ```

4. Fetch data locally:
   ```bash
   uv run python fetch_data.py
   ```

5. Serve the site locally (optional):
   ```bash
   cd site && python -m http.server 8000
   ```

### GitHub Actions Setup

1. Create a GitHub environment named `litterbot-fetch`

2. Add the following secrets to the environment:
   - `LITTERBOT_USERNAME` - Your Litter-Robot account email
   - `LITTERBOT_PASSWORD` - Your Litter-Robot account password
   - `CAT_NAME` - Your cat's name (displayed on dashboard)
   - `NETLIFY_BUILD_HOOK` - Netlify build hook URL for triggering deploys

3. The workflow will run automatically every 4 hours, or trigger manually via "Run workflow"

### Netlify Setup

1. Connect your GitHub repository to Netlify

2. Configure build settings:
   - **Publish directory**: `site`
   - **Build command**: (none needed, static files only)

3. Create a build hook:
   - Go to Site settings > Build & deploy > Build hooks
   - Create a hook named "GitHub Actions trigger"
   - Copy the URL and add it as the `NETLIFY_BUILD_HOOK` secret in GitHub

### TRMNL Setup

1. In the TRMNL app, create a new Private Plugin

2. Configure the plugin:
   - **Strategy**: Polling
   - **Polling URL**: `https://your-netlify-site.netlify.app/data.json`
   - **Polling Interval**: 4 hours (to match GitHub Actions schedule)

3. Copy the appropriate layout HTML from `trmnl/` based on your desired display size:
   - `trmnl-full.html` - Full screen (800x480)
   - `trmnl-half-horizontal.html` - Wide banner (800x240)
   - `trmnl-half-vertical.html` - Tall sidebar (400x480)
   - `trmnl-quad.html` - Quarter screen (400x240)

4. Paste the HTML into the plugin's markup editor

## Data Structure

The `data.json` file contains:

```json
{
  "cat_name": "Saba",
  "robot_name": "scoopy",
  "generated_at": "2026-01-03T16:16:15.052321-08:00",
  "date_range": {
    "start": "Dec 27",
    "end": "Jan 03, 2026",
    "display": "Dec 27 - Jan 03, 2026"
  },
  "personality_traits": ["Early Bird", "Weekday Regular"],
  "total_visits": 21,
  "visits_per_day": 3.1,
  "chart_data": [
    { "weekday": "Sat", "display": "12/27", "count": 1 }
  ],
  "weight_history": [
    { "display": "12/27", "weight": 11.2 }
  ],
  "timing": {
    "longest_gap": "15h 56m",
    "shortest_gap": "2h 19m"
  },
  "weight": {
    "average": 11.3,
    "min": 10.5,
    "max": 12.3,
    "trend": "gaining",
    "change": 0.12
  },
  "peak_hour": {
    "hour": 11,
    "count": 3,
    "display": "11:00 AM"
  },
  "robot_stats": {
    "clean_cycles": 21,
    "interruptions": 3
  }
}
```

## Dependencies

- [pylitterbot](https://github.com/natekspencer/pylitterbot) - Async Python library for Litter-Robot API
- [python-dotenv](https://github.com/theskumar/python-dotenv) - Environment variable management

## License

MIT
