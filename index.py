#!/usr/bin/python
"""Build almost the dumbest possible full-text-search index.

Not sure if this is something I want to do for real; right now it
takes 600ms (10% of total rebuild time) and generates 190K of index,
gzipped (30% of the total).

"""

import os
import re
import sys


def go():
    files = [f for f in os.listdir('markdown')
             if not f.endswith('~') or f.startswith('#') or f.startswith('.')]
    idx = {f: set(word.lower()
                  for line in open('markdown/' + f)
                  for word in re.findall(r'\w+', line))
           for f in files}
    all_words = set().union(*idx.values())
    sys.stderr.write('%d words\n' % len(all_words))
    inverted = {w: set(f for f in idx if w in idx[f])
                for w in all_words}
    sys.stderr.write('%d in more than one note\n' %
                     sum(1 for w in inverted if len(inverted[w]) > 1))
    sys.stderr.write("Mean of %.2f unique in each note\n" %
                     (sum(len(words) for words in idx.values()) / len(idx)))
    for f in sorted(files):
        print('%s: %s' % (f, ' '.join(sorted(idx[f]))))

if __name__ == '__main__':
    go()
