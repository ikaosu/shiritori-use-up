-- 管理者画面から決める、日ごとのお題(予約)。その日だけ、data/prompts.json のお題より優先される
CREATE TABLE day_prompts (
  day INTEGER PRIMARY KEY,
  word TEXT NOT NULL,
  link TEXT NOT NULL,
  disp TEXT,
  note TEXT,
  rule TEXT,
  ban TEXT,
  seal TEXT,
  created INTEGER NOT NULL
);
