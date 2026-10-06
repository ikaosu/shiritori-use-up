"""お題(最初の単語)を与えて、使い切りの最少語数(目安)と最多語数(目安)を探す試作。

厳密な最適は求めない。ビーム探索で「見つかった範囲での最少/最多」を出す。
"""
import json, os, sys, random, collections

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
from prep import KANA, NORM

IDX = {c: i for i, c in enumerate(KANA)}


def mask_of(s):
    m = 0
    for ch in s:
        m |= 1 << IDX[ch]
    return m


def load(variant, pos_filter):
    rows = json.load(open(os.path.join(HERE, '..', '.cache', f'words_{variant}.json'), encoding='utf-8'))
    by_start = collections.defaultdict(list)
    exact = collections.defaultdict(list)
    for r, s, cons, e, p2, p3, surf in rows:
        if not pos_filter(p2, p3):
            continue
        m = mask_of(cons)
        w = (m, IDX[e], r, surf, len(cons))
        by_start[IDX[s]].append(w)
        exact[(IDX[s], m)].append(w)
    for lst in by_start.values():
        lst.sort(key=lambda w: -w[4])
    return by_start, exact


def initial(first_word):
    cons = ''.join(NORM.get(c, c) for c in first_word if c != 'ー')
    used = mask_of(cons)
    last = first_word[-1]
    return used, IDX[NORM.get(last, last)]


ALL = (1 << len(KANA)) - 1
N = IDX['ん']


def popcount(x):
    return bin(x).count('1')


def min_search(by_start, exact, used0, link0, width=400, topk=60, maxdepth=9, mindepth=0):
    """ビーム探索で使い切り最少語数の目安を探す。"""
    rem0 = ALL & ~used0
    beam = {(rem0, link0): []}
    for depth in range(1, maxdepth + 1):
        # 完了チェック: 次の1語で使い切れるか
        for (rem, link), path in beam.items():
            for w in exact.get((link, rem), []):
                if len(path) + 1 >= mindepth:
                    return path + [w]
        nxt = {}
        for (rem, link), path in beam.items():
            cnt = 0
            for w in by_start.get(link, []):
                if w[0] & ~rem:
                    continue
                e = w[1]
                nrem = rem & ~w[0]
                if e == N and nrem != 0:
                    continue
                if nrem == 0:
                    if len(path) + 1 >= mindepth:
                        return path + [w]
                    continue
                key = (nrem, e)
                if key not in nxt:
                    nxt[key] = path + [w]
                cnt += 1
                if cnt >= topk:
                    break
        # 残りが少ないもの優先。同点はランダム
        items = list(nxt.items())
        random.shuffle(items)
        items.sort(key=lambda kv: popcount(kv[0][0]))
        beam = dict(items[:width])
        if not beam:
            return None
    return None


def max_search(by_start, used0, link0, tries=300):
    """単語数をできるだけ増やす(使い切らなくてよい)。2文字消費の語を優先して貪欲+ランダム。"""
    best = []
    rem0 = ALL & ~used0
    for _ in range(tries):
        rem, link, path = rem0, link0, []
        while True:
            cands = [w for w in by_start.get(link, []) if not (w[0] & ~rem) and w[1] != N]
            if not cands:
                break
            small = [w for w in cands if w[4] == 2] or cands
            # 出口(次に続けられる)がある語を優先
            random.shuffle(small)
            pick = None
            for w in small[:50]:
                nrem = rem & ~w[0]
                if any(not (x[0] & ~nrem) and x[1] != N for x in by_start.get(w[1], [])[-400:]):
                    pick = w
                    break
            if pick is None:
                pick = small[0]
            path.append(pick)
            rem &= ~pick[0]
            link = pick[1]
        if len(path) > len(best):
            best = path
    return best


def show(path):
    return ' → '.join(f'{w[3]}({w[2]})' for w in path)


FILTERS = {
    '普通名詞のみ': lambda p2, p3: p2 == '普通名詞',
    '普通名詞+地名': lambda p2, p3: p2 == '普通名詞' or (p2 == '固有名詞' and p3 == '地名'),
    '名詞すべて': lambda p2, p3: True,
}

if __name__ == '__main__':
    first = sys.argv[1] if len(sys.argv) > 1 else 'たからもの'
    variant = sys.argv[2] if len(sys.argv) > 2 else 'core'
    random.seed(1)
    used0, link0 = initial(first)
    print(f'お題: {first} → 「{KANA[link0]}」から / 残り {45 - popcount(used0)} 字')
    for name, flt in FILTERS.items():
        by_start, exact = load(variant, flt)
        n = sum(len(v) for v in by_start.values())
        mn = min_search(by_start, exact, used0, link0)
        mx = max_search(by_start, used0, link0)
        print(f'\n【{name}】語数 {n}')
        print('  最少(見つかった範囲):', (f'{len(mn)}語: ' + show(mn)) if mn else '見つからず')
        print('  最多(見つかった範囲):', f'{len(mx)}語: ' + show(mx))
