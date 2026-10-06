CREATE TABLE IF NOT EXISTS scores (
  day     INTEGER NOT NULL,   -- JST の日付(1970-01-01 からの日数)
  mode    INTEGER NOT NULL,   -- 1: 節約, 2: ハード(使い切り)
  device  TEXT    NOT NULL,   -- 端末ごとの乱数ID(1日・1モードにつき1件)
  name    TEXT    NOT NULL,
  n       INTEGER NOT NULL,   -- つないだ語数
  chain   TEXT    NOT NULL,   -- つないだ言葉(JSON配列)。後から確かめるため
  created INTEGER NOT NULL,   -- 記録した時刻(ミリ秒)。同点のときは早い方が上
  PRIMARY KEY (day, mode, device)
);
CREATE INDEX IF NOT EXISTS idx_scores_rank ON scores (day, mode, n DESC, created);
