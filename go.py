#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Generate a Dercuano bundle in the current directory.
"""
from __future__ import print_function
import dercuano
import cgitb


def go(dirname):
    bundle = dercuano.Bundle(dirname)
    for note in bundle.notes:
        note.render_if_outdated(print=print)
    bundle.generate_categories()
    bundle.generate_index()
    bundle.install_liabilities()
    bundle.generate_archive()


if __name__ == '__main__':
    cgitb.enable(format='text')
    go('.')
