#!/usr/bin/env python3
import json
import os
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
import re

REPO_DIR = Path(__file__).resolve().parents[1]
WORKSPACE_DIR = REPO_DIR.parent
LOCAL_DATA_DIR = WORKSPACE_DIR / 'data'
REPO_DATA_DIR = REPO_DIR / 'data'
DATA_DIR = LOCAL_DATA_DIR if (LOCAL_DATA_DIR / 'trade-journal.json').exists() else REPO_DATA_DIR
STATUS_JSON = WORKSPACE_DIR / 'temp' / 'status' / 'trading-stack-status.json'
HEALTH_JSON = DATA_DIR / 'engine-health-report.json'
AIHF_JSON = LOCAL_DATA_DIR / 'ai-hedge-fund-committee-scan.json'
AIHF_BLIND_JSON = LOCAL_DATA_DIR / 'ai-hedge-fund-committee-blind.json'
AIHF_PORTFOLIO_JSON = LOCAL_DATA_DIR / 'aihf-paper-portfolio.json'
AIHF_ALPACA_STATE_JSON = LOCAL_DATA_DIR / 'aihf-alpaca-paper-state.json'
MT5_DIR = Path(r'C:\Users\vikto\metatradertest')
OUT_DIR = REPO_DATA_DIR
SITE_DATA_DIR = REPO_DIR / 'site' / 'data'
CET = ZoneInfo('Europe/Stockholm')

ENGINE_LABELS = {
    'A': 'Engine A, Multi-Signal',
    'B': 'Engine B, Scalper',
    'C': 'Engine C, ORB',
    'D': 'Engine D, Volume Scanner',
    'daytrading': 'Daytrading Engine',
    'crypto_24_7': 'Crypto 24/7',
    'crypto': 'Crypto 24/7',
    'engine_c_orb': 'Engine C, ORB',
    'engine_d_volume': 'Engine D, Volume Scanner',
    'JOHN': 'Crypto John',
    'crypto_john': 'Crypto John Live',
    'xau_grid': 'XAU Grid',
    'metatrader_xau': 'MetaTrader XAU Bot',
}

CONFIGURED_ENGINES = [
    {'key': 'A', 'label': 'Engine A', 'channel': '#engine-a', 'script': 'engine-a-multisignal.py', 'cadence': '5 min market hours', 'status': 'active'},
    {'key': 'B', 'label': 'Engine B', 'channel': '#engine-b', 'script': 'engine-b-scalper.py', 'cadence': '5 min market hours', 'status': 'active'},
    {'key': 'daytrading', 'label': 'Daytrading', 'channel': '#engine-daytrading', 'script': 'daytrading-engine.py', 'cadence': '5 min market hours', 'status': 'active'},
    {'key': 'C', 'label': 'Engine C ORB', 'channel': '#engine-c-orb', 'script': 'engine-c-orb.py', 'cadence': '5 min market hours', 'status': 'active'},
    {'key': 'D', 'label': 'Engine D Scanner', 'channel': '#engine-d-scanner', 'script': 'engine-d-volume.py', 'cadence': '5 min market hours', 'status': 'active'},
    {'key': 'crypto_24_7', 'label': 'Crypto 24/7', 'channel': '#engine-crypto', 'script': 'crypto-engine.py', 'cadence': '15 min 24/7', 'status': 'active'},
    {'key': 'crypto_john', 'label': 'Crypto John Live', 'channel': '#engine-john', 'script': 'crypto-engine-john-live.py', 'cadence': '15 min 24/7', 'status': 'active'},
    {'key': 'xau_grid', 'label': 'XAU Grid', 'channel': '#engine-xau-grid', 'script': 'xau-grid-engine.py', 'cadence': '5 min weekdays', 'status': 'active'},
    {'key': 'metatrader_xau', 'label': 'MT5 XAUUSD Bot', 'channel': '#engine-xau-grid', 'script': r'C:\\Users\\vikto\\metatradertest\\run_live.py', 'cadence': '24/5 launcher', 'status': 'external'},
]


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
    mode = str(trade.get('trade_mode') or '')
    raw = str(mode or trade.get('engine') or trade.get('engine_name') or 'unknown')
    aliases = {
        'JOHN': 'crypto_john',
        'Crypto John': 'crypto_john',
        'Crypto John Live': 'crypto_john',
        'crypto-john': 'crypto_john',
        'Crypto Engine': 'crypto_24_7',
        'Crypto 24/7': 'crypto_24_7',
        'crypto': 'crypto_24_7',
        'engine_d_volume': 'D',
        'engine_d_vol': 'D',
        'Engine D, Volume Scanner': 'D',
        'engine_a_multisignal': 'A',
        'Multi-Signal': 'A',
        'engine_c_orb': 'C',
        'Engine C, ORB': 'C',
        'Daytrading Engine': 'daytrading',
    }
    return aliases.get(raw, raw)



def health_for_engine(health, engine):
    if not isinstance(health, dict):
        return {}
    engines = health.get('engines') or {}
    aliases = {
        'A': ['A','engine_a_multisignal'],
        'B': ['B'],
        'C': ['C','engine_c_orb'],
        'D': ['D','engine_d_vol','engine_d_volume'],
        'daytrading': ['daytrading'],
        'crypto_24_7': ['crypto_24_7','crypto'],
        'crypto_john': ['crypto_john','JOHN'],
        'xau_grid': ['xau_grid'],
        'metatrader_xau': ['metatrader_xau'],
    }.get(engine, [engine])
    for key in aliases:
        if key in engines:
            return engines[key]
    return {}

def engine_explanation(cfg, h, row):
    if row.get('open', 0) > 0:
        return 'Has live position now'
    health = h.get('health')
    if health == 'paused' or float(h.get('size_multiplier') or 1) == 0:
        return 'Auto-paused by health/edge'
    if not row.get('last_trade_at'):
        return 'No trade yet'
    return 'No open trade, waiting for signal'

def pnl_of(trade):
    return float(trade.get('realized_pnl') or trade.get('pnl') or 0)

def r_multiple_of(trade):
    pnl = pnl_of(trade)
    try:
        entry=float(trade.get('entry_price') or 0); stop=float(trade.get('stop_loss') or 0); qty=abs(float(trade.get('qty') or 0))
        risk=abs(entry-stop)*qty
        if risk>0: return pnl/risk
    except Exception:
        pass
    return None


def status_of_trade(trade):
    return str(trade.get('status') or '').lower()


def load_trades():
    journal = read_json(DATA_DIR / 'trade-journal.json', {})
    return journal.get('trades', []) if isinstance(journal, dict) else []


def alpaca_headers():
    key = os.getenv('ALPACA_KEY') or os.getenv('APCA_API_KEY_ID')
    secret = os.getenv('ALPACA_SECRET') or os.getenv('APCA_API_SECRET_KEY')
    cred_path = WORKSPACE_DIR.parents[1] / '.credentials' / 'alpaca-paper.json'
    if (not key or not secret) and cred_path.exists():
        creds = read_json(cred_path, {})
        key = key or creds.get('key_id')
        secret = secret or creds.get('secret_key')
    if not key or not secret:
        return None
    return {'APCA-API-KEY-ID': key, 'APCA-API-SECRET-KEY': secret}


def alpaca_get(path, default):
    headers = alpaca_headers()
    if not headers:
        return default
    base = os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets').rstrip('/')
    try:
        r = requests.get(base + path, headers=headers, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {'error': str(e), 'fallback': default}


def latest_open_trade_by_symbol(trades):
    grouped = defaultdict(list)
    for t in trades:
        if status_of_trade(t) != 'open':
            continue
        sym = str(t.get('symbol') or '').replace('/', '')
        if not sym:
            continue
        dt = parse_dt(t.get('timestamp_entry') or t.get('entry_time_cet')) or datetime.min.replace(tzinfo=CET)
        grouped[sym].append({**t, '_dt': dt})
    out = {}
    for sym, rows in grouped.items():
        known = [r for r in rows if trade_engine(r) != 'unknown']
        pool = known or rows
        out[sym] = sorted(pool, key=lambda r: r['_dt'], reverse=True)[0]
    return out


def protection_by_symbol(orders):
    out = defaultdict(list)
    if not isinstance(orders, list):
        return out
    for o in orders:
        if o.get('type') in ('stop', 'stop_limit', 'trailing_stop') or o.get('stop_price'):
            out[str(o.get('symbol')).replace('/', '')].append(o)
    return out


def stale_open_trades(trades, alpaca_positions):
    live = {str(p.get('symbol')).replace('/', '') for p in alpaca_positions if isinstance(p, dict)} if isinstance(alpaca_positions, list) else set()
    stale = []
    for t in trades:
        sym = str(t.get('symbol') or '').replace('/', '')
        if status_of_trade(t) == 'open' and sym and sym not in live:
            stale.append({
                'symbol': t.get('symbol'), 'engine': trade_engine(t), 'engine_label': ENGINE_LABELS.get(trade_engine(t), trade_engine(t)),
                'side': t.get('side'), 'entry_price': t.get('entry_price'), 'qty': t.get('qty'),
                'opened_at': t.get('timestamp_entry') or t.get('entry_time_cet'), 'stop_loss': t.get('stop_loss'), 'take_profit': t.get('take_profit')
            })
    return stale[-30:]


def summarize_positions(alpaca_positions, trades, orders):
    if isinstance(alpaca_positions, dict) and 'error' in alpaca_positions:
        return {'error': alpaca_positions['error'], 'rows': [], 'count': 0, 'total_unrealized_pl': 0, 'stale_journal_opens': []}
    open_by_symbol = latest_open_trade_by_symbol(trades)
    protection = protection_by_symbol(orders)
    rows = []
    for p in alpaca_positions if isinstance(alpaca_positions, list) else []:
        sym = p.get('symbol')
        t = open_by_symbol.get(str(sym).replace('/', ''), {})
        engine = trade_engine(t) if t else infer_engine(sym)
        stops = protection.get(str(sym).replace('/', ''), [])
        stop_prices = [float(o.get('stop_price')) for o in stops if o.get('stop_price')]
        qty = float(p.get('qty') or 0)
        rows.append({
            'symbol': sym,
            'side': p.get('side'),
            'qty': qty,
            'avg_entry_price': float(p.get('avg_entry_price') or 0),
            'current_price': float(p.get('current_price') or 0),
            'market_value': float(p.get('market_value') or 0),
            'cost_basis': float(p.get('cost_basis') or 0),
            'unrealized_pl': float(p.get('unrealized_pl') or 0),
            'unrealized_plpc': round(float(p.get('unrealized_plpc') or 0) * 100, 2),
            'change_today': round(float(p.get('change_today') or 0) * 100, 2),
            'asset_class': p.get('asset_class'),
            'engine': engine,
            'engine_label': ENGINE_LABELS.get(engine, engine),
            'stop_loss': stop_prices[0] if stop_prices else t.get('stop_loss'),
            'take_profit': t.get('take_profit'),
            'opened_at': t.get('timestamp_entry') or t.get('entry_time_cet'),
            'protection': 'protected' if stops or p.get('asset_class') == 'crypto' else 'missing_stop',
            'protection_orders': len(stops),
            'stop_prices': stop_prices,
        })
    rows.sort(key=lambda x: x['unrealized_pl'])
    return {
        'count': len(rows),
        'total_unrealized_pl': round(sum(x['unrealized_pl'] for x in rows), 2),
        'longs': sum(1 for x in rows if x['side'] == 'long'),
        'shorts': sum(1 for x in rows if x['side'] == 'short'),
        'rows': rows,
        'protected_count': sum(1 for x in rows if x.get('protection') == 'protected'),
        'missing_stop_count': sum(1 for x in rows if x.get('protection') == 'missing_stop'),
        'stale_journal_opens': stale_open_trades(trades, alpaca_positions),
    }


def infer_engine(symbol):
    if str(symbol).endswith('USD'):
        return 'crypto_24_7'
    return 'unknown'


def summarize_orders(orders):
    if not isinstance(orders, list):
        return []
    return [{
        'symbol': o.get('symbol'), 'side': o.get('side'), 'qty': o.get('qty'), 'type': o.get('type'),
        'order_class': o.get('order_class'), 'status': o.get('status'), 'limit_price': o.get('limit_price'),
        'stop_price': o.get('stop_price'), 'created_at': o.get('created_at')
    } for o in orders[:50]]


def period_start(now):
    return {'day': now.date(), 'week': (now - timedelta(days=now.weekday())).date(), 'month': now.date().replace(day=1)}


def summarize_periods(trades):
    now = datetime.now(CET); starts = period_start(now)
    out = {k: {'pnl': 0.0, 'trades': 0, 'wins': 0} for k in starts}
    for t in trades:
        if status_of_trade(t) == 'open':
            continue
        dt = parse_dt(t.get('timestamp_exit') or t.get('timestamp_entry'))
        if not dt: continue
        pnl = pnl_of(t); d = dt.date()
        for key, start in starts.items():
            if d >= start:
                out[key]['pnl'] += pnl; out[key]['trades'] += 1; out[key]['wins'] += pnl > 0
    for b in out.values():
        n = b['trades']; b['win_rate'] = round((b['wins'] / n * 100), 1) if n else 0.0; b['pnl'] = round(b['pnl'], 2)
    return out


def summarize_engines(trades, health, positions_summary):
    grouped = defaultdict(lambda: {'engine': '', 'trades': 0, 'open': 0, 'wins': 0, 'pnl': 0.0, 'unrealized': 0.0, 'last_trade_at': None})
    for cfg in CONFIGURED_ENGINES:
        grouped[cfg['key']]['engine'] = cfg['key']
    for t in trades:
        engine = trade_engine(t); row = grouped[engine]; row['engine'] = engine; row['trades'] += 1
        if status_of_trade(t) == 'open': row['open'] += 1
        else:
            pnl = pnl_of(t); row['pnl'] += pnl; row['wins'] += pnl > 0
        dt = parse_dt(t.get('timestamp_exit') or t.get('timestamp_entry'))
        if dt and (row['last_trade_at'] is None or dt > row['last_trade_at']): row['last_trade_at'] = dt
    # Live Alpaca positions are the authority for open count.
    for row in grouped.values():
        row['open'] = 0
        row['unrealized'] = 0.0
    for p in positions_summary.get('rows', []):
        row = grouped[p['engine']]; row['engine'] = p['engine']; row['open'] += 1; row['unrealized'] += p['unrealized_pl']
    rows = []
    for engine, row in grouped.items():
        if engine == 'unknown' and row['open'] == 0:
            continue
        closed = sum(1 for t in trades if trade_engine(t) == engine and status_of_trade(t) != 'open'); wr = round((row['wins'] / closed * 100), 1) if closed else 0.0
        cfg = next((c for c in CONFIGURED_ENGINES if c['key'] == engine), {})
        h = health_for_engine(health, engine)
        rows.append({
            'engine': engine, 'label': cfg.get('label') or ENGINE_LABELS.get(engine, engine), 'channel': cfg.get('channel', '-'),
            'script': cfg.get('script', '-'), 'cadence': cfg.get('cadence', '-'), 'configured_status': cfg.get('status', 'seen in journal'),
            'trades': row['trades'], 'closed_trades': closed, 'open_positions': row['open'], 'win_rate': wr,
            'pnl': round(row['pnl'], 2), 'unrealized_pl': round(row['unrealized'], 2),
            'health_state': h.get('health') or ('active' if cfg else 'journal'), 'size_multiplier': h.get('size_multiplier'),
            'health_note': h.get('note') or '', 'recent_pnl': round(float(h.get('recent_pnl') or 0), 2),
            'recent_win_rate': round(float(h.get('recent_win_rate') or 0) * 100, 1) if h else 0,
            'last_trade_at': row['last_trade_at'].isoformat() if row['last_trade_at'] else None,
            'why_no_trade': engine_explanation(cfg, h, row),
        })
    rows.sort(key=lambda x: (x['open_positions'] > 0, x['pnl'], x['win_rate']), reverse=True)
    return rows



def summarize_run_monitor(trades, health):
    log_path = DATA_DIR / 'engine-run.log'
    lines = log_path.read_text(encoding='utf-8', errors='ignore').splitlines()[-1500:] if log_path.exists() else []
    monitor = {c['key']: {'engine': c['key'], 'label': c['label'], 'last_run': None, 'last_signal': None, 'last_skip': None, 'status': 'unknown', 'scanned': 0, 'signals': 0, 'executed': 0, 'diagnosis': 'No recent run found'} for c in CONFIGURED_ENGINES}
    current_ts = None
    for line in lines:
        ts = line[:19] if len(line) >= 19 and line[:4].isdigit() else None
        if ts: current_ts = ts
        low=line.lower()
        if 'run started' in low:
            for key in ('A','B'):
                monitor[key]['last_run'] = current_ts; monitor[key]['status'] = 'ran'
        m=re.search(r'Engine A: scanned=(\d+), executed=(\d+)', line)
        if m:
            mon=monitor['A']; mon['last_run']=current_ts; mon['scanned']=int(m.group(1)); mon['executed']=int(m.group(2)); mon['last_signal']=line.split('Engine A:',1)[1].strip(); mon['status']='blocked' if int(m.group(2))==0 else 'traded'
        m=re.search(r'Engine B: signals=(\d+), executed=(\d+)', line)
        if m:
            mon=monitor['B']; mon['last_run']=current_ts; mon['signals']=int(m.group(1)); mon['executed']=int(m.group(2)); mon['last_signal']=line.split('Engine B:',1)[1].strip(); mon['status']='blocked' if int(m.group(2))==0 else 'traded'
        if any(x in low for x in ('skip','no signal','no trade','outside window','max trades','negative ev','llm')):
            for name,key in {'engine a':'A','engine b':'B','crypto 24/7':'crypto_24_7','crypto john':'crypto_john','engine c':'C','engine d':'D','daytrading':'daytrading'}.items():
                if name in low: monitor[key]['last_skip'] = line[-220:]
    for e in summarize_engines(trades, health, {'rows': []}):
        key=e['engine']; m=monitor.setdefault(key, {'engine':key,'label':e['label']})
        m.update({'last_trade_at': e.get('last_trade_at'), 'health_state': e.get('health_state'), 'why_no_trade': e.get('why_no_trade'), 'size_multiplier': e.get('size_multiplier'), 'recent_pnl': e.get('recent_pnl'), 'recent_win_rate': e.get('recent_win_rate')})
        if not m.get('last_run') and e.get('last_trade_at'): m['last_run'] = e.get('last_trade_at')
    for key,m in monitor.items():
        if key=='A' and m.get('scanned') and not m.get('executed'):
            m['diagnosis']='Scanning symbols but no setups pass multi-signal gates; review thresholds/stale edge filters.'
        elif key=='B' and m.get('signals') and not m.get('executed'):
            m['diagnosis']='Signals detected but execution vetoed by risk/edge/LLM/position filters.'
        elif key=='crypto_24_7':
            open_crypto=[t for t in trades if trade_engine(t)=='crypto_24_7' and status_of_trade(t)=='open']
            m['diagnosis']=f'{len(open_crypto)} open journal crypto positions; closed P/L is flat until exits reconcile.' if open_crypto else 'Waiting for strict crypto setup.'
        elif not m.get('last_trade_at') and not m.get('last_signal'):
            m['diagnosis']='Configured but no usable recent trade/signal in local journal/log.'
        elif m.get('executed')==0:
            m['diagnosis']=m.get('last_skip') or 'Ran but did not execute.'
        else:
            m['diagnosis']='Healthy/recent activity.'
        if m.get('health_state') == 'paused': m['status']='paused'
        elif m.get('status') == 'unknown': m['status']='ok'
    return list(monitor.values())

def summarize_mismatches(positions_summary):
    rows=[]
    stale = positions_summary.get('stale_journal_opens', []) or []
    if stale:
        by_engine = {}
        for t in stale:
            label = t.get('engine_label') or t.get('engine') or 'unknown'
            by_engine.setdefault(label, set()).add(t.get('symbol') or '?')
        rows.append({
            'type': 'journal_open_not_in_alpaca_summary',
            'severity': 'info',
            'count': len(stale),
            'action': 'Historical journal cleanup needed, not live risk',
            'details': [f"{k}: {len(v)} symbols" for k, v in sorted(by_engine.items())][:8],
            'symbols': sorted({t.get('symbol') for t in stale if t.get('symbol')})[:12],
        })
    if positions_summary.get('missing_stop_count',0):
        rows.append({'type':'missing_stop', 'severity':'critical', 'action':'Add stop/protection', 'count':positions_summary.get('missing_stop_count')})
    return rows


def summarize_governance(trades, positions_summary):
    items=[]
    for p in positions_summary.get('rows', []):
        risk = abs((float(p.get('avg_entry_price') or 0)-float(p.get('stop_loss') or 0))*float(p.get('qty') or 0))
        rr = None
        if p.get('stop_loss') and p.get('take_profit'):
            loss=abs(float(p['avg_entry_price'])-float(p['stop_loss'])); gain=abs(float(p['take_profit'])-float(p['avg_entry_price'])); rr=round(gain/loss,2) if loss else None
        score = 24 if p.get('protection')=='protected' and rr and rr>=1.5 else 18
        status = 'PAPER' if score>=20 else 'WATCHLIST'
        items.append({'symbol':p['symbol'],'engine':p['engine_label'],'status':status,'score':score,'bull_case':'Entry valid while price respects setup and stop.','bear_case':'Invalidates if stop/kill level breaks or crypto exposure spikes.','kill_criteria':f"Stop {p.get('stop_loss') or '-'}",'rr':rr,'risk_dollars':round(risk,2)})
    return items


def is_hedge_trade(t):
    blob = ' '.join(str(t.get(k) or '') for k in ('symbol','engine','engine_name','trade_mode','setup_type','close_reason','exit_reason')).lower()
    return any(x in blob for x in ('hedge','xau','gold','grid'))


def trade_close_dt(t):
    return parse_dt(t.get('timestamp_exit') or t.get('closed_at') or t.get('timestamp_entry') or t.get('entry_time_cet'))


def summarize_analytics(trades):
    now = datetime.now(CET)
    starts = {
        'today': now.date(),
        'week': (now - timedelta(days=now.weekday())).date(),
        'month': now.date().replace(day=1),
        'last_30d': (now - timedelta(days=30)).date(),
        'all': datetime(1970,1,1,tzinfo=CET).date(),
    }
    def empty(): return {'pnl':0.0,'trades':0,'wins':0,'losses':0,'profit':0.0,'loss':0.0,'best':None,'worst':None,'r_sum':0.0,'r_count':0,'best_r':None,'worst_r':None}
    periods={k:empty() for k in starts}; by_engine=defaultdict(lambda:{k:empty() for k in starts}); by_hedge={k:empty() for k in starts}; daily=defaultdict(empty); monthly=defaultdict(empty); weekly=defaultdict(empty)
    closed=[]
    for t in trades:
        if status_of_trade(t)=='open':
            continue
        dt=trade_close_dt(t)
        if not dt: continue
        pnl=pnl_of(t); r_mult=r_multiple_of(t); engine=trade_engine(t); hedge='hedge' if is_hedge_trade(t) else 'non_hedge'; d=dt.date(); wk=f"{dt.isocalendar().year}-W{dt.isocalendar().week:02d}"; mo=dt.strftime('%Y-%m')
        closed.append((dt,pnl,t,engine,hedge))
        buckets=[daily[d.isoformat()], weekly[wk], monthly[mo]]
        for key,start in starts.items():
            if d>=start: buckets += [periods[key], by_engine[engine][key], by_hedge[key]]
        for b in buckets:
            b['pnl']+=pnl; b['trades']+=1; b['wins']+= pnl>0; b['losses']+= pnl<0; b['profit']+= max(pnl,0); b['loss']+= min(pnl,0)
            if b['best'] is None or pnl>b['best']['pnl']: b['best']={'symbol':t.get('symbol'),'pnl':round(pnl,2),'date':dt.isoformat()}
            if b['worst'] is None or pnl<b['worst']['pnl']: b['worst']={'symbol':t.get('symbol'),'pnl':round(pnl,2),'date':dt.isoformat()}
            if r_mult is not None:
                b['r_sum']+=r_mult; b['r_count']+=1
                rr={'symbol':t.get('symbol'),'r':round(r_mult,2),'date':dt.isoformat()}
                if b['best_r'] is None or r_mult>b['best_r']['r']: b['best_r']=rr
                if b['worst_r'] is None or r_mult<b['worst_r']['r']: b['worst_r']=rr
    def finish(b):
        b['pnl']=round(b['pnl'],2); b['profit']=round(b['profit'],2); b['loss']=round(b['loss'],2)
        b['win_rate']=round(b['wins']/b['trades']*100,1) if b['trades'] else 0
        b['profit_factor']=round(b['profit']/abs(b['loss']),2) if b['loss'] else (999 if b['profit'] else 0)
        b['expectancy']=round(b['pnl']/b['trades'],2) if b['trades'] else 0
        b['avg_r']=round(b['r_sum']/b['r_count'],2) if b.get('r_count') else 0
        return b
    def finish_map(m): return {k:finish(v) for k,v in sorted(m.items())}
    equity=[]; cum=0
    for dt,pnl,t,engine,hedge in sorted(closed, key=lambda x:x[0]):
        cum+=pnl; equity.append({'date':dt.isoformat(),'pnl':round(pnl,2),'cum':round(cum,2),'symbol':t.get('symbol'),'engine':engine,'hedge':hedge})
    return {
        'generated_at': now.isoformat(),
        'periods': finish_map(periods),
        'by_engine': {ENGINE_LABELS.get(e,e): finish_map(v) for e,v in by_engine.items()},
        'hedge_overlay': finish_map(by_hedge),
        'daily': finish_map(daily),
        'weekly': finish_map(weekly),
        'monthly': finish_map(monthly),
        'equity_curve': equity[-240:],
        'r_distribution': [{'date':dt.isoformat(),'symbol':t.get('symbol'),'engine':engine,'r':round(r_multiple_of(t),2),'pnl':round(pnl,2)} for dt,pnl,t,engine,hedge in closed if r_multiple_of(t) is not None][-240:],
        'date_bounds': {'first': closed[0][0].isoformat() if closed else None, 'last': closed[-1][0].isoformat() if closed else None},
    }


def summarize_metatrader_bot():
    log_path = MT5_DIR / 'bot_run.log'
    state = read_json(MT5_DIR / 'live_state.json', {})
    lines = log_path.read_text(encoding='utf-8', errors='ignore').splitlines()[-220:] if log_path.exists() else []
    signals=[]; errors=[]; account=None; equity=None; last_ts=None; autotrading_disabled=False
    for line in lines:
        m=re.search(r'(20\d\d-\d\d-\d\d[ T]\d\d:\d\d:\d\d)', line)
        if m: last_ts=m.group(1).replace(' ', 'T')
        if 'konto ' in line and 'MT5 anslutet' in line:
            mm=re.search(r'konto\s+(\d+)\s+pa\s+(.+?)\s+\(typ:\s*(\d+)\)', line)
            if mm: account={'id':mm.group(1),'server':mm.group(2),'type':mm.group(3)}
        if 'start-equity:' in line or 'start-equity' in line:
            mm=re.search(r'start-equity:\s*([0-9.]+)', line)
            if mm: equity=float(mm.group(1))
        if 'NEW SIGNAL:' in line:
            mm=re.search(r'NEW SIGNAL:\s*(\w+)\s+? opening\s+([0-9.]+) lots', line)
            signals.append({'time':last_ts,'side':mm.group(1) if mm else None,'lots':float(mm.group(2)) if mm else None,'raw':line[-220:]})
        if 'ERROR' in line or 'misslyckades' in line:
            autotrading_disabled = autotrading_disabled or 'AutoTrading disabled' in line
            errors.append({'time':last_ts,'raw':line[-260:]})
    status = 'blocked_autotrading' if autotrading_disabled else ('running_or_recent' if lines else 'unknown')
    hb = MT5_DIR / 'live_heartbeat.txt'
    return {'name':'XAUUSD MetaTrader Bot','path':str(MT5_DIR),'log':str(log_path),'status':status,'account':account,'start_equity':equity,'state':state,'last_seen':last_ts,'heartbeat_modified':datetime.fromtimestamp(hb.stat().st_mtime, CET).isoformat() if hb.exists() else None,'signals_last_220_lines':signals[-10:],'errors_last_220_lines':errors[-8:],'autotrading_disabled':autotrading_disabled,'next_action':'Enable AutoTrading in MT5 client before live orders can execute.' if autotrading_disabled else 'Monitor live_state and broker positions.'}

def summarize_recent_trades(trades, limit=80):
    rows = []
    for t in trades:
        dt = parse_dt(t.get('timestamp_exit') or t.get('timestamp_entry'))
        if not dt: continue
        engine = trade_engine(t)
        rows.append({'engine': engine, 'label': ENGINE_LABELS.get(engine, engine), 'symbol': t.get('symbol'), 'side': t.get('side') or t.get('direction'), 'status': t.get('status'), 'pnl': round(pnl_of(t), 2), 'entry_price': t.get('entry_price'), 'exit_price': t.get('exit_price') or t.get('close_price'), 'timestamp': dt.isoformat(), 'reason': t.get('close_reason') or t.get('exit_reason') or ''})
    rows.sort(key=lambda x: x['timestamp'], reverse=True)
    return rows[:limit]



def summarize_engine_activity(trades, health, positions_summary):
    engines=summarize_engines(trades, health, positions_summary)
    run={r.get('engine'):r for r in summarize_run_monitor(trades, health)}
    analytics=summarize_analytics(trades).get('by_engine',{})
    rows=[]
    for e in engines:
        key=e['engine']; label=e['label']; a=analytics.get(ENGINE_LABELS.get(key,key)) or analytics.get(label) or {}
        month=a.get('month',{}) if isinstance(a,dict) else {}
        r=run.get(key,{})
        rows.append({
            'engine':key,'label':label,'closed_month_trades':month.get('trades',0),'closed_month_pnl':month.get('pnl',0),
            'open_positions':e.get('open_positions',0),'unrealized_pl':e.get('unrealized_pl',0),'last_trade_at':e.get('last_trade_at'),
            'last_run':r.get('last_run'),'last_signal':r.get('last_signal'),'last_skip':r.get('last_skip'), 'run_status':r.get('status'),
            'diagnosis':r.get('diagnosis') or e.get('why_no_trade'),'health_state':e.get('health_state'), 'action_hint': engine_action_hint(key,r,e,month)
        })
    return rows


def engine_action_hint(key,r,e,month):
    if month.get('trades',0)>0: return 'Trading this month; monitor quality not quantity.'
    if key=='A': return 'Audit Engine A thresholds/edge filters; it scans but does not execute.'
    if key=='B': return 'Inspect veto reasons when signals>0 but executed=0.'
    if key=='crypto_24_7': return 'Separate open/unrealized from closed P/L; reconcile stale opens if any.'
    if key=='unknown': return 'Fix engine mapping for live broker positions.'
    return 'Check cron/log coverage and whether this engine is intentionally inactive.'

def summarize_health(health):
    return {'leaders': [], 'paused': [], 'cooldown': []} if not isinstance(health, dict) else {'leaders': [], 'paused': [], 'cooldown': []}


def summarize_ai_committee():
    scan = read_json(AIHF_JSON, {})
    blind = read_json(AIHF_BLIND_JSON, {})
    decisions = scan.get('decisions') or []
    top = decisions[:12]
    counts = {}
    for d in decisions:
        counts[d.get('decision', 'UNKNOWN')] = counts.get(d.get('decision', 'UNKNOWN'), 0) + 1
    return {
        'generated_at': scan.get('generated_at'),
        'quality_gate_threshold': scan.get('quality_gate_threshold'),
        'snapshot_counts': scan.get('snapshot_counts'),
        'counts': counts,
        'top': top,
        'agent_heatmap': scan.get('agent_heatmap') or [],
        'discord_summary': scan.get('discord_summary'),
        'blind_evaluation': blind.get('blind_evaluation'),
        'simulation': read_json(AIHF_PORTFOLIO_JSON, {}),
        'alpaca_live': read_json(AIHF_ALPACA_STATE_JSON, {}),
        'execution_model_note': 'Simulation is a local research shadow book. Alpaca Paper Live is the broker paper account and is the primary live-paper track. Results differ because of start date, account equity, whole-share/bracket fills, and existing account positions.',
        'caveat': 'AIHF is Alpaca PAPER only. Simulation and broker paper are separated deliberately.',
    }


def build():
    OUT_DIR.mkdir(parents=True, exist_ok=True); SITE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    trades = load_trades(); status = read_json(STATUS_JSON, {}); health = read_json(HEALTH_JSON, {}); daily = read_json(DATA_DIR / 'daily-state.json', {})
    account = alpaca_get('/v2/account', {})
    alpaca_positions = alpaca_get('/v2/positions', [])
    orders = alpaca_get('/v2/orders?status=open&limit=100&nested=true', [])
    positions = summarize_positions(alpaca_positions, trades, orders)
    overview = {
        'generated_at': datetime.now(CET).isoformat(),
        'portfolio_value': float(account.get('portfolio_value') or daily.get('portfolio_value_current') or 0) if isinstance(account, dict) else daily.get('portfolio_value_current'),
        'buying_power': float(account.get('buying_power') or 0) if isinstance(account, dict) else None,
        'cash': float(account.get('cash') or 0) if isinstance(account, dict) else None,
        'daily_pnl': positions.get('total_unrealized_pl', daily.get('daily_pnl')),
        'trades_today': daily.get('trades_today'),
        'positions_count': positions.get('count', 0),
        'orders_count': len(orders) if isinstance(orders, list) else 0,
        'stack_status': status,
    }
    outputs = {
        'overview.json': overview,
        'positions.json': positions,
        'orders.json': summarize_orders(orders),
        'engines.json': summarize_engines(trades, health, positions),
        'trades.json': summarize_recent_trades(trades),
        'periods.json': summarize_periods(trades),
        'analytics.json': summarize_analytics(trades),
        'metatrader.json': summarize_metatrader_bot(),
        'health.json': summarize_health(health),
        'status.json': {'stack': status, 'configured_engines': CONFIGURED_ENGINES},
        'run-monitor.json': summarize_run_monitor(trades, health),
        'engine-activity.json': summarize_engine_activity(trades, health, positions),
        'mismatches.json': summarize_mismatches(positions),
        'governance.json': summarize_governance(trades, positions),
        'ai-committee.json': summarize_ai_committee(),
    }
    for filename, payload in outputs.items():
        for out_dir in (OUT_DIR, SITE_DATA_DIR):
            with open(out_dir / filename, 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f'Wrote {len(outputs)} dashboard data files to {OUT_DIR} and {SITE_DATA_DIR}')

if __name__ == '__main__':
    build()
