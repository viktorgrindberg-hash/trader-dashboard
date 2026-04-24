#!/usr/bin/env python3
import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / 'data'
STATUS_JSON = BASE_DIR / 'temp' / 'status' / 'trading-stack-status.json'
HEALTH_JSON = DATA_DIR / 'engine-health-report.json'
OUT_DIR = BASE_DIR / 'dashboard' / 'data'
SITE_DATA_DIR = BASE_DIR / 'dashboard' / 'site' / 'data'
CET = ZoneInfo('Europe/Stockholm')

ENGINE_LABELS = {
    'A': 'Engine A',
    'B': 'Engine B',
    'C': 'Engine C ORB',
    'D': 'Crypto 24/7',
    'daytrading': 'Daytrading',
    'crypto_24_7': 'Crypto 24/7',
    'engine_c_orb': 'Engine C ORB',
    'JOHN': 'Crypto John',
    'crypto_john': 'Crypto John',
}


def read_json(path, default):
    if not path.exists():
        return default
    with open(path, 'r', encoding='utf-8-sig') as f:
        return json.load(f)


def parse_dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00')).astimezone(CET)
    except Exception:
        return None


def trade_engine(trade):
    engine = trade.get('engine') or trade.get('trade_mode') or trade.get('engine_name') or 'unknown'
    return str(engine)


def pnl_of(trade):
    return float(trade.get('realized_pnl') or trade.get('pnl') or 0)


def status_of_trade(trade):
    return str(trade.get('status') or '').lower()


def load_trades():
    journal = read_json(DATA_DIR / 'trade-journal.json', {})
    return journal.get('trades', []) if isinstance(journal, dict) else []


def period_start(now):
    return {
        'day': now.date(),
        'week': (now - timedelta(days=now.weekday())).date(),
        'month': now.date().replace(day=1),
    }


def summarize_periods(trades):
    now = datetime.now(CET)
    starts = period_start(now)
    out = {
        'day': {'pnl': 0.0, 'trades': 0, 'wins': 0},
        'week': {'pnl': 0.0, 'trades': 0, 'wins': 0},
        'month': {'pnl': 0.0, 'trades': 0, 'wins': 0},
    }
    for t in trades:
        if status_of_trade(t) == 'open':
            continue
        dt = parse_dt(t.get('timestamp_exit') or t.get('timestamp_entry'))
        if not dt:
            continue
        pnl = pnl_of(t)
        d = dt.date()
        for key, start in starts.items():
            if d >= start:
                out[key]['pnl'] += pnl
                out[key]['trades'] += 1
                if pnl > 0:
                    out[key]['wins'] += 1
    for bucket in out.values():
        trades_n = bucket['trades']
        bucket['win_rate'] = round((bucket['wins'] / trades_n * 100), 1) if trades_n else 0.0
        bucket['pnl'] = round(bucket['pnl'], 2)
    return out


def summarize_engines(trades, health):
    grouped = defaultdict(lambda: {'engine': '', 'trades': 0, 'open': 0, 'wins': 0, 'pnl': 0.0, 'last_trade_at': None})
    for t in trades:
        engine = trade_engine(t)
        row = grouped[engine]
        row['engine'] = engine
        row['trades'] += 1
        if status_of_trade(t) == 'open':
            row['open'] += 1
        else:
            pnl = pnl_of(t)
            row['pnl'] += pnl
            if pnl > 0:
                row['wins'] += 1
        dt = parse_dt(t.get('timestamp_exit') or t.get('timestamp_entry'))
        if dt and (row['last_trade_at'] is None or dt > row['last_trade_at']):
            row['last_trade_at'] = dt

    health_map = {}
    if isinstance(health, dict):
        for section in ('engines', 'engine_health', 'ranked_engines'):
            if isinstance(health.get(section), list):
                for item in health[section]:
                    key = str(item.get('engine') or item.get('name') or '')
                    if key:
                        health_map[key] = item

    rows = []
    for engine, row in grouped.items():
        closed = max(row['trades'] - row['open'], 0)
        wr = round((row['wins'] / closed * 100), 1) if closed else 0.0
        h = health_map.get(engine, {})
        rows.append({
            'engine': engine,
            'label': ENGINE_LABELS.get(engine, engine),
            'trades': row['trades'],
            'closed_trades': closed,
            'open_positions': row['open'],
            'win_rate': wr,
            'pnl': round(row['pnl'], 2),
            'health_state': h.get('state') or h.get('health_state') or 'unknown',
            'size_multiplier': h.get('size_multiplier'),
            'last_trade_at': row['last_trade_at'].isoformat() if row['last_trade_at'] else None,
        })
    rows.sort(key=lambda x: (x['pnl'], x['win_rate']), reverse=True)
    return rows


def summarize_recent_trades(trades, limit=50):
    closed = []
    for t in trades:
        dt = parse_dt(t.get('timestamp_exit') or t.get('timestamp_entry'))
        if not dt:
            continue
        closed.append({
            'engine': trade_engine(t),
            'label': ENGINE_LABELS.get(trade_engine(t), trade_engine(t)),
            'symbol': t.get('symbol'),
            'side': t.get('side') or t.get('direction'),
            'status': t.get('status'),
            'pnl': round(pnl_of(t), 2),
            'entry_price': t.get('entry_price'),
            'exit_price': t.get('exit_price') or t.get('close_price'),
            'timestamp': dt.isoformat(),
            'reason': t.get('close_reason') or t.get('exit_reason') or '',
        })
    closed.sort(key=lambda x: x['timestamp'], reverse=True)
    return closed[:limit]


def summarize_health(health):
    if not isinstance(health, dict):
        return {'leaders': [], 'paused': [], 'cooldown': []}
    setups = []
    for section in ('setups', 'setup_health', 'ranked_setups'):
        if isinstance(health.get(section), list):
            setups = health[section]
            break
    leaders, paused, cooldown = [], [], []
    for item in setups:
        state = item.get('state') or item.get('health_state')
        packed = {
            'engine': item.get('engine'),
            'setup': item.get('setup') or item.get('setup_name'),
            'state': state,
            'pnl': item.get('pnl'),
            'win_rate': item.get('win_rate'),
            'size_multiplier': item.get('size_multiplier'),
        }
        if state == 'leader':
            leaders.append(packed)
        elif state == 'paused':
            paused.append(packed)
        elif state == 'cooldown':
            cooldown.append(packed)
    return {'leaders': leaders[:10], 'paused': paused[:10], 'cooldown': cooldown[:10]}


def build():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SITE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    trades = load_trades()
    status = read_json(STATUS_JSON, {})
    health = read_json(HEALTH_JSON, {})
    daily = read_json(DATA_DIR / 'daily-state.json', {})

    overview = {
        'generated_at': datetime.now(CET).isoformat(),
        'portfolio_value': daily.get('portfolio_value_current'),
        'daily_pnl': daily.get('daily_pnl'),
        'trades_today': daily.get('trades_today'),
        'stack_status': status,
    }

    outputs = {
        'overview.json': overview,
        'engines.json': summarize_engines(trades, health),
        'trades.json': summarize_recent_trades(trades),
        'periods.json': summarize_periods(trades),
        'health.json': summarize_health(health),
        'status.json': status,
    }

    for filename, payload in outputs.items():
        for out_dir in (OUT_DIR, SITE_DATA_DIR):
            with open(out_dir / filename, 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f'Wrote {len(outputs)} dashboard data files to {OUT_DIR} and {SITE_DATA_DIR}')


if __name__ == '__main__':
    build()
