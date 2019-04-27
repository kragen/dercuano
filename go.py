#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Generate a Dercuano bundle in the current directory.
"""
import dercuano


def go(dirname):
    bundle = dercuano.Bundle(dirname)
    for note in bundle.notes():
        note.render_if_outdated()
    bundle.generate_categories()
    bundle.generate_index()
    bundle.generate_archive()


if __name__ == '__main__':
    go('.')
