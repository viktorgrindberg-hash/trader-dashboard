# Automation plan

## What is already automated locally
- `dashboard/scripts/build_dashboard_data.py` turns live trader data into deployable JSON snapshots.
- `dashboard/site/index.html` reads those JSON files directly.

## What should be automated next
### 1. Cloud build/deploy
Whenever dashboard code changes:
- rebuild dashboard JSON
- deploy `dashboard/site`

### 2. Recurring refresh
On an always-on host:
- run exporter every 1-5 minutes
- publish updated JSON snapshots

## Best automation path
### Path A, strongest
- GitHub repo
- Cloudflare Pages
- VPS cron job for exporter

### Path B, lighter
- GitHub repo
- Cloudflare Pages
- GitHub Actions scheduled exporter

## Required secrets outside this machine
- GitHub access token or logged-in GitHub CLI
- Cloudflare API token
- Cloudflare account id
- Cloudflare zone id or Pages project access
- Alpaca paper keys on exporter host

## Important
This current machine does **not** have `git`, `gh`, or visible GitHub/Cloudflare env tokens available right now, so full remote automation cannot be completed from here until credentials/tooling exist.
