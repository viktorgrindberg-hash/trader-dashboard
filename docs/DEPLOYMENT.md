# Deployment plan for trader.nordgrindberg.com

## Recommended stack
- **Frontend:** Cloudflare Pages
- **Source control:** GitHub repo
- **Data exporter:** small VPS, GitHub Action on schedule, or another always-on worker
- **DNS:** Cloudflare DNS or your current DNS provider

## Architecture
### Tier 1, static dashboard
The dashboard itself is static HTML/CSS/JS and can be served globally.

### Tier 2, data snapshots
A recurring exporter updates JSON files:
- account / equity
- open positions
- open orders
- engine ranking
- daily / weekly / monthly metrics
- latest trades
- health states

### Tier 3, secret handling
Alpaca keys must stay server-side only.
Never expose them in frontend JS.

## Best path
### Option A, recommended
- Push dashboard code to GitHub
- Connect repo to Cloudflare Pages
- Run exporter on a VPS every 1-5 minutes
- Exporter writes JSON snapshots to repo artifact storage, object storage, or deploy branch

### Option B, lower ops
- Cloudflare Pages for UI
- GitHub Actions scheduled exporter if rate/update requirements are light
- Good for every 5-15 minutes, less ideal for near-live

### Option C, Lovable
- Use Lovable to build UI quickly
- Still host real data pipeline separately
- Good for prototyping, not sufficient by itself for durable live data

## DNS
Create a custom hostname:
- `trader.nordgrindberg.com`

If using Cloudflare Pages, connect the custom domain in Pages settings and point DNS as instructed by Cloudflare.

## MVP release checklist
1. Create GitHub repo for dashboard
2. Connect repo to Cloudflare Pages
3. Add custom domain `trader.nordgrindberg.com`
4. Move exporter to an always-on host
5. Store Alpaca secrets only on exporter host
6. Publish JSON snapshots
7. Point frontend to snapshot URLs
8. Add uptime monitoring

## Future upgrades
- auth gate / password
- private P/L views
- websocket or SSE updates
- trade detail drill-down
- engine regime panels
- correlation / exposure map
