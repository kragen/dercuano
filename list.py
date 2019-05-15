#!/usr/bin/python
from __future__ import print_function
import os
import stat


if __name__ == '__main__':
    files = os.listdir('.')
    sizes = {fn: os.lstat(fn).st_size for fn in files}
    existing = set(os.listdir(os.path.split(__file__)[0]+'/markdown'))
    for fn in sorted(files, key=sizes.__getitem__):
        if not fn.endswith('~'):
            print("%8d %s %s" % (sizes[fn], '*' if fn in existing else ' ', fn))
