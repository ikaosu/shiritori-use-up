"""本番の控え(SQL)から、「1回の挑戦が、語数と使い切りの両方に載る」仕組みへの、データ移行のSQLを作る。

方針(追加と補う更新だけ。記録は消さない。何度実行しても同じ結果になる):
  - 語数ランキング(mode 1)   : その端末の、語数が最大の記録を採る(ハードの記録の方が長ければ、そちらで更新)
  - 使い切りランキング(mode 2): その端末の、使い切った(のこり0字)記録のうち、語数が最小のものを採る
  - mode 1 の記録に、のこり文字(rest)を補う
  - 使い切れていないハードの記録(rest > 0)は、そのまま残す(新しい仕組みでは表示されない)

使い方: python tools/gen_migration.py <控え.sql> <出力.sql>
"""
import sys, json, sqlite3, os
HERE = os.path.dirname(__file__); sys.path.insert(0, HERE)
from prep import convert, NORM, KANA_SET

src, out = sys.argv[1], sys.argv[2]
db = sqlite3.connect(':memory:')
db.executescript(open(src, encoding='utf-8').read())
prompts = {p['word']: p for p in json.load(open(os.path.join(HERE, '..', 'data', 'prompts.json'), encoding='utf-8'))}


def sealed(p):
    return {NORM.get(c, c) for c in p['word'] + p.get('seal', '') if NORM.get(c, c) in KANA_SET}


def replay(prompt, chain):
    p = prompts.get(prompt)
    if not p:
        return None
    used = set(sealed(p))
    for w in chain:
        c = convert(w)
        if not c:
            return None
        used |= set(c[1])
    return 45 - len(used)


def q(v):
    if v is None:
        return 'NULL'
    if isinstance(v, int):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


rows = db.execute('select day, prompt, mode, device, name, n, rest, chain, created from scores').fetchall()
groups = {}
warn = []
for day, prompt, mode, device, name, n, rest, chain, created in rows:
    ch = json.loads(chain)
    r = replay(prompt, ch)
    if r is None or len(ch) != n:
        warn.append((day, prompt, mode, name, n))
        continue
    groups.setdefault((day, prompt, device), []).append(dict(day=day, prompt=prompt, mode=mode, device=device, name=name, n=n, rest_db=rest, rest=r, chain=chain, created=created))

stmts, report = [], []
for (day, prompt, device), xs in sorted(groups.items()):
    m1 = next((x for x in xs if x['mode'] == 1), None)
    m2 = next((x for x in xs if x['mode'] == 2), None)
    # 1) 語数ランキング
    best = max(xs, key=lambda x: (x['n'], -x['created']))
    if m1 is None:
        stmts.append(f"INSERT OR IGNORE INTO scores (day, prompt, mode, device, name, n, rest, chain, created) VALUES ({day}, {q(prompt)}, 1, {q(device)}, {q(best['name'])}, {best['n']}, {best['rest']}, {q(best['chain'])}, {best['created']});")
        report.append(f"語数ランキングに追加: {best['name']} {best['n']}語")
    elif best['n'] > m1['n']:
        stmts.append(f"UPDATE scores SET n = {best['n']}, rest = {best['rest']}, chain = {q(best['chain'])}, created = {best['created']} WHERE day = {day} AND prompt = {q(prompt)} AND mode = 1 AND device = {q(device)} AND n < {best['n']};")
        report.append(f"語数ランキングを更新: {m1['name']} {m1['n']}語 → {best['n']}語")
    elif m1['rest_db'] is None:
        stmts.append(f"UPDATE scores SET rest = {m1['rest']} WHERE day = {day} AND prompt = {q(prompt)} AND mode = 1 AND device = {q(device)} AND rest IS NULL;")
    # 2) 使い切りランキング
    clears = [x for x in xs if x['rest'] == 0]
    if clears:
        c = min(clears, key=lambda x: (x['n'], x['created']))
        if m2 is None:
            stmts.append(f"INSERT OR IGNORE INTO scores (day, prompt, mode, device, name, n, rest, chain, created) VALUES ({day}, {q(prompt)}, 2, {q(device)}, {q((m1 or c)['name'])}, {c['n']}, 0, {q(c['chain'])}, {c['created']});")
            report.append(f"使い切りランキングに追加: {(m1 or c)['name']} {c['n']}語")
        elif m2['rest'] != 0 or m2['n'] > c['n']:
            stmts.append(f"UPDATE scores SET n = {c['n']}, rest = 0, chain = {q(c['chain'])}, created = {c['created']} WHERE day = {day} AND prompt = {q(prompt)} AND mode = 2 AND device = {q(device)} AND (COALESCE(rest, 999) > 0 OR n > {c['n']});")
            report.append(f"使い切りランキングを更新: {m2['name']}")
    # 3) 使い切れていないハードは、そのまま残す
    if m2 is not None and m2['rest'] > 0 and not clears:
        report.append(f"残すだけ(表示されない): {m2['name']} ハード {m2['n']}語 のこり{m2['rest']}字")

with open(out, 'w', encoding='utf-8', newline='\n') as f:
    f.write('-- 1回の挑戦が、語数と使い切りの両方に載る仕組みへの、データ移行(追加と補う更新だけ。何度実行しても同じ結果)\n')
    f.write('\n'.join(stmts) + '\n')
print(f'記録 {len(rows)} 件 / 端末×お題 {len(groups)} 組 / 変更のSQL {len(stmts)} 文')
if warn:
    print('※ 検証できなかった記録:', warn)
for r in report:
    print('  -', r)
