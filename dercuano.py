# -*- coding: utf-8 -*-
from __future__ import print_function
import cgi
import errno
import os
import urllib
import urlparse
import subprocess

import markdown


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

    def get_title(self):
        for subj, verb, obj in self.triples():
            if subj == 'dercuano' and verb == 'bundle':
                return obj

        return 'Dercuano'

    def notes(self):
        dirname = self.filename('markdown')
        for notename in os.listdir(dirname):
            yield Note(self, notename, os.path.join(dirname, notename))

    def filename(self, *parts):
        return os.path.join(self.dirname, *parts)

    def generate_categories(self):
        for category in self.categories():
            self.generate_category(category)

    def category_filename(self, category):
        return self.filename(self.output_dir,
                             'categories',
                             as_filename(category) + '.html')

    def note_filename(self, notename):
        return self.filename(self.output_dir,
                             'notes',
                             as_filename(notename) + '.html')

    def note_title(self, notename):
        for subj, verb, obj in self.triples():
            if subj == notename and verb == 'titled':
                return obj
        return notename.replace('-', ' ').title()

    def generate_category(self, category):
        vomit_html(self.category_filename(category),
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
            yield tuple(urlparse.unquote(field.replace('+', '%20'))
                                         for field in line.split())


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
    return ley(html(title('Category ', category_name),
                    head_stuff()))

def index_html(bundle):
    return ley(html(title(bundle.get_title(), ' version ', bundle.get_version()),
                    head_stuff()))

def ley(htmlish):
    "HTML generator.  Tiny version of Stan from Nevow."
    try:
        as_html = htmlish.as_html
    except AttributeError:
        if isinstance(htmlish, unicode):
            return cgi.escape(htmlish)
        if isinstance(htmlish, str):
            return ley(htmlish.decode('utf-8'))
        if isinstance(htmlish, list):
            return u''.join(ley(item) for item in htmlish)
        raise
    else:
        return as_html()

class Element:
    def __init__(self, tagname, attrs, content):
        self.tagname = tagname
        self.attrs = attrs
        self.content = content

    def as_html(self):
        return '<%s%s%s>%s</%s>' % (
            self.tagname,
            ' ' if self.attrs else '',
            self.render_attrs(),
            ley(self.content),
            self.tagname)

    def render_attrs(self):
        return ' '.join('%s="%s"' % (k, cgi.escape(v, True))
                        for k, v in self.attrs.items())

def tag(tagname):
    def render(*args, **kwargs):
        return Element(tagname=tagname, attrs=kwargs, content=list(args))
    return render

def tags(*tagnames):
    for tagname in tagnames:
        yield tag(tagname)

html, title, h1 = tags('html', 'title', 'h1')

class RawHTML:
    def __init__(self, html):
        self.html = html

    def as_html(self):
        return self.html

class Note:
    def __init__(self, bundle, notename, source_file):
        self.bundle = bundle
        self.notename = notename
        self.source_file = source_file

    def render_if_outdated(self, print=lambda *args: None):
        if self.is_outdated():
            print("rerendering", self.notename)
            vomit_html(self.output_filename(), self.render().encode('utf-8'))

    def output_filename(self):
        return self.bundle.note_filename(self.notename)

    def render(self):
        with open(self.source_file) as f:
            body = markdown.markdown(f.read().decode('utf-8'))
        note_title = self.bundle.note_title(self.notename)
        return note_html(self.bundle, note_title, body)

    def is_outdated(self):
        source_stat = os.stat(self.source_file)
        try:
            output_stat = os.stat(self.output_filename())
        except OSError as err:
            if err.errno == errno.ENOENT:
                return True
            raise

        return output_stat.st_mtime <= source_stat.st_mtime


def note_html(bundle, note_title, body):
    return ley(html(title(note_title + ' ⁑ ' + bundle.get_title()),
                    head_stuff(),
                    h1(note_title),
                    RawHTML(body)))

def head_stuff():
    return [tag('meta')(charset="utf-8")]
