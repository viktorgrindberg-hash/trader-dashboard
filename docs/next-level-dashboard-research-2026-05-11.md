# Trader Dashboard Next-Level Research — 2026-05-11

## Executive direction
Build this as a **Trading Operations OS**, not a pretty dashboard. The winning pattern across modern trading journal/performance products is: calendar heatmap, equity curve, period P/L, strategy/engine breakdowns, trade replay/context, and broker/import integrations. Our unique edge should be unified automation governance: Alpaca engines + AIHF + XAU/MetaTrader + risk gates in one cockpit.

## Current dashboard audit
Strengths:
- Already has live Alpaca positions, orders, risk status, engine comparison, run monitor, journal health, governance, AIHF panel and chart drilldowns.
- Good base for safety: missing stops, crypto exposure, daily loss halt warnings.

Gaps fixed in this iteration:
- Added `analytics.json` with P/L by today/week/month/30D/all, per engine, hedge overlay, daily/weekly/monthly buckets, equity curve, win rate, profit factor and expectancy.
- Added `metatrader.json` from `C:\Users\vikto\metatradertest\bot_run.log` + `live_state.json`.
- Added dashboard UI section: **2027 Performance OS** with period tiles, daily P/L heatmap, equity curve, per-engine matrix and MT5 XAU bot card.

Remaining next-level opportunities:
1. Cross-filter everything: click losing day → filters engine, symbols, setup, session, trades and chart replays.
2. Add R-multiple analytics, max drawdown, time-of-day/session heatmaps and setup tags.
3. Add broker-source badges: Alpaca paper, AIHF paper, MT5 demo/live, simulator.
4. Add rulebook scoring: every trade gets plan adherence, risk compliance and exit-quality scores.
5. Add bot health timeline: heartbeat, signal, order attempt, broker accept/reject, P/L, risk state.
6. Add screenshot/chart replay archive around every entry/exit.

## Competitor pattern notes
- PnLGrid emphasizes P&L calendar heatmap, equity curve, win rate, profit factor, daily journal and fast import.
- TradeMetricX emphasizes dashboard KPIs, cumulative performance, P&L calendar, notes/mood, strategy analytics, replay and market news.
- P&L Ledger emphasizes week/month/year/all-time summaries, drawdown, win rate, profit factor and expectancy.
- TradeFXBook emphasizes MT5 sync, backtesting, equity curves, calendar heatmaps, session/symbol/tag breakdowns, risk/reward and replay.
- TraderLytix emphasizes cross-filter analytics: click a losing pattern and all widgets update.
- TradingView remains the benchmark for charts/replay/multi-asset workflows, but user chatter still points to portfolio monitoring/broker integration gaps.

## Design principles for our 2027 version
- **Decision latency first:** Can Viktor answer “what is hurting/helping now?” in 5 seconds?
- **Risk before beauty:** P/L is secondary to max loss, stop coverage, exposure, stale bots and broker rejects.
- **Automation transparency:** Every engine/bot should explain: last run, last signal, why no trade, last order result, current block.
- **One timeline:** Signals, orders, fills, exits, alerts and cron runs should be stitched chronologically.
- **Drilldown without page hopping:** Summary → engine → day → trade → chart/replay in one surface.

## Sources used
- PnLGrid: https://pnlgrid.com/
- TradeMetricX: https://www.trademetricx.com/
- P&L Ledger: https://www.pnlledger.com/
- TradingView Features: https://www.tradingview.com/features/
- TrackEdge: https://www.trackedge.org/
- TradeFXBook: https://www.tradefxbook.com/
- TraderLytix: https://www.traderlytix.com/
