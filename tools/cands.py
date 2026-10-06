"""お題の候補を検証する。読み(ひらがな)を与えると、封じられる文字・残り・最大語数・使い切れるか・最初の文字の取りやすさを出す。

使い方: python tools/cands.py <結果の出力先.jsonl>
"""
import os, sys, json, collections, random, time
HERE = os.path.dirname(__file__); sys.path.insert(0, HERE)
from prep import convert, NORM, KANA_SET
from solve import mask_of, IDX, min_search, max_search, popcount, ALL, N

CANDS = [
    # 食べ物
    ('カレーライス', 'かれーらいす'), ('ハンバーグ', 'はんばーぐ'), ('オムライス', 'おむらいす'), ('チョコレート', 'ちょこれーと'),
    ('ソフトクリーム', 'そふとくりーむ'), ('ホットケーキ', 'ほっとけーき'), ('スパゲッティ', 'すぱげってぃ'), ('ミルクティー', 'みるくてぃー'),
    ('みたらしだんご', 'みたらしだんご'), ('回転寿司', 'かいてんずし'), ('お好み焼き', 'おこのみやき'), ('ナポリタン', 'なぽりたん'),
    ('フルーツサンド', 'ふるーつさんど'), ('メロンパン', 'めろんぱん'),
    # もの・場所・作品
    ('東京スカイツリー', 'とうきょうすかいつりー'), ('ジェットコースター', 'じぇっとこーすたー'), ('観覧車', 'かんらんしゃ'),
    ('スマートフォン', 'すまーとふぉん'), ('ニンテンドースイッチ', 'にんてんどーすいっち'), ('プレイステーション', 'ぷれいすてーしょん'),
    ('ポケットモンスター', 'ぽけっともんすたー'), ('スーパーマリオ', 'すーぱーまりお'), ('ドラゴンボール', 'どらごんぼーる'),
    ('名探偵コナン', 'めいたんていこなん'), ('サザエさん', 'さざえさん'), ('ちびまる子ちゃん', 'ちびまるこちゃん'), ('ドラえもん', 'どらえもん'),
    ('ハリーポッター', 'はりーぽったー'), ('ウルトラマン', 'うるとらまん'), ('仮面ライダー', 'かめんらいだー'), ('機動戦士ガンダム', 'きどうせんしがんだむ'),
    # 行事
    ('花火大会', 'はなびたいかい'), ('運動会', 'うんどうかい'), ('文化祭', 'ぶんかさい'), ('クリスマスツリー', 'くりすますつりー'),
    ('お正月', 'おしょうがつ'), ('初日の出', 'はつひので'), ('大掃除', 'おおそうじ'), ('ハロウィン', 'はろうぃん'), ('七五三', 'しちごさん'),
    ('豆まき', 'まめまき'), ('桜前線', 'さくらぜんせん'), ('夏祭り', 'なつまつり'), ('ゴールデンウィーク', 'ごーるでんうぃーく'), ('バレンタインデー', 'ばれんたいんでー'),
    # 文字の仕掛け(お題の文字そのものが、仕掛けになる)
    ('あいうえお', 'あいうえお'), ('かきくけこ', 'かきくけこ'), ('さしすせそ', 'さしすせそ'), ('たちつてと', 'たちつてと'), ('なにぬねの', 'なにぬねの'),
    ('はひふへほ', 'はひふへほ'), ('まみむめも', 'まみむめも'), ('らりるれろ', 'らりるれろ'), ('いろはにほへと', 'いろはにほへと'), ('五十音', 'ごじゅうおん'),
    ('しりとり', 'しりとり'), ('節約しりとり', 'せつやくしりとり'), ('ひらがな', 'ひらがな'), ('日本語', 'にほんご'),
]

by_start = collections.defaultdict(list); exact = collections.defaultdict(list)
for line in open(os.path.join(HERE, '..', 'data', 'words.txt'), encoding='utf-8'):
    r, t = line.rstrip('\n').split('\t')
    if int(t) == 3:
        continue
    s, cons, e = convert(r); m = mask_of(cons); w = (m, IDX[e], r, r, len(cons))
    by_start[IDX[s]].append(w); exact[(IDX[s], m)].append(w)
for l in by_start.values():
    l.sort(key=lambda w: -w[4])

out = open(sys.argv[1], 'w', encoding='utf-8')
random.seed(1)
for disp, word in CANDS:
    t0 = time.time()
    letters = [NORM.get(c, c) for c in word if NORM.get(c, c) in KANA_SET]
    used = 0
    for c in letters:
        used |= 1 << IDX[c]
    link_raw = word[-1]
    link = NORM.get(link_raw, link_raw)
    if link == 'ー':
        prev = [c for c in word if c != 'ー'][-1]
        link = NORM.get(prev, prev)  # 長音で終わるときは、母音(近似)
    rec = {'disp': disp, 'word': word, 'sealed': ''.join(sorted(set(letters))), 'n_sealed': popcount(used), 'left': 45 - popcount(used),
           'M': (45 - popcount(used)) // 2, 'link': link}
    if link == 'ん' or link not in IDX:
        rec.update(ok=False, why='最初の文字が「ん」(続けられない)')
        out.write(json.dumps(rec, ensure_ascii=False) + '\n'); out.flush(); continue
    rem = ALL & ~used
    # 最初の文字から始められる言葉の数(多いほど、始めやすい)
    rec['starts'] = sum(1 for w in by_start.get(IDX[link], []) if not (w[0] & ~rem) and w[1] != N)
    sol = min_search(by_start, exact, used, IDX[link], width=250, topk=50, maxdepth=14)
    rec['clear'] = len(sol) if sol else None
    mx = max_search(by_start, used, IDX[link], tries=150)
    rec['maxfound'] = len(mx)
    rec['ok'] = bool(sol)
    rec['sec'] = round(time.time() - t0, 1)
    out.write(json.dumps(rec, ensure_ascii=False) + '\n'); out.flush()
out.close()
print('done')
