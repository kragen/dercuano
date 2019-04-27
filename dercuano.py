# -*- coding: utf-8 -*-
import os
import urllib
import urlparse
import subprocess


def ok(a, b):
    assert a == b, (a, b)

class Bundle:
    def __init__(self, dirname):
        self.dirname = dirname
        self._triples = list(load_triples(self.filename('triples')))
        self.output_dir = 'dercuano-' + self.get_version()

    def get_version(self):
        for subj, verb, obj in self.triples():
            if subj == 'dercuano' and verb == 'version':
                return obj

        return 'prerelease'

    def notes(self):
        for notename in os.listdir(self.filename('markdown')):
            yield Note(self, notename)

    def filename(self, *parts):
        return os.path.join(self.dirname, *parts)

    def generate_categories(self):
        for category in self.categories():
            self.generate_category(category)

    def generate_category(self, category):
        vomit_html(self.filename(self.output_dir,
                                 'categories',
                                 as_filename(category) + '.html'),
                   category_html(self, category))

    def categories(self):
        return set(obj for subj, verb, obj in self.triples()
                   if verb == 'concerns')

    def generate_index(self):
        vomit_html(self.filename(self.output_dir, 'index.html'),
                   index_html(self))

    def generate_archive(self):
        subprocess.check_call('cd %s; tar czvf dercuano-%s.tar.gz %s' % (
            self.dirname, self.get_version(), self.output_dir),
                              shell=True)

    def triples(self):
        return self._triples
 

def load_triples(filename):
    with open(filename) as f:
        for line in f:
            yield tuple(urlparse.unquote(field) for field in line.split())


def vomit_html(output_filename, html_contents):
    dirname, _ = os.path.split(output_filename)
    if not os.path.exists(dirname):
        os.makedirs(dirname)

    with open(output_filename + '.tmp', 'w') as f:
        f.write(html_contents)

    os.rename(output_filename + '.tmp', output_filename)

def as_filename(candidate_filename):
    "Escape slashes, colons, NULs, etc., that break some filesystems."
    return urllib.quote_plus(candidate_filename, safe='')

ok(as_filename('a/bad file\\name: this\0'),
   'a%2Fbad+file%5Cname%3A+this%00')

def category_html(bundle, category_name):
    return '<html><title>Category ' + category_name

def index_html(bundle):
    return '<html><title>Dercuano version ' + bundle.get_version()

class Note:
    def __init__(self, bundle, notename):
        self.bundle = bundle
        self.notename = notename
