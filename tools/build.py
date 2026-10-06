"""ゲーム用データを作る。

出力:
  data/words.txt          1行 = 「読み<TAB>種別」。種別 0:普通名詞 1:地名 2:その他の固有名詞 3:人名
  .cache/prompt_cands.json  お題の候補(普通名詞・5字・全部ちがう字・よく使われる語)
"""
import csv, os, re, json, sys, collections

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
from prep import convert, kata2hira, FILES, CACHE, KANA_SET

OUT = os.path.join(HERE, '..', 'data')
os.makedirs(OUT, exist_ok=True)

ASCII_RE = re.compile(r'[A-Za-z0-9０-９Ａ-Ｚａ-ｚ]')
HIRA_PLAIN = re.compile(r'^[あ-ん]+$')
SMALL = set('ぁぃぅぇぉっゃゅょゎ')

words = {}   # reading -> tag
cands = {}   # reading -> (cost, surface)

for fn in FILES[:2]:  # small + core
    with open(os.path.join(CACHE, fn), encoding='utf-8', newline='') as f:
        for row in csv.reader(f):
            if len(row) < 12 or row[5] not in ('名詞',):
                continue
            surf = row[0]
            if ASCII_RE.search(surf):
                continue
            p2, p3 = row[6], row[7]
            if p2 in ('普通名詞', '数詞'):
                tag = 0
            elif p2 == '固有名詞':
                tag = 1 if p3 == '地名' else 3 if p3 == '人名' else 2
            else:
                continue
            r = kata2hira(row[11])
            if r is None or convert(r) is None:
                continue
            if r not in words or tag < words[r]:
                words[r] = tag
            if tag == 0 and p3 == '一般' and HIRA_PLAIN.search(r) and len(r) == 5 \
                    and not (set(r) & SMALL) and len(set(r)) == 5 and r[-1] != 'ん' and '' != surf:
                try:
                    cost = int(row[3])
                except ValueError:
                    continue
                if r not in cands or cost < cands[r][0]:
                    cands[r] = (cost, surf)

with open(os.path.join(OUT, 'words.txt'), 'w', encoding='utf-8', newline='\n') as f:
    for r, t in sorted(words.items()):
        f.write(f'{r}\t{t}\n')
print('words.txt:', len(words), collections.Counter(words.values()))

ranked = sorted(cands.items(), key=lambda kv: kv[1][0])[:1500]
json.dump([[r, c, s] for r, (c, s) in ranked], open(os.path.join(CACHE, 'prompt_cands.json'), 'w', encoding='utf-8'), ensure_ascii=False)
print('お題候補:', len(cands))
print(' '.join(f'{s}({r})' for r, (c, s) in ranked[:60]))
