"""お題を与えて、使い切りの1例(辞書は人名を除く)を出力する。検証用。"""
import os, sys, collections
HERE = os.path.dirname(__file__); sys.path.insert(0, HERE)
from prep import convert
from solve import mask_of, IDX, min_search, initial
import random
random.seed(3)
by_start = collections.defaultdict(list); exact = collections.defaultdict(list)
for line in open(os.path.join(HERE, '..', 'data', 'words.txt'), encoding='utf-8'):
    r, t = line.rstrip('\n').split('\t')
    if int(t) == 3: continue
    s, cons, e = convert(r); m = mask_of(cons); w = (m, IDX[e], r, r, len(cons))
    by_start[IDX[s]].append(w); exact[(IDX[s], m)].append(w)
for l in by_start.values(): l.sort(key=lambda w: -w[4])
u, l = initial(sys.argv[1])
p = min_search(by_start, exact, u, l, width=250, topk=50, maxdepth=10)
print(' '.join(w[2] for w in p))
