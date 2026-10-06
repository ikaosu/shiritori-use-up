"""お題の候補を検証して data/prompts.json を作る。

条件: 辞書にある / 全部ちがう字 / 末尾が「ん」でない / 使い切りの解が見つかる(人名を除く辞書で)
"""
import os, sys, json, random, collections
HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
from prep import convert, KANA, NORM
from solve import mask_of, IDX, min_search, initial, popcount

CANDS = """たからもの ひみつきち ゆうえんち おもいで はなたば さくらもち いちごみるく たいやき おにぎり ひこうき
かみなり ほしぞら たけのこ みかづき ゆきだるま あまやどり はなむけ こもれび ひなたぼっこ さんぽみち
ことばあそび ゆめものがたり しあわせ あおぞら はるかぜ なつやすみ ふゆげしき ちからもち まほうつかい ひとやすみ
うたごえ ゆうやけ こいのぼり もみじがり かきごおり すいかわり おとしだま ひなまつり さかなつり ほたるがり
やまのぼり あさやけ くじらぐも ねこじゃらし うみのひ ふじさん たこやき くつした てぶくろ わたがし
きんぎょすくい はなびたいかい やきいも ひまわり あじさい こいごころ""".split()

words = {}
for line in open(os.path.join(HERE, '..', 'data', 'words.txt'), encoding='utf-8'):
    r, t = line.rstrip('\n').split('\t')
    words[r] = int(t)

by_start = collections.defaultdict(list)
exact = collections.defaultdict(list)
for r, t in words.items():
    if t == 3:      # 人名は除いて検証
        continue
    s, cons, e = convert(r)
    m = mask_of(cons)
    w = (m, IDX[e], r, r, len(cons))
    by_start[IDX[s]].append(w)
    exact[(IDX[s], m)].append(w)
for lst in by_start.values():
    lst.sort(key=lambda w: -w[4])

random.seed(7)
ok = []
for c in CANDS:
    if c not in words:
        print(f'  辞書になし: {c}')
        continue
    norm = [NORM.get(ch, ch) for ch in c]
    if len(set(norm)) != len(norm) or c[-1] == 'ん' or 'を' in c:
        print(f'  不適: {c}')
        continue
    used0, link0 = initial(c)
    sol = min_search(by_start, exact, used0, link0, width=250, topk=50, maxdepth=10)
    if sol is None:
        print(f'  解なし: {c}')
        continue
    ok.append({'word': c, 'link': KANA[link0], 'left': 45 - popcount(used0), 'ref': len(sol)})
    print(f'  OK {c} → {KANA[link0]} (残り{45 - popcount(used0)}) 目安 {len(sol)}語')
    sys.stdout.flush()

json.dump(ok, open(os.path.join(HERE, '..', 'data', 'prompts.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print('採用', len(ok))
