#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Quick script to add a note."""
import os
import shutil
import sys

import when


def add(filename):
    me = os.path.split(__file__)[0]
    dest_dir = me + '/markdown/'
    if os.path.exists(dest_dir + filename):
        sys.stderr.write("%r already exists\n" % filename)
        return
    shutil.copy(filename, dest_dir)
    formatted = when.format_when(filename, *when.when(filename))
    sys.stdout.write(formatted)
    with open(me + '/triples', 'a') as f:
        f.write('\n' + formatted)

if __name__ == '__main__':
    for filename in sys.argv[1:]:
        add(filename)
