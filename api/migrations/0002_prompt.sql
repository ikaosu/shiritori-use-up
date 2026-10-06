-- 集計を「日 × お題」ごとに分ける(同じ日にお題を差し替えても、記録が混ざらないように)
ALTER TABLE scores RENAME TO scores_old;
CREATE TABLE scores (
  day     INTEGER NOT NULL,
  prompt  TEXT    NOT NULL,   -- お題(読み)。記録したときの今日のお題
  mode    INTEGER NOT NULL,
  device  TEXT    NOT NULL,
  name    TEXT    NOT NULL,
  n       INTEGER NOT NULL,
  chain   TEXT    NOT NULL,
  created INTEGER NOT NULL,
  PRIMARY KEY (day, prompt, mode, device)
);
-- 2026-10-06(20732)は、お題を差し替える前の記録だけが入っている(お題は「こもれび」だった)
INSERT INTO scores (day, prompt, mode, device, name, n, chain, created)
  SELECT day, CASE WHEN day = 20732 THEN 'こもれび' ELSE '' END, mode, device, name, n, chain, created FROM scores_old;
DROP TABLE scores_old;
CREATE INDEX idx_scores_rank ON scores (day, prompt, mode, n DESC, created);
