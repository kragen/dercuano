# -*- coding: utf-8 -*-
"""Implement Dercuano.

Next up:

- some kind of fucking CSS, Jesus.
- another note or two

"""
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

    def __repr__(self):
        return 'Bundle(%r)' % self.dirname

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

    def output_filename(self, *parts):
        return self.filename(self.output_dir, *parts)

    def generate_categories(self):
        for category in self.categories():
            self.generate_category(category)

    def category_filename(self, category):
        return self.output_filename(self.category_localpart(category))

    def category_localpart(self, category):
        return 'categories/' + as_filename(category) + '.html'

    def note_filename(self, notename):
        return self.output_filename(self.note_localpart(notename))

    def note_localpart(self, notename):
        return 'notes/' + as_filename(notename) + '.html'

    def note_title(self, notename):
        for subj, verb, obj in self.triples():
            if subj == notename and verb == 'titled':
                return obj
        return notename.replace('-', ' ').title()

    def category_title(self, category_name):
        for subj, verb, obj in self.triples():
            if subj == category_name and verb == 'category-titled':
                return obj
        return category_name.replace('-', ' ').title()

    def category_link(self, category_name, level=1):
        return a(self.category_title(category_name),
                 href='../' * level + self.category_localpart(category_name))

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
            if not line.strip():
                continue
            yield tuple(urlparse.unquote(field.replace('+', '%20'))
                                         for field in line.split())


def vomit_html(output_filename, html_contents):
    dirname, _ = os.path.split(output_filename)
    if not os.path.exists(dirname):
        os.makedirs(dirname)

    if isinstance(html_contents, unicode):
        html_contents = html_contents.encode('utf-8')

    with open(output_filename + '.tmp', 'w') as f:
        f.write(html_contents)

    os.rename(output_filename + '.tmp', output_filename)

def as_filename(candidate_filename):
    "Escape slashes, colons, NULs, etc., that break some filesystems."
    return urllib.quote_plus(candidate_filename, safe='')

ok(as_filename('a/bad file\\name: this\0'),
   'a%2Fbad+file%5Cname%3A+this%00')

def category_html(bundle, category_name):
    category_title = bundle.category_title(category_name)
    return ley(html(title(category_title, ' ⁂ ', bundle.get_title()),
                    head_stuff(),
                    h1('Notes in category: ', category_title),
                    ul([li(note.link_ley())
                        for note in bundle.notes()
                        if category_name in note.categories()])))

def index_html(bundle):
    categories = sorted(bundle.categories())
    return ley(html(title(bundle.get_title(),
                          ' version ', bundle.get_version()),
                    head_stuff(),
                    ul([li(note.link_ley(level=0))
                        for note in bundle.notes()]),
                    div(h2('Categories'),
                        ul([li(bundle.category_link(category, level=0))
                            for category in categories]))
                    if categories else []))

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

html, title, h1, h2 = tags('html', 'title', 'h1', 'h2')
div, ul, li, a = tags('div', 'ul', 'li', 'a')

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

    def __repr__(self):
        return 'Note(%r, %r, %r)' % (self.bundle, self.notename, self.source_file)

    def link_ley(self, level=1):
        return a(self.title(), href=("../" * level + self.localpart()))

    def render_if_outdated(self, print=lambda *args: None):
        if self.is_outdated():
            print("rerendering", self.notename)
            vomit_html(self.output_filename(), self.render().encode('utf-8'))

    def output_filename(self):
        return self.bundle.output_filename(self.localpart())

    def localpart(self):
        return self.bundle.note_localpart(self.notename)

    def title(self):
        return self.bundle.note_title(self.notename)

    def render(self):
        with open(self.source_file) as f:
            body = markdown.markdown(f.read().decode('utf-8'))
        categories = sorted(self.categories())
        return note_html(self.bundle, self.title(), body,
                         div(h2('Categories'),
                             ul([li(self.bundle.category_link(category))
                                 for category in categories]))
                         if categories else [])

    def categories(self):
        return set(obj for subj, verb, obj in self.bundle.triples()
                   if subj == self.notename and verb == 'concerns')

    def is_outdated(self):
        source_stat = os.stat(self.source_file)
        try:
            output_stat = os.stat(self.output_filename())
        except OSError as err:
            if err.errno == errno.ENOENT:
                return True
            raise

        return output_stat.st_mtime <= source_stat.st_mtime


def note_html(bundle, note_title, body, footers):
    return ley(html(title(note_title, ' ⁑ ', bundle.get_title()),
                    head_stuff(),
                    h1(note_title),
                    RawHTML(body),
                    footers))

def head_stuff():
    return [tag('meta')(charset="utf-8")]
