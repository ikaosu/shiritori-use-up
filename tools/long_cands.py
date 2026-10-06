"""よく知られた長い言葉を挙げて、「同じ文字を2回使わない(長音は数えない)」ものだけを残し、ソルバーで遊べるか確かめる。"""
import os, sys, json, collections, random, time
HERE = os.path.dirname(__file__); sys.path.insert(0, HERE)
from prep import convert, NORM, KANA_SET
from solve import mask_of, IDX, min_search, max_search, popcount, ALL, N

CANDS = """
未確認飛行物体:みかくにんひこうぶったい|ソーシャルネットワーキングサービス:そーしゃるねっとわーきんぐさーびす|天空の城ラピュタ:てんくうのしろらぴゅた
ユニバーサルスタジオ:ゆにばーさるすたじお|ラグビーワールドカップ:らぐびーわーるどかっぷ|ゲームボーイアドバンス:げーむぼーいあどばんす
チョコミントアイス:ちょこみんとあいす|バニラアイスクリーム:ばにらあいすくりーむ|フィギュアスケート:ふぃぎゅあすけーと|鬼滅の刃:きめつのやいば
ブラックサンダー:ぶらっくさんだー|ポカリスエット:ぽかりすえっと|メリーゴーラウンド:めりーごーらうんど|ディズニーランド:でぃずにーらんど
ジェットコースター:じぇっとこーすたー|いろはにほへとちりぬる:いろはにほへとちりぬる|日本レコード大賞:にほんれこーどたいしょう
アメリカンフットボール:あめりかんふっとぼーる|コンパクトデジタルカメラ:こんぱくとでじたるかめら|ランダムアクセスメモリー:らんだむあくせすめもりー
ローカルエリアネットワーク:ろーかるえりあねっとわーく|ウェアラブルデバイス:うぇあらぶるでばいす|東京スカイツリー:とうきょうすかいつりー
ナイアガラの滝:ないあがらのたき|自由の女神:じゆうのめがみ|アンコールワット:あんこーるわっと|スマートウォッチ:すまーとうぉっち
ポケットモンスター:ぽけっともんすたー|ニンテンドースイッチ:にんてんどーすいっち|機動戦士ガンダム:きどうせんしがんだむ
ゴールデンウィーク:ごーるでんうぃーく|ミスタードーナツ:みすたーどーなつ|ファミリーマート:ふぁみりーまーと|カルピスソーダ:かるぴすそーだ
スーパーマーケット:すーぱーまーけっと|メロンクリームソーダ:めろんくりーむそーだ|チョコレートアイス:ちょこれーとあいす
ブルーベリーヨーグルト:ぶるーべりーよーぐると|スラムダンク:すらむだんく|ホームセンター:ほーむせんたー|ブラックホール:ぶらっくほーる
ロールプレイングゲーム:ろーるぷれいんぐげーむ|シミュレーションゲーム:しみゅれーしょんげーむ|アクションゲーム:あくしょんげーむ
プロ野球選手:ぷろやきゅうせんしゅ|オリンピックメダル:おりんぴっくめだる|ワールドベースボールクラシック:わーるどべーすぼーるくらしっく
スイートポテト:すいーとぽてと|ミルクレープ:みるくれーぷ|キャラメルプリン:きゃらめるぷりん|チーズケーキ:ちーずけーき
カフェオレ:かふぇおれ|カプチーノ:かぷちーの|ホットコーヒー:ほっとこーひー|アイスコーヒー:あいすこーひー|レモンティー:れもんてぃー
フルーツパフェ:ふるーつぱふぇ|プリンアラモード:ぷりんあらもーど|ティラミス:てぃらみす|ミルフィーユ:みるふぃーゆ
キャンプファイヤー:きゃんぷふぁいやー|ウォータースライダー:うぉーたーすらいだー|ビーチバレーボール:びーちばれーぼーる
スケートボード:すけーとぼーど|サーフィン:さーふぃん|スノーボード:すのーぼーど|アイスホッケー:あいすほっけー
ハロウィンパーティー:はろうぃんぱーてぃー|クリスマスケーキ:くりすますけーき|バレンタインチョコ:ばれんたいんちょこ
お花見弁当:おはなみべんとう|七夕飾り:たなばたかざり|盆踊り大会:ぼんおどりたいかい|紅白歌合戦:こうはくうたがっせん
大晦日:おおみそか|年賀状:ねんがじょう|お年玉:おとしだま|除夜の鐘:じょやのかね|初詣:はつもうで
スマートフォンケース:すまーとふぉんけーす|モバイルバッテリー:もばいるばってりー|ワイヤレスイヤホン:わいやれすいやほん
ノートパソコン:のーとぱそこん|ゲーミングパソコン:げーみんぐぱそこん|デスクトップパソコン:ですくとっぷぱそこん
ドラゴンクエスト:どらごんくえすと|ファイナルファンタジー:ふぁいなるふぁんたじー|スーパーマリオブラザーズ:すーぱーまりおぶらざーず
ゼルダの伝説:ぜるだのでんせつ|星のカービィ:ほしのかーびぃ|どうぶつの森:どうぶつのもり|大乱闘スマッシュブラザーズ:だいらんとうすまっしゅぶらざーず
ハリーポッターと賢者の石:はりーぽったーとけんじゃのいし|ロードオブザリング:ろーどおぶざりんぐ|スターウォーズ:すたーうぉーず
ジュラシックパーク:じゅらしっくぱーく|ターミネーター:たーみねーたー|バックトゥザフューチャー:ばっくとぅざふゅーちゃー
ピタゴラスイッチ:ぴたごらすいっち|おかあさんといっしょ:おかあさんといっしょ|ひらけポンキッキ:ひらけぽんきっき
サザエさん:さざえさん|笑点:しょうてん|水曜どうでしょう:すいようどうでしょう|世界ふしぎ発見:せかいふしぎはっけん
""".replace('\n', '|').split('|')
cands = [c.split(':') for c in CANDS if ':' in c]

by_start = collections.defaultdict(list); exact = collections.defaultdict(list)
for line in open(os.path.join(HERE, '..', 'data', 'words.txt'), encoding='utf-8'):
    r, t = line.rstrip('\n').split('\t')
    if int(t) == 3: continue
    s, cons, e = convert(r); m = mask_of(cons); w = (m, IDX[e], r, r, len(cons))
    by_start[IDX[s]].append(w); exact[(IDX[s], m)].append(w)
for l in by_start.values(): l.sort(key=lambda w: -w[4])

passed, dropped = [], collections.Counter()
for disp, word in cands:
    letters = [NORM.get(c, c) for c in word if c != 'ー']
    if any(c not in KANA_SET for c in letters):
        dropped['未対応の文字'] += 1; continue
    if len(set(letters)) != len(letters):
        dropped['文字の重複'] += 1; continue
    if len(letters) < 7:
        dropped['短い(7字未満)'] += 1; continue
    if letters[-1] == 'ん':
        dropped['ん終わり'] += 1; continue
    passed.append((disp, word, letters))
print(f'挙げた {len(cands)} 個 → 文字が重複しない7字以上: {len(passed)} 個 / 除外: {dict(dropped)}\n', flush=True)

out = open(sys.argv[1], 'w', encoding='utf-8')
random.seed(1)
for disp, word, letters in sorted(passed, key=lambda t: -len(t[2])):
    used = 0
    for c in letters: used |= 1 << IDX[c]
    end = word[-1]
    link = (NORM.get([c for c in word if c != 'ー'][-1], [c for c in word if c != 'ー'][-1]) if end != 'ー' else None)
    if end == 'ー':  # 長音で終わる: 次は、直前の文字の母音から
        from solve import IDX as _I
        prev = NORM.get([c for c in word if c != 'ー'][-1], [c for c in word if c != 'ー'][-1])
        VOW = {}
        for row, v in [('あかさたなはまやらわ', 'あ'), ('いきしちにひみり', 'い'), ('うくすつぬふむゆる', 'う'), ('えけせてねへめれ', 'え'), ('おこそとのほもよろ', 'お')]:
            for c in row: VOW[c] = v
        link = VOW.get(prev, prev)
    rem = ALL & ~used
    starts = sum(1 for w in by_start.get(IDX[link], []) if not (w[0] & ~rem) and w[1] != N)
    sol = min_search(by_start, exact, used, IDX[link], width=250, topk=50, maxdepth=14)
    mx = max_search(by_start, used, IDX[link], tries=120)
    M = (45 - popcount(used)) // 2
    rec = dict(disp=disp, word=word, L=len(letters), left=45 - len(letters), M=M, link=link, starts=starts, clear=len(sol) if sol else None, maxfound=len(mx))
    out.write(json.dumps(rec, ensure_ascii=False) + '\n'); out.flush()
    print(f"{len(letters):>2}字 {disp:<14} 残り{45 - len(letters)} 最大{M}{'○' if len(mx) >= M else '△' + str(len(mx))} 使い切り{(str(len(sol)) + '語') if sol else '解なし'} 始め{starts:>5} →{link}", flush=True)
