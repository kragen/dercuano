#!/usr/bin/python
"""Build almost the dumbest possible full-text-search index.

Not sure if this is something I want to do for real; right now it
takes 600ms (10% of total rebuild time) and generates 190K of index,
gzipped (30% of the total).

"""

import os
import re


def go():
    files = [f for f in os.listdir('markdown')
             if not f.endswith('~') or f.startswith('#') or f.startswith('.')]
    idx = {f: sorted(set(word.lower()
                         for line in open('markdown/' + f)
                         for word in re.findall(r'\w+', line)))
           for f in files}
    for f in sorted(files):
        print('%s: %s' % (f, ' '.join(idx[f])))

if __name__ == '__main__':
    go()
