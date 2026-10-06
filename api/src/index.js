// 節約しりとり ランキング API (Cloudflare Workers + D1)
//
// 送られてくるのは「つないだ言葉の列」。サーバーが、お題・ルール・辞書をすべて検証してから記録する。
// 辞書は、秘密の値(DICT_SALT)を混ぜたハッシュ(6バイト)の並びを同梱している(dict.bin)。
import dictBin from '../dict.bin';
import prompts from '../../data/prompts.json';

// ---- 文字の決まり(play.html と同じ) ----
const KANA = 'あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわん';
const IDX = {}; [...KANA].forEach((c, i) => { IDX[c] = i; });
const TOTAL = KANA.length; // 45
const NORM = {};
[...'がぎぐげござじずぜぞだぢづでどばびぶべぼ'].forEach((c, i) => { NORM[c] = 'かきくけこさしすせそたちつてとはひふへほ'[i]; });
[...'ぱぴぷぺぽ'].forEach((c, i) => { NORM[c] = 'はひふへほ'[i]; });
[...'ぁぃぅぇぉっゃゅょゎゔ'].forEach((c, i) => { NORM[c] = 'あいうえおつやゆよわう'[i]; });
const VOWEL = {};
[['あかさたなはまやらわ', 'あ'], ['いきしちにひみり', 'い'], ['うくすつぬふむゆる', 'う'], ['えけせてねへめれ', 'え'], ['おこそとのほもよろ', 'お']]
  .forEach(([row, v]) => [...row].forEach(c => { VOWEL[c] = v; }));
const toHira = s => s.normalize('NFKC').replace(/[\s　]/g, '').replace(/[ァ-ヶ]/g, c => String.fromCharCode(c.charCodeAt(0) - 0x60));

function analyze(r) {
  if (!/^[ぁ-ゖー]+$/.test(r) || r.length < 3 || r[0] === 'ー') return { err: 'bad' };
  const units = [];
  for (const ch of r) {
    if (ch === 'ー') { units.push('ー'); continue; }
    const n = NORM[ch] || ch;
    if (n === 'を' || !(n in IDX)) return { err: 'bad' };
    units.push(n);
  }
  const start = units[0];
  const cons = units.slice(1).filter(u => u !== 'ー');
  if (cons.length < 2) return { err: 'short' };
  let end;
  if (units[units.length - 1] === 'ー') {
    const prev = units.filter(u => u !== 'ー').pop();
    if (!(prev in VOWEL)) return { err: 'bad' };
    end = VOWEL[prev];
  } else end = units[units.length - 1];
  return { start, cons, end };
}

// ---- 辞書(ハッシュの二分探索) ----
const DICT = new Uint8Array(dictBin);
const enc = new TextEncoder();
async function inDict(salt, reading) {
  const d = new Uint8Array(await crypto.subtle.digest('SHA-256', enc.encode(salt + reading)));
  let lo = 0, hi = DICT.length / 6 - 1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1, o = mid * 6;
    let c = 0;
    for (let i = 0; i < 6; i++) { c = DICT[o + i] - d[i]; if (c) break; }
    if (c === 0) return true;
    if (c < 0) lo = mid + 1; else hi = mid - 1;
  }
  return false;
}

// ---- お題 ----
const DAY0 = Math.floor(Date.UTC(2026, 0, 1) / 86400e3);
const jstDay = () => Math.floor((Date.now() + 9 * 3600e3) / 86400e3);
function today() {
  const day = jstDay();
  return { day, p: prompts[(((day - DAY0) % prompts.length) + prompts.length) % prompts.length] };
}

// ---- 検証 ----
async function validate(env, p, mode, chain) {
  if (!Array.isArray(chain) || chain.length < 1 || chain.length > TOTAL) return 'chain';
  const used = new Set([...p.word].map(c => NORM[c] || c));
  let link = p.link;
  for (let i = 0; i < chain.length; i++) {
    if (typeof chain[i] !== 'string' || chain[i].length > 40) return 'word';
    const r = toHira(chain[i]);
    const a = analyze(r);
    if (a.err) return `rule:${i}`;
    if (a.start !== link) return `link:${i}`;
    const seen = new Set();
    for (const c of a.cons) {
      if (seen.has(c) || used.has(c)) return `used:${i}`;
      seen.add(c);
    }
    if (!(await inDict(env.DICT_SALT, r))) return `dict:${i}`;
    if (a.end === 'ん' && i !== chain.length - 1) return `n:${i}`;
    for (const c of a.cons) used.add(c);
    link = a.end;
  }
  if (mode === 2 && TOTAL - used.size !== 0) return 'notcleared';
  return null;
}

// ---- 応答 ----
function corsHeaders(origin) {
  const ok = origin === 'https://ikaosu.github.io' || /^http:\/\/(localhost|127\.0\.0\.1):\d+$/.test(origin);
  return {
    'Access-Control-Allow-Origin': ok ? origin : 'https://ikaosu.github.io',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'content-type, x-admin-token',
    'Vary': 'Origin',
  };
}
const json = (obj, status, cors) => new Response(JSON.stringify(obj), { status, headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store', ...cors } });
const cleanName = s => String(s || '').normalize('NFKC').replace(/[\u0000-\u001f\u007f<>&"']/g, '').trim().slice(0, 12) || '名無し';
const DEVICE_RE = /^[A-Za-z0-9-]{8,64}$/;

async function ranking(env, day, p, mode, device) {
  const total = (await env.DB.prepare('SELECT COUNT(*) AS c FROM scores WHERE day = ? AND mode = ?').bind(day, mode).first()).c;
  let top = [];
  if (mode === 1) {
    const { results } = await env.DB.prepare('SELECT name, n, device FROM scores WHERE day = ? AND mode = 1 ORDER BY n DESC, created ASC LIMIT 10').bind(day).all();
    let rank = 0, prev = null;
    top = results.map((r, i) => { if (r.n !== prev) { rank = i + 1; prev = r.n; } return { rank, name: r.name, n: r.n, mine: !!device && r.device === device }; });
  }
  let me = null;
  if (device) {
    const row = await env.DB.prepare('SELECT name, n FROM scores WHERE day = ? AND mode = ? AND device = ?').bind(day, mode, device).first();
    if (row) {
      const rank = mode === 1 ? 1 + (await env.DB.prepare('SELECT COUNT(*) AS c FROM scores WHERE day = ? AND mode = 1 AND n > ?').bind(day, row.n).first()).c : null;
      me = { name: row.name, n: row.n, rank };
    }
  }
  return { day, prompt: p.word, mode, total, top, me };
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const cors = corsHeaders(req.headers.get('Origin') || '');
    if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: cors });
    try {
      const { day, p } = today();
      if (url.pathname === '/api/v1/health') return json({ ok: true, day, prompt: p.word }, 200, cors);

      if (url.pathname === '/api/v1/ranking' && req.method === 'GET') {
        const mode = url.searchParams.get('mode') === '2' ? 2 : 1;
        const device = url.searchParams.get('device') || '';
        return json(await ranking(env, day, p, mode, DEVICE_RE.test(device) ? device : ''), 200, cors);
      }

      if (url.pathname === '/api/v1/score' && req.method === 'POST') {
        let b;
        try { b = await req.json(); } catch { return json({ error: 'json' }, 400, cors); }
        const mode = b.mode === 2 ? 2 : b.mode === 1 ? 1 : 0;
        if (!mode || !DEVICE_RE.test(String(b.device || ''))) return json({ error: 'param' }, 400, cors);
        if (b.prompt !== p.word) return json({ error: 'expired', prompt: p.word }, 409, cors);
        const bad = await validate(env, p, mode, b.chain);
        if (bad) return json({ error: 'invalid', detail: bad }, 422, cors);
        const n = b.chain.length, name = cleanName(b.name), now = Date.now();
        await env.DB.prepare(
          `INSERT INTO scores (day, mode, device, name, n, chain, created) VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT (day, mode, device) DO UPDATE SET name = excluded.name,
             n = CASE WHEN excluded.n > scores.n THEN excluded.n ELSE scores.n END,
             chain = CASE WHEN excluded.n > scores.n THEN excluded.chain ELSE scores.chain END,
             created = CASE WHEN excluded.n > scores.n THEN excluded.created ELSE scores.created END`
        ).bind(day, mode, b.device, name, n, JSON.stringify(b.chain), now).run();
        return json({ ok: true, ...(await ranking(env, day, p, mode, b.device)) }, 200, cors);
      }

      if (url.pathname.startsWith('/api/v1/admin/')) {
        if (!env.ADMIN_TOKEN || req.headers.get('x-admin-token') !== env.ADMIN_TOKEN) return json({ error: 'forbidden' }, 403, cors);
        if (url.pathname === '/api/v1/admin/list') {
          const d = +(url.searchParams.get('day') || day);
          const { results } = await env.DB.prepare('SELECT day, mode, device, name, n, chain, created FROM scores WHERE day = ? ORDER BY mode, n DESC, created').bind(d).all();
          return json({ day: d, rows: results }, 200, cors);
        }
        if (url.pathname === '/api/v1/admin/delete' && req.method === 'POST') {
          const b = await req.json();
          const r = await env.DB.prepare('DELETE FROM scores WHERE day = ? AND mode = ? AND device = ?').bind(+b.day, +b.mode, String(b.device)).run();
          return json({ ok: true, changes: r.meta.changes }, 200, cors);
        }
      }
      return json({ error: 'not_found' }, 404, cors);
    } catch (e) {
      return json({ error: 'server', detail: String(e && e.message || e) }, 500, cors);
    }
  },
};
