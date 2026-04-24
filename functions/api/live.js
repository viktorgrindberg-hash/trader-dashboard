export async function onRequestGet({ env }) {
  const key = env.ALPACA_KEY;
  const secret = env.ALPACA_SECRET;
  const base = env.ALPACA_BASE_URL || 'https://paper-api.alpaca.markets';
  if (!key || !secret) {
    return json({ error: 'Missing Alpaca env vars on Cloudflare Pages' }, 500);
  }
  const headers = {
    'APCA-API-KEY-ID': key,
    'APCA-API-SECRET-KEY': secret,
  };
  try {
    const [account, positions, orders] = await Promise.all([
      fetch(`${base}/v2/account`, { headers }).then(checkJson),
      fetch(`${base}/v2/positions`, { headers }).then(checkJson),
      fetch(`${base}/v2/orders?status=open&limit=100&nested=true`, { headers }).then(checkJson),
    ]);
    const totalUnrealized = positions.reduce((sum, p) => sum + Number(p.unrealized_pl || 0), 0);
    return json({
      generated_at: new Date().toISOString(),
      account,
      overview: {
        portfolio_value: Number(account.portfolio_value || 0),
        buying_power: Number(account.buying_power || 0),
        cash: Number(account.cash || 0),
        positions_count: positions.length,
        orders_count: orders.length,
        daily_pnl: Number(totalUnrealized.toFixed(2)),
      },
      positions,
      orders,
    });
  } catch (err) {
    return json({ error: err.message || String(err) }, 502);
  }
}

async function checkJson(res) {
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json();
}

function json(payload, status = 200) {
  return new Response(JSON.stringify(payload, null, 2), {
    status,
    headers: {
      'content-type': 'application/json; charset=utf-8',
      'cache-control': 'no-store, max-age=0',
    },
  });
}
