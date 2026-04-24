export async function onRequestGet({ request, env }) {
  const url = new URL(request.url);
  const symbol = (url.searchParams.get('symbol') || '').toUpperCase().replace('/', '');
  const timeframe = url.searchParams.get('timeframe') || '5Min';
  const limit = Math.min(Number(url.searchParams.get('limit') || 120), 500);
  if (!symbol) return json({ error: 'Missing symbol' }, 400);
  const key = env.ALPACA_KEY;
  const secret = env.ALPACA_SECRET;
  if (!key || !secret) return json({ error: 'Missing Alpaca env vars' }, 500);
  const headers = { 'APCA-API-KEY-ID': key, 'APCA-API-SECRET-KEY': secret };
  try {
    const crypto = symbol.endsWith('USD') && !['USO'].includes(symbol);
    const dataBase = env.ALPACA_DATA_URL || 'https://data.alpaca.markets';
    const endpoint = crypto
      ? `${dataBase}/v1beta3/crypto/us/bars?symbols=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(timeframe)}&limit=${limit}&sort=asc`
      : `${dataBase}/v2/stocks/${encodeURIComponent(symbol)}/bars?timeframe=${encodeURIComponent(timeframe)}&limit=${limit}&adjustment=raw&feed=iex&sort=asc`;
    const raw = await fetch(endpoint, { headers }).then(checkJson);
    const bars = crypto ? (raw.bars?.[symbol] || []) : (raw.bars || []);
    return json({ generated_at: new Date().toISOString(), symbol, timeframe, bars });
  } catch (err) {
    return json({ error: err.message || String(err), symbol }, 502);
  }
}
async function checkJson(res) { if (!res.ok) throw new Error(`${res.status} ${await res.text()}`); return res.json(); }
function json(payload, status = 200) { return new Response(JSON.stringify(payload, null, 2), { status, headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store, max-age=0' } }); }
