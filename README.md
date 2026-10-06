# 節約しりとり

使った文字は、二度と使えない。お題の言葉で消えた文字を避けながら、しりとりをどこまでつなげられるか。

- `index.html` … アプリ本体。タイトル → ゲーム → 結果の3画面(遊び方・ランキング・設定は下から出るシート)
- `play.html` … 以前のURL用。`index.html` へ移すだけ
- `api/` … ランキングAPI(Cloudflare Workers + D1)。送られた「つないだ言葉の列」を、お題・ルール・辞書で検証してから記録する
- `data/` … 辞書(`words.txt`)とお題(`prompts.json`)
- `og.png` … 共有時の画像(`tools/og.html` を画面に書き出して作る)

## 遊び方(仕様)
- お題の言葉の文字は、最初から消えている。言葉の2文字目以降が消える(頭の文字は前の言葉から引き継ぐ)
- 1回の挑戦が、**2つのランキング**に載る
  - **語数ランキング**: つないだ語数が多いほど上位。最大語数(理論値)のときは、印が付く
  - **使い切りランキング**: 全部の文字を使い切った人だけ。少ない語数ほど上位(同じなら、早く記録した方)
- 続けられなくなったら「ここで終わる」。全部使い切ると、自動で終わる
- 長音を除いて3文字以上(各言葉が最低2文字を消費する)、「を」は対象外(対象は45字)
- 濁音・半濁音は清音、小さい字は大きい字として数える。長音は消さず、次は直前の母音から
- 「ん」で終わると続けられない(そこで終わり)
- 入力は、50音表のタイルをタップして言葉をつくる(PCではキーボードも可)

## お題
- `data/prompts.json`。お題に `day`(その日だけ)・`note`(タイトルに出すひとこと)・`seal`(お題の文字のほかに、最初から封じる文字)を指定できる。`day` のない日は、日ごとの乱数で選ぶ
- 画面とサーバーに、同じ `idxForDay` がある(変えるときは、両方)

## 動かす
`data/` を読み込むので、サーバー経由で開く。

    python -m http.server 8000   # → http://localhost:8000/

手元のAPI: `wrangler d1 migrations apply shiritori --local -c api/wrangler.toml` → `wrangler dev -c api/wrangler.toml`。画面は `?api=http://127.0.0.1:8787` を付けて開く。`&day=20733` で日付を指定できる(API側は `.dev.vars` の `DAY_OVERRIDE`)。`?dev` を付けると、設定に開発用が出る。

## 辞書
SudachiDict(Apache 2.0)の CSV を `.cache/` に置いて `python tools/build.py`。お題の検証は `python tools/curate.py`。サーバー用は `python tools/build_dict_bin.py`(秘密の値 `DICT_SALT` を混ぜたハッシュにする)。

## ランキングAPI(`api/`)
- 1日・1お題・1端末につき、語数と使い切りの記録がそれぞれ1件
- 辞書は、`api/dict.bin`(ソルト入りハッシュ)。`DICT_SALT` と `ADMIN_TOKEN` は `api/.dev.vars`(リポジトリに入れない)と `wrangler secret put` に置く
- 公開: `wrangler deploy -c api/wrangler.toml`。データベースの変更は `api/migrations/`
- 管理: `https://ikaosu.github.io/shiritori-use-up/#admin`(合言葉を入れると、日ごと・お題ごとに、みんなの解答が見られて、記録を消せる)

## データ移行(2026-10-06、モードを1つにしたとき)
- 手順: 本番の控えを取る(`wrangler d1 export`) → `python tools/preview_migration.py <控え.sql>` で、移行後の姿を確認 → `python tools/gen_migration.py <控え.sql> <出力.sql>` で移行SQLを作る → 手元のD1(本番のコピー)で試す → 本番に `wrangler d1 execute --remote --file` → もう一度控えを取って、同じ移行で変更が0文になることを確かめる
- 移行は、追加と補う更新だけ(記録は消さない)。何度実行しても同じ結果になる

## テストの決まり
- **本番のデータベースには、テストの記録を書き込まない。** テストは、手元の `wrangler dev`(ローカルのD1)に向けて行う
- どうしても本番に入れるときは、名前を「TEST-」で始める。消すのも、その目印があるものだけ。**本物のプレイヤーの記録は、確認なしで消さない**

## 辞書の出典
SudachiDict (Works Applications, Apache License 2.0)。公開時は帰属表示を出している。上流データの条件は、公開前に確認が必要。
