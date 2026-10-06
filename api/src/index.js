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
// ---- 日ごとのお題 ----
// お題に day(JST の日数)があれば、その日だけのお題。ない日は、日ごとに決まる乱数で選ぶ(全員同じ。同じお題が続かない)
function mulberry32(a) { return () => { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
function orderOf(cycle, m) {
  const o = [...Array(m).keys()], r = mulberry32(cycle * 7919 + 12345);
  for (let i = m - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [o[i], o[j]] = [o[j], o[i]]; }
  if (cycle > 0 && o[0] === orderOf(cycle - 1, m)[m - 1]) [o[0], o[1]] = [o[1], o[0]];
  return o;
}
function idxForDay(day, list) {
  const fixed = list.findIndex(p => p.day === day);
  if (fixed >= 0) return fixed;
  const pool = list.map((p, i) => i).filter(i => list[i].day === undefined), m = pool.length;
  const START = 20733; // この日から、乱数で選ぶ(それより前は、順番どおり)
  if (day < START) return pool[(((day - Math.floor(Date.UTC(2026, 0, 1) / 86400e3)) % m) + m) % m];
  const k = day - START;
  return pool[orderOf(Math.floor(k / m), m)[k % m]];
}
const jstDay = () => Math.floor((Date.now() + 9 * 3600e3) / 86400e3);
function today(env) {
  const day = env && env.DAY_OVERRIDE ? +env.DAY_OVERRIDE : jstDay(); // DAY_OVERRIDE は、手元の試験用(本番には設定しない)
  return { day, p: prompts[idxForDay(day, prompts)] };
}

// ---- 検証 ----
// 節約の理論値: 1語で消える文字は最低2つなので、お題で残る文字の半分が最大の語数
const sealedOf = p => new Set([...p.word + (p.seal || '')].map(c => NORM[c] || c).filter(c => c in IDX));
const maxWordsOf = p => Math.floor((TOTAL - sealedOf(p).size) / 2);

async function validate(env, p, mode, chain, out) {
  if (!Array.isArray(chain) || chain.length < 1 || chain.length > TOTAL) return 'chain';
  const used = sealedOf(p); // お題の文字と、封じる文字。長音は消える文字ではない
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
  out.rest = TOTAL - used.size;
  if (mode === 2 && out.rest !== 0) return 'notcleared'; // 使い切りランキングは、使い切った人だけ
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
  const M = maxWordsOf(p);
  // 語数ランキング(mode 1)は、語数が多いほど上位。使い切りランキング(mode 2)は、使い切った人だけで、語数が少ないほど上位。同じなら、早く記録した方が上
  const cond = mode === 2 ? 'AND rest = 0' : '';
  const total = (await env.DB.prepare(`SELECT COUNT(*) AS c FROM scores WHERE day = ? AND prompt = ? AND mode = ? ${cond}`).bind(day, p.word, mode).first()).c;
  const order = mode === 1 ? 'n DESC, created ASC' : 'n ASC, created ASC';
  const { results } = await env.DB.prepare(`SELECT name, n, device FROM scores WHERE day = ? AND prompt = ? AND mode = ? ${cond} ORDER BY ${order} LIMIT 10`).bind(day, p.word, mode).all();
  let rank = 0, prev = null;
  const top = results.map((r, i) => {
    if (r.n !== prev) { rank = i + 1; prev = r.n; }
    return { rank, name: r.name, n: r.n, rest: mode === 2 ? 0 : null, max: mode === 1 && r.n >= M, mine: !!device && r.device === device };
  });
  let me = null;
  if (device) {
    const row = await env.DB.prepare(`SELECT name, n FROM scores WHERE day = ? AND prompt = ? AND mode = ? ${cond} AND device = ?`).bind(day, p.word, mode, device).first();
    if (row) {
      const better = await env.DB.prepare(`SELECT COUNT(*) AS c FROM scores WHERE day = ? AND prompt = ? AND mode = ? ${cond} AND n ${mode === 1 ? '>' : '<'} ?`).bind(day, p.word, mode, row.n).first();
      me = { name: row.name, n: row.n, rest: mode === 2 ? 0 : null, max: mode === 1 && row.n >= M, rank: 1 + better.c };
    }
  }
  return { day, prompt: p.word, mode, total, M, top, me };
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const cors = corsHeaders(req.headers.get('Origin') || '');
    if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: cors });
    try {
      const { day, p } = today(env);
      if (url.pathname === '/api/v1/health') return json({ ok: true, day, prompt: p.word }, 200, cors);

      if (url.pathname === '/api/v1/ranking' && req.method === 'GET') {
        const mode = url.searchParams.get('mode') === '2' ? 2 : 1;
        const device = url.searchParams.get('device') || '';
        // day を指定すると、過去の日のランキング(その日の公式のお題)を返す
        let d = Math.floor(+url.searchParams.get('day') || day);
        if (!(d >= day - 400 && d <= day)) d = day;
        const pp = d === day ? p : prompts[idxForDay(d, prompts)];
        return json(await ranking(env, d, pp, mode, DEVICE_RE.test(device) ? device : ''), 200, cors);
      }

      // その端末の、これまでの記録
      if (url.pathname === '/api/v1/history' && req.method === 'GET') {
        const device = url.searchParams.get('device') || '';
        if (!DEVICE_RE.test(device)) return json({ error: 'param' }, 400, cors);
        const { results } = await env.DB.prepare(
          `SELECT s.day, s.prompt, s.mode, s.n, s.rest,
             (CASE WHEN s.mode = 1
               THEN (SELECT COUNT(*) FROM scores t WHERE t.day = s.day AND t.prompt = s.prompt AND t.mode = 1 AND t.n > s.n)
               ELSE (SELECT COUNT(*) FROM scores t WHERE t.day = s.day AND t.prompt = s.prompt AND t.mode = 2 AND t.rest = 0 AND t.n < s.n) END) AS better,
             (SELECT COUNT(*) FROM scores t WHERE t.day = s.day AND t.prompt = s.prompt AND t.mode = s.mode AND (s.mode = 1 OR t.rest = 0)) AS total
           FROM scores s WHERE s.device = ? AND (s.mode = 1 OR s.rest = 0) ORDER BY s.day DESC, s.mode LIMIT 60`).bind(device).all();
        const rows = results.map(r => {
          const pr = prompts.find(x => x.word === r.prompt);
          return { day: r.day, prompt: r.prompt, mode: r.mode, n: r.n, rest: r.mode === 2 ? r.rest : null, rank: r.better + 1, total: r.total, max: r.mode === 1 && !!pr && r.n >= maxWordsOf(pr) };
        });
        return json({ rows }, 200, cors);
      }

      if (url.pathname === '/api/v1/score' && req.method === 'POST') {
        let b;
        try { b = await req.json(); } catch { return json({ error: 'json' }, 400, cors); }
        const mode = b.mode === 2 ? 2 : b.mode === 1 ? 1 : 0;
        if (!mode || !DEVICE_RE.test(String(b.device || ''))) return json({ error: 'param' }, 400, cors);
        if (b.prompt !== p.word) return json({ error: 'expired', prompt: p.word }, 409, cors);
        const out = {};
        const bad = await validate(env, p, mode, b.chain, out);
        if (bad) return json({ error: 'invalid', detail: bad }, 422, cors);
        const n = b.chain.length, name = cleanName(b.name), now = Date.now();
        await env.DB.prepare(
          `INSERT INTO scores (day, prompt, mode, device, name, n, rest, chain, created) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT (day, prompt, mode, device) DO UPDATE SET name = excluded.name,
             n = CASE WHEN (excluded.mode = 1 AND excluded.n > scores.n) OR (excluded.mode = 2 AND (excluded.rest < COALESCE(scores.rest, 999) OR (excluded.rest = COALESCE(scores.rest, 999) AND excluded.n < scores.n))) THEN excluded.n ELSE scores.n END,
             chain = CASE WHEN (excluded.mode = 1 AND excluded.n > scores.n) OR (excluded.mode = 2 AND (excluded.rest < COALESCE(scores.rest, 999) OR (excluded.rest = COALESCE(scores.rest, 999) AND excluded.n < scores.n))) THEN excluded.chain ELSE scores.chain END,
             created = CASE WHEN (excluded.mode = 1 AND excluded.n > scores.n) OR (excluded.mode = 2 AND (excluded.rest < COALESCE(scores.rest, 999) OR (excluded.rest = COALESCE(scores.rest, 999) AND excluded.n < scores.n))) THEN excluded.created ELSE scores.created END,
             rest = CASE WHEN (excluded.mode = 1 AND excluded.n > scores.n) OR (excluded.mode = 2 AND (excluded.rest < COALESCE(scores.rest, 999) OR (excluded.rest = COALESCE(scores.rest, 999) AND excluded.n < scores.n))) THEN excluded.rest ELSE scores.rest END`
        ).bind(day, p.word, mode, b.device, name, n, out.rest, JSON.stringify(b.chain), now).run();
        return json({ ok: true, ...(await ranking(env, day, p, mode, b.device)) }, 200, cors);
      }

      if (url.pathname.startsWith('/api/v1/admin/')) {
        if (!env.ADMIN_TOKEN || req.headers.get('x-admin-token') !== env.ADMIN_TOKEN) return json({ error: 'forbidden' }, 403, cors);
        if (url.pathname === '/api/v1/admin/days') {
          const { results } = await env.DB.prepare('SELECT day, prompt, COUNT(*) AS c FROM scores GROUP BY day, prompt ORDER BY day DESC, prompt LIMIT 90').all();
          return json({ today: day, days: results }, 200, cors);
        }
        if (url.pathname === '/api/v1/admin/list') {
          const d = +(url.searchParams.get('day') || day);
          const { results } = await env.DB.prepare('SELECT day, prompt, mode, device, name, n, rest, chain, created FROM scores WHERE day = ? ORDER BY prompt, mode, CASE WHEN mode = 1 THEN -n ELSE COALESCE(rest, 999) * 100 + n END, created').bind(d).all();
          return json({ day: d, rows: results }, 200, cors);
        }
        if (url.pathname === '/api/v1/admin/delete' && req.method === 'POST') {
          const b = await req.json();
          // お題(prompt)を指定したときは、そのお題の記録だけを消す
          const r = b.prompt
            ? await env.DB.prepare('DELETE FROM scores WHERE day = ? AND prompt = ? AND mode = ? AND device = ?').bind(+b.day, String(b.prompt), +b.mode, String(b.device)).run()
            : await env.DB.prepare('DELETE FROM scores WHERE day = ? AND mode = ? AND device = ?').bind(+b.day, +b.mode, String(b.device)).run();
          return json({ ok: true, changes: r.meta.changes }, 200, cors);
        }
      }
      return json({ error: 'not_found' }, 404, cors);
    } catch (e) {
      return json({ error: 'server', detail: String(e && e.message || e) }, 500, cors);
    }
  },
};
