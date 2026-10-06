-- ハードも、使い切れなかった記録を載せる(のこり何文字まで行ったか)。少ないほど上位
ALTER TABLE scores ADD COLUMN rest INTEGER;
-- これまでのハードの記録は、すべて使い切り成功
UPDATE scores SET rest = 0 WHERE mode = 2;
CREATE INDEX idx_scores_rest ON scores (day, prompt, mode, rest, created);
