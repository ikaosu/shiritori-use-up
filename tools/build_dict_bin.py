"""辞書(data/words.txt)を、秘密の値を混ぜたハッシュの並び(api/dict.bin)にする。

- 1語 = sha256(DICT_SALT + 読み) の先頭6バイト。小さい順に並べる(サーバーが二分探索する)
- DICT_SALT は api/.dev.vars に書く(リポジトリには入れない)。本番は `wrangler secret put DICT_SALT` で同じ値を入れる
  → ハッシュだけでは、辞書にない言葉(偽の言葉)を作れない
"""
import hashlib, os, re, secrets, sys

ROOT = os.path.join(os.path.dirname(__file__), '..')
VARS = os.path.join(ROOT, 'api', '.dev.vars')


def read_vars():
    d = {}
    if os.path.exists(VARS):
        for line in open(VARS, encoding='utf-8'):
            m = re.match(r'^([A-Z_]+)=(.*)$', line.strip())
            if m:
                d[m.group(1)] = m.group(2)
    return d


v = read_vars()
if 'DICT_SALT' not in v:
    v['DICT_SALT'] = secrets.token_hex(16)
    v.setdefault('ADMIN_TOKEN', secrets.token_hex(16))
    with open(VARS, 'w', encoding='utf-8', newline='\n') as f:
        for k, val in v.items():
            f.write(f'{k}={val}\n')
    print('api/.dev.vars を作成(DICT_SALT, ADMIN_TOKEN)')

salt = v['DICT_SALT']
keys = set()
for line in open(os.path.join(ROOT, 'data', 'words.txt'), encoding='utf-8'):
    r = line.split('\t', 1)[0]
    if r:
        keys.add(hashlib.sha256((salt + r).encode('utf-8')).digest()[:6])
data = b''.join(sorted(keys))
with open(os.path.join(ROOT, 'api', 'dict.bin'), 'wb') as f:
    f.write(data)
print('dict.bin:', len(keys), '語,', len(data), 'bytes')
