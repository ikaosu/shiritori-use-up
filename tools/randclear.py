"""お題を与えて、いろいろな語数で使い切れる列を、ランダムに探す。検証用。"""
import os, sys, collections, random, time
HERE = os.path.dirname(__file__); sys.path.insert(0, HERE)
from prep import convert
from solve import mask_of, IDX, initial, popcount, N, ALL
by_start = collections.defaultdict(list); exact = collections.defaultdict(list)
for line in open(os.path.join(HERE, '..', 'data', 'words.txt'), encoding='utf-8'):
    r, t = line.rstrip('\n').split('\t')
    if int(t) == 3: continue
    s, cons, e = convert(r); m = mask_of(cons); w = (m, IDX[e], r, r, len(cons))
    by_start[IDX[s]].append(w); exact[(IDX[s], m)].append(w)
random.seed(int(sys.argv[2]) if len(sys.argv) > 2 else 1)
u, l = initial(sys.argv[1]); rem0 = ALL & ~u
found = {}
t0 = time.time()
while time.time() - t0 < float(sys.argv[3]) if len(sys.argv) > 3 else 60:
    rem, link, path = rem0, l, []
    while True:
        # 残りが少なくなったら、ちょうど使い切れる語を探す
        done = None
        for w in exact.get((link, rem), []):
            done = path + [w]; break
        if done:
            found.setdefault(len(done), done); break
        cands = [w for w in by_start.get(link, []) if not (w[0] & ~rem) and w[1] != N and 2 <= w[4] <= 4]
        if not cands or popcount(rem) < 2: break
        w = random.choice(cands)
        path.append(w); rem &= ~w[0]; link = w[1]
for k in sorted(found):
    print(k, ' '.join(x[2] for x in found[k]))
