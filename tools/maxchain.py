"""お題を与えて、できるだけ長い(最大語数に近い)しりとりを探して出力する。検証用。"""
import os, sys, collections, random
HERE = os.path.dirname(__file__); sys.path.insert(0, HERE)
from prep import convert
from solve import mask_of, IDX, max_search, initial
by_start = collections.defaultdict(list)
for line in open(os.path.join(HERE, '..', 'data', 'words.txt'), encoding='utf-8'):
    r, t = line.rstrip('\n').split('\t')
    if int(t) == 3: continue
    s, cons, e = convert(r); w = (mask_of(cons), IDX[e], r, r, len(cons))
    by_start[IDX[s]].append(w)
for l in by_start.values(): l.sort(key=lambda w: -w[4])
random.seed(int(sys.argv[2]) if len(sys.argv) > 2 else 1)
u, l = initial(sys.argv[1])
best = max_search(by_start, u, l, tries=int(sys.argv[3]) if len(sys.argv) > 3 else 400)
print(len(best), ' '.join(w[2] for w in best))
