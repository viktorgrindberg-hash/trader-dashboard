# Engine Scaling Plan — 2026-05-11

## Position
Do **not** scale leverage globally yet. Current system is still in paper/diagnostic phase and several engines have unresolved state/quality issues. Scale quality and observability first, then notional.

## Risk ladder

### Level 0 — Diagnostics only
Use when an engine is paused, stale, has mapping issues, missing stops, or no clear positive expectancy.
- Size: $0 live-paper new entries, scans allowed
- Required: diagnostics JSON, last run/signal/block reason
- Engines now: Engine A until canary is explicitly enabled

### Level 1 — Canary paper
Use when engine has a plausible edge but insufficient recent evidence.
- Max 1 trade/day
- Max 0.10% account risk per trade
- Max 1 open position per engine
- No leverage
- Must have stop/kill criteria
- Graduate after 20 closed trades with positive expectancy and max drawdown < 2R cluster

### Level 2 — Standard paper
- 0.25% to 0.50% account risk per trade
- Max 3 open positions per engine
- Correlation cap across same theme/symbol bucket
- No leverage unless portfolio drawdown < 3% and 30D profit factor > 1.3

### Level 3 — Scaled paper
- 0.50% to 1.00% risk per trade
- Only engines with 50+ recent trades or robust out-of-sample evidence
- Requires stop coverage, daily loss halt, engine health not paused/throttled

### Level 4 — Leverage / margin
Not recommended now. Only consider after:
- 3 consecutive profitable months
- 30D profit factor > 1.5
- max drawdown controlled below 5%
- no stale journal/broker mismatches
- broker-native/software stops verified
- correlation overlay active

## Engine-specific next steps

### Engine A
Current state: paused by health/Kelly. It finds signals, but Kelly size returns $0 after weak historical A performance.
Next: keep paused or enable Level 1 canary only after final review. Do not leverage.

### Engine B
Current state: gets signals but execution is vetoed by risk/edge/LLM/filters.
Next: add B diagnostics similar to Engine A. Find exact veto categories before changing size.

### Engine C ORB
Current state: best current performer in May.
Next: do not blindly leverage. Consider Level 2 standard paper if stop coverage and correlation are clean.

### Engine D Scanner
Current state: few May trades, positive but small sample.
Next: keep canary/standard paper, collect more data.

### Crypto 24/7
Current state: open journal positions make closed P/L look flat.
Next: reconcile open positions/exits before scaling. Crypto exposure hard cap remains 15%.

### Crypto John
Current state: active and profitable month so far, but crypto correlation risk is high.
Next: keep under crypto exposure cap, avoid leverage.

### XAU Grid / MT5 XAU
Current state: XAU grid recovering; MT5 bot blocked by AutoTrading disabled.
Next: integrate bot telemetry and keep demo/paper until stop/exposure rules are verified.

## Core rule
Scale **risk-adjusted edge**, never scale just because a bot is active. If the dashboard cannot explain why an engine did or did not trade, the engine does not deserve leverage.
