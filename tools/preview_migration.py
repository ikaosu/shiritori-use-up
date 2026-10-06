"""本番の控え(SQL)を手元に読み込んで、新しい仕組みで並べ直した結果を表示する。読み取り専用(何も書き込まない)。

使い方: python tools/preview_migration.py <控えの .sql>
"""
import sys, json, sqlite3, os
HERE = os.path.dirname(__file__); sys.path.insert(0, HERE)
from prep import convert, NORM, KANA_SET

path = sys.argv[1]
db = sqlite3.connect(':memory:')
db.executescript(open(path, encoding='utf-8').read())
prompts = {p['word']: p for p in json.load(open(os.path.join(HERE, '..', 'data', 'prompts.json'), encoding='utf-8'))}


def sealed(p):
    return {NORM.get(c, c) for c in p['word'] + p.get('seal', '') if NORM.get(c, c) in KANA_SET}


def replay(prompt, chain):
    """つないだ言葉を、お題から順に消費していって、のこりの文字数を返す。ルール違反があれば None"""
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


rows = db.execute('select day, prompt, mode, device, name, n, rest, chain, created from scores order by day, prompt, mode, n desc, created').fetchall()
print(f'本番の記録: {len(rows)} 件')
groups = {}
for day, prompt, mode, device, name, n, rest, chain, created in rows:
    ch = json.loads(chain)
    r = replay(prompt, ch)
    groups.setdefault((day, prompt), []).append(dict(mode=mode, device=device, name=name, n=n, rest_db=rest, rest=r, chain=ch, created=created, len_ok=(len(ch) == n)))

for (day, prompt), L in groups.items():
    disp = prompts.get(prompt, {}).get('disp') or prompt
    print('\n' + '=' * 78)
    print(f'日 {day} / お題 {disp}（{prompt}）: {len(L)} 件')
    bad = [x for x in L if x['rest'] is None or not x['len_ok']]
    if bad:
        print('  ※ 検証できない記録:', [(x['name'], x['n']) for x in bad])
    m1 = sorted([x for x in L if x['mode'] == 1], key=lambda x: (-x['n'], x['created']))
    m2 = [x for x in L if x['mode'] == 2]
    print(f'  [いまの語数ランキング(mode 1)] {len(m1)} 人 → 移行しても、並びは変わりません')
    prev, rank = None, 0
    for i, x in enumerate(m1):
        if x['n'] != prev:
            rank, prev = i + 1, x['n']
        theory = '  ★理論値' if prompt in prompts and x['n'] >= (45 - len(sealed(prompts[prompt]))) // 2 else ''
        print(f"    {rank:>2}位 {x['name']:<12} {x['n']:>2}語  (のこり {x['rest']}字){'  ← 使い切り' if x['rest'] == 0 else ''}{theory}")
    print(f'  [いまのハード(mode 2)] {len(m2)} 件')
    for x in m2:
        print(f"    {x['name']:<12} {x['n']}語 のこり{x['rest_db']}字")
    # 移行後の使い切りランキング: 語数ランキングの記録のうち、使い切った(のこり0字)もの + 既存のハードの使い切り
    clears = {}
    for x in m1 + m2:
        if x['rest'] == 0:
            k = x['device']
            if k not in clears or x['n'] < clears[k]['n']:
                clears[k] = x
    ranked = sorted(clears.values(), key=lambda x: (x['n'], x['created']))
    print(f'  [移行後の使い切りランキング] {len(ranked)} 人（使い切った人だけ。少ない語数ほど上位）')
    prev, rank = None, 0
    for i, x in enumerate(ranked):
        if x['n'] != prev:
            rank, prev = i + 1, x['n']
        print(f"    {rank:>2}位 {x['name']:<12} {x['n']:>2}語で使い切り")
    if not ranked:
        print('    （まだ、使い切った記録はありません）')
    # 語数ランキング側へ: 既存のハードの記録が、語数ランキングに無い人
    m1dev = {x['device'] for x in m1}
    only2 = [x for x in m2 if x['device'] not in m1dev]
    if only2:
        print('  [語数ランキングに無い、ハードの人]', [(x['name'], x['n']) for x in only2])


# ================= 移行後(案) =================
# 1回の挑戦が、2つのランキングに載る仕組みなので、既存の記録も、端末ごとに次のようにそろえる
#   語数ランキング  = その端末の、語数(n)が最大の記録(語数ランキング・ハードの両方から)
#   使い切り        = その端末の、使い切った(のこり0字)記録のうち、語数が最小のもの
print('\n\n' + '#' * 78)
print('# 移行後(案): 端末ごとに、語数と使い切りの、それぞれの最良の記録を採る')
print('#' * 78)
for (day, prompt), L in groups.items():
    if prompt != 'るーびっくきゅーぶ':
        continue
    disp = prompts[prompt]['disp']
    M = (45 - len(sealed(prompts[prompt]))) // 2
    by_dev = {}
    for x in L:
        by_dev.setdefault(x['device'], []).append(x)
    words, clears = [], []
    for dev, xs in by_dev.items():
        best = max(xs, key=lambda x: (x['n'], -x['created']))
        name = max(xs, key=lambda x: x['created'])['name']
        words.append((best['n'], best['created'], name, dev, [x['mode'] for x in xs if x['n'] == best['n']]))
        cl = [x for x in xs if x['rest'] == 0]
        if cl:
            c = min(cl, key=lambda x: (x['n'], x['created']))
            clears.append((c['n'], c['created'], name, dev))
    words.sort(key=lambda t: (-t[0], t[1]))
    clears.sort(key=lambda t: (t[0], t[1]))
    before_m1 = {x['device']: x['n'] for x in L if x['mode'] == 1}
    print(f'\n■ {disp}  最大語数(理論値) {M}語')
    print(f'\n  [語数ランキング(移行後)] {len(words)} 人')
    prev, rank = None, 0
    for i, (n, cr, name, dev, ms) in enumerate(words):
        if n != prev:
            rank, prev = i + 1, n
        was = before_m1.get(dev)
        note = '' if was == n else ('  ← 新しく載る(語数ランキングの記録なし)' if was is None else f'  ← {was}語から更新(ハードの記録の方が長い)')
        print(f"    {rank:>2}位 {name:<12} {n:>2}語{'  ★理論値' if n >= M else ''}{note}")
    print(f'\n  [使い切りランキング(移行後)] {len(clears)} 人  ※使い切った人だけ。少ない語数ほど上位')
    prev, rank = None, 0
    for i, (n, cr, name, dev) in enumerate(clears):
        if n != prev:
            rank, prev = i + 1, n
        print(f"    {rank:>2}位 {name:<12} {n:>2}語で使い切り")
    partial = [(x['name'], x['n'], x['rest_db']) for x in L if x['mode'] == 2 and x['rest'] and x['rest'] > 0]
    print(f'\n  [使い切りランキングから外れる記録(ハードで、使い切れていない)] {partial}')
