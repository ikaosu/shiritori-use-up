"""SudachiDict の CSV から、ゲーム用の単語リストを作る。

ルール(確定分):
- 使い切り対象は 45 字(あ〜ん から「を」を除く)
- 濁音・半濁音は清音、小書きは大書きとして扱う
- 長音「ー」は消費しない。語末が「ー」なら直前の文字の母音で次を始める
- 3 文字以上(長音を含めて数える)
- 各単語は 2 文字目以降を消費する(頭の文字は前の単語から引き継ぐだけ)
- 1 つの単語の中で同じ文字を 2 回消費できない
- 「を」を含む語は使わない
"""
import csv, json, sys, collections, os

CACHE = os.path.join(os.path.dirname(__file__), '..', '.cache')
FILES = ['small_lex.csv', 'core_lex.csv', 'notcore_lex.csv']

KANA = list('あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわん')
KANA_SET = set(KANA)

# 濁音・半濁音・小書き → 清音・大書き
NORM = {}
for a, b in zip('がぎぐげござじずぜぞだぢづでどばびぶべぼ', 'かきくけこさしすせそたちつてとはひふへほ'):
    NORM[a] = b
for a, b in zip('ぱぴぷぺぽ', 'はひふへほ'):
    NORM[a] = b
for a, b in zip('ぁぃぅぇぉっゃゅょゎゔ', 'あいうえおつやゆよわう'):
    NORM[a] = b

VOWEL = {}
for row, v in [('あかさたなはまやらわ', 'あ'), ('いきしちにひみり', 'い'), ('うくすつぬふむゆる', 'う'),
               ('えけせてねへめれ', 'え'), ('おこそとのほもよろ', 'お')]:
    for c in row:
        VOWEL[c] = v


def kata2hira(s):
    out = []
    for ch in s:
        o = ord(ch)
        if 0x30A1 <= o <= 0x30F6:
            out.append(chr(o - 0x60))
        elif ch == 'ー':
            out.append('ー')
        else:
            return None
    return ''.join(out)


def convert(reading):
    """読み(ひらがな+ー)を (start, consumed, end) に。使えない語は None。"""
    if len(reading) < 3 or reading[0] == 'ー':
        return None
    units = []
    for ch in reading:
        if ch == 'ー':
            units.append('ー')
            continue
        ch = NORM.get(ch, ch)
        if ch not in KANA_SET:
            return None
        units.append(ch)
    if 'を' in reading:
        return None
    start = units[0]
    consumed = [u for u in units[1:] if u != 'ー']
    if len(set(consumed)) != len(consumed):
        return None
    if len(consumed) < 2:
        return None
    # 末尾
    if units[-1] == 'ー':
        prev = [u for u in units if u != 'ー'][-1]
        if prev not in VOWEL:
            return None
        end = VOWEL[prev]
    else:
        end = units[-1]
    return start, ''.join(consumed), end


def load(variant):
    """variant: small / core / full"""
    files = {'small': FILES[:1], 'core': FILES[:2], 'full': FILES}[variant]
    words = {}   # reading -> (pos2, pos3, surface)
    stats = collections.Counter()
    for fn in files:
        with open(os.path.join(CACHE, fn), encoding='utf-8', newline='') as f:
            for row in csv.reader(f):
                if len(row) < 12 or row[5] != '名詞':
                    continue
                p2, p3 = row[6], row[7]
                stats[(p2, p3)] += 1
                r = kata2hira(row[11])
                if r is None:
                    continue
                if r not in words:
                    words[r] = (p2, p3, row[0])
    return words, stats


if __name__ == '__main__':
    variant = sys.argv[1] if len(sys.argv) > 1 else 'core'
    words, stats = load(variant)
    print(f'[{variant}] 名詞の読み(重複除く): {len(words)}')
    print('品詞内訳(行数, 上位):')
    for (p2, p3), n in stats.most_common(12):
        print(f'  {p2}/{p3}: {n}')
    ok = {}
    for r, meta in words.items():
        c = convert(r)
        if c:
            ok[r] = (c, meta)
    print(f'ルールを満たす語: {len(ok)}')
    by_pos = collections.Counter(m[1][0] + '/' + m[1][1] for m in ok.values())
    print('  内訳:', by_pos.most_common(8))
    ends_n = sum(1 for c, m in ok.values() if c[2] == 'ん')
    print(f'  「ん」で終わる語: {ends_n}')
    starts = collections.Counter(c[0] for c, m in ok.values())
    print('  頭文字ごとの語数(少ない順10):', sorted(starts.items(), key=lambda x: x[1])[:10])
    print('  頭文字ごとの語数(多い順5):', starts.most_common(5))
    lens = collections.Counter(len(c[1]) + 1 for c, m in ok.values())
    print('  読みの長さ(長音除く)分布:', sorted(lens.items()))
    out = os.path.join(CACHE, f'words_{variant}.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump([[r, c[0], c[1], c[2], m[0], m[1], m[2]] for r, (c, m) in ok.items()], f, ensure_ascii=False)
    print('->', out)
