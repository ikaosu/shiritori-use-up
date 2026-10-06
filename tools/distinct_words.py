"""SudachiDict の名詞から、「同じ文字を2回使わない」長い単語を探す。長音は数えない。濁音・小さい字は、清音・大きい字として数える。
お題の候補探し用(よく知られているかは、人が見て選ぶ)。
"""
import csv, os, sys, collections
HERE = os.path.dirname(__file__); sys.path.insert(0, HERE)
from prep import NORM, KANA_SET, kata2hira, CACHE

MINLEN = int(sys.argv[1]) if len(sys.argv) > 1 else 9
seen = {}
for fn in (['small_lex.csv'] if os.environ.get('ONLY_SMALL') else ['small_lex.csv', 'core_lex.csv']):
    with open(os.path.join(CACHE, fn), encoding='utf-8', newline='') as f:
        for row in csv.reader(f):
            if len(row) < 12 or row[5] != '名詞' or row[6] not in ('普通名詞',):
                continue
            r = kata2hira(row[11])
            if not r or r.endswith('ん') or r.endswith('ン'):
                continue
            letters = [NORM.get(c, c) for c in r if c != 'ー']
            if any(c not in KANA_SET for c in letters) or 'を' in letters:
                continue
            if len(set(letters)) != len(letters) or len(letters) < MINLEN:
                continue
            surf, cost = row[0], int(row[3])
            if r not in seen or cost < seen[r][1]:
                seen[r] = (surf, cost, row[7])
rows = sorted(seen.items(), key=(lambda kv: kv[1][1]) if os.environ.get('BY_COST') else (lambda kv: (-len([c for c in kv[0] if c != 'ー']), kv[1][1])))
print(f'同じ文字を2回使わない名詞(長音を除いて{MINLEN}文字以上、「ん」で終わらない): {len(rows)} 語')
by = collections.Counter(len([c for c in r if c != 'ー']) for r, _ in rows)
print('文字数ごと:', dict(sorted(by.items(), reverse=True)))
for r, (s, c, sub) in rows[:int(sys.argv[2]) if len(sys.argv) > 2 else 120]:
    print(f'{len([x for x in r if x != "ー"]):>2} {s}　{r}　(コスト{c})')
