# Trader Dashboard

Cloud-hostable 24/7 dashboard scaffold for `trader.nordgrindberg.com`.

## Goal
A durable internet-facing dashboard that stays online even when the local trading PC is off.

## Recommended architecture
- **Frontend hosting:** Cloudflare Pages
- **Repo hosting:** GitHub
- **Always-on data generator:** small VPS / cloud cron job
- **Domain:** `trader.nordgrindberg.com`

## Why
If the PC is off, the PC cannot be the live data source. The dashboard and the exporter must live in the cloud.

## Folder layout
- `dashboard/site/` static frontend
- `dashboard/data/` generated JSON snapshots for local preview
- `dashboard/docs/` deployment and DNS notes
- `dashboard/scripts/` export/build helpers

## MVP data files
- `overview.json`
- `engines.json`
- `trades.json`
- `periods.json`
- `health.json`
- `status.json`

## Suggested live flow
1. A cloud job runs every 1-5 minutes.
2. It reads Alpaca + local exported journal/state snapshots.
3. It writes JSON into the deployed site or object storage.
4. Cloudflare Pages serves the frontend from `trader.nordgrindberg.com`.

## Local build
```powershell
python dashboard\scripts\build_dashboard_data.py
```

Then open:
- `dashboard/site/index.html`

## Deploy options
### Best long-term
Cloudflare Pages + GitHub + VPS/cloud exporter.

### Fast prototype
Lovable for frontend, but keep the data/export layer outside Lovable.
