# 節約しりとり

使った文字は、二度と使えない。お題の言葉で消えた文字を避けながら、しりとりをどこまでつなげられるか。

- `index.html` … アプリ本体。タイトル → ゲーム → 結果の3画面(遊び方・ランキング・設定は下から出るシート)
  - **節約(ふつう)**: できるだけ多くの言葉をつなぐ。語数で称号がつく
  - **ハード**: 50音をぜんぶ使い切れたら成功(語数は結果に出すだけ)
- `play.html` … 以前のURL用。`index.html` へ移すだけ
- `api/` … ランキングAPI(Cloudflare Workers + D1)。送られた「つないだ言葉の列」を、お題・ルール・辞書で検証してから記録する
- `og.png` … 共有時の画像(`tools/og.html` を画面に書き出して作る)

## 動かす
`data/` を読み込むので、サーバー経由で開く。

    python -m http.server 8000   # → http://localhost:8000/

## 辞書データを作り直す
SudachiDict(Apache 2.0)の CSV を `.cache/` に置いて `python tools/build.py`。
お題の検証は `python tools/curate.py`(使い切りの解がある語だけを採用)。

## ルール
- お題の言葉の文字は、最初から消えている
- 言葉の2文字目以降が消える(頭の文字は前の言葉から引き継ぐ)
- 長音を除いて3文字以上(各言葉が最低2文字を消費する。1文字だけ消す短い言葉の連打を防ぐため)、「を」は対象外(対象は45字)
- 濁音・半濁音は清音、小さい字は大きい字として数える。長音は消さず、次は直前の母音から
- 「ん」で終わると続けられない(ハードでは使い切る最後の1語だけ可)
- 入力は、50音表のタイルをタップして言葉をつくる(PCではキーボードも可)

## 辞書の出典
SudachiDict (Works Applications, Apache License 2.0)。公開時は帰属表示を出している。上流データの条件は、公開前に確認が必要。

## ランキングAPI(`api/`)
- 1日・1モード・1端末につき1件。節約は語数が多い方を残す。同じ語数なら早く記録した方が上
- 辞書は、秘密の値(`DICT_SALT`)を混ぜたハッシュ(`api/dict.bin`)で持つ。`python tools/build_dict_bin.py` で作る。`DICT_SALT` と `ADMIN_TOKEN` は `api/.dev.vars`(リポジトリに入れない)と `wrangler secret put` に置く
- 手元で動かす: `wrangler d1 migrations apply shiritori --local -c api/wrangler.toml` → `wrangler dev -c api/wrangler.toml`。画面は `?api=http://127.0.0.1:8787` を付けて開く。`?dev` を付けると、設定に開発用(辞書の範囲・お題の切り替え)が出る
- 公開: `wrangler deploy -c api/wrangler.toml`
- 管理: 画面は `https://ikaosu.github.io/shiritori-use-up/#admin`(合言葉を入れると、日ごと・お題ごと・モードごとに、みんなの解答が見られて、記録を消せる)。API は `GET /api/v1/admin/days`・`/admin/list?day=`・`POST /admin/delete`(ヘッダ `x-admin-token`)

## テストの決まり
- **本番のデータベースには、テストの記録を書き込まない。** テストは、手元の `wrangler dev`(ローカルのD1)に向けて行う。画面は `?api=http://127.0.0.1:8787` を付けて開く
- どうしても本番に入れるときは、名前を「TEST-」で始める。消すのも、その目印があるものだけ。**本物のプレイヤーの記録は、確認なしで消さない**
- ハードは、使い切れなくても記録される(のこり文字が少ないほど上位)。節約は、語数が最大(理論値)のとき、印が付く
