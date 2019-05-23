# -*- coding: utf-8 -*-
"""Implement Dercuano.

Next up:

- maybe reify categories as a class?
- maybe some metadata about unfinished
  status?
- maybe list categories on the link to the note?
- A Bayesian classifier
- add "INCOMPLETE UNVERIFIED DRAFT" to everything, and maybe
  SPECULATIVE to some things too
- add more notes

"""
from __future__ import print_function, division
import cgi
import errno
import os
import re
import urllib
import urlparse
import subprocess

import markdown

import relation


def ok(a, b):
    assert a == b, (a, b)

class Bundle:
    def __init__(self, dirname):
        self.dirname = dirname
        self._relations = as_relations(load_triples(self.filename('triples')))
        self.output_dir = 'dercuano-' + self.get_version()
        self.cached_titles = {}
        self.notes = list(self._notes())
        self.note_map = {note.notename: note for note in self.notes}

    def __repr__(self):
        return 'Bundle(%r)' % self.dirname

    def get_version(self):
        v = self.relation('version')['dercuano']
        return 'prerelease' if not v else v[0]

    def get_title(self):
        t = self.relation('bundle')['dercuano']
        return 'Dercuano' if not t else t[0]

    def get_intro(self):
        with open(self.filename('intro.md')) as f:
            return RawHTML(markdown.markdown(f.read().decode('utf-8')))

    def _notes(self):
        dirname = self.filename('markdown')
        for notename in sorted(os.listdir(dirname)):
            if notename.endswith('~') or notename[0] in '.#':
                continue
            yield Note(self, notename, os.path.join(dirname, notename))

    def note(self, notename):
        return self.note_map[notename]

    def filename(self, *parts):
        return os.path.join(self.dirname, *parts)

    def output_filename(self, *parts):
        return self.filename(self.output_dir, *parts)

    def generate_categories(self):
        for category in self.categories():
            if len(self.notes_in_category(category)) > 1:
                self.generate_category(category)

    def category_filename(self, category):
        return self.output_filename(self.category_localpart(category))

    def category_localpart(self, category):
        return 'topics/' + as_filename(category) + '.html'

    def note_filename(self, notename):
        return self.output_filename(self.note_localpart(notename))

    def note_localpart(self, notename):
        return 'notes/' + as_filename(notename) + '.html'

    def note_title(self, notename):
        t = self.relation('titled')[notename]
        if t:
            return t[0]

        internal_title = self.internal_title(notename)
        if internal_title is not None:
            return internal_title

        return notename.replace('-', ' ').capitalize()

    def internal_title(self, notename):
        if notename not in self.cached_titles:
            self.cached_titles[notename] = self.read_internal_title(notename)
        return self.cached_titles[notename]

    def read_internal_title(self, notename):
        with open(self.note(notename).source_file) as f:
            possible_title = f.readline().strip()
            possible_title_marker = f.readline().strip()
            if possible_title_marker and all(c == '='
                                             for c in possible_title_marker):
                return possible_title
            return None

    def category_title(self, category_name):
        t = self.relation('category-titled')[category_name]
        return category_name.replace('-', ' ').capitalize() if not t else t[0]

    def category_link(self, category_name, level=1):
        return a(self.category_title(category_name),
                 href='../' * level + self.category_localpart(category_name))

    def generate_category(self, category):
        vomit_html(self.category_filename(category),
                   category_html(self, category))

    def categories(self):
        return set(~self.relation('concerns'))

    def notes_in_category(self, category_name):
        return list(self._notes_in_category(category_name))

    def _notes_in_category(self, category_name):
        for notename in (~self.relation('concerns'))[category_name]:
            try:
                yield self.note_map[notename]
            except KeyError:
                print("erroneous category subject", notename)

    def category_size(self, category_name):
        return len((~self.relation('concerns'))[category_name])

    def generate_index(self):
        vomit_html(self.filename(self.output_dir, 'index.html'),
                   index_html(self))

    def install_liabilities(self):
        home, _ = os.path.split(__file__)
        liabilities = os.path.join(home, 'liabilities')
        subprocess.check_call(['cp', '-a', liabilities, self.output_dir])

    def generate_archive(self):
        subprocess.check_call('cd %s; tar czf dercuano-%s.tar.gz %s' % (
            self.dirname, self.get_version(), self.output_dir),
                              shell=True)

    def relation(self, verb):
        try:
            return self._relations[verb]
        except KeyError:
            return relation.Relation()


def load_triples(filename):
    with open(filename) as f:
        for line in f:
            if not line.strip():
                continue
            fields = tuple(urlparse.unquote(field.replace('+', '%20'))
                           for field in line.split())
            for fn in fields[2:]:
                yield (fields[0], fields[1], fn)


def as_relations(triples):
    relations = {}
    for subj, verb, obj in triples:
        if verb not in relations:
            relations[verb] = relation.Relation()
        relations[verb].put(subj, obj)

    # Precompute inverse relations eagerly
    for verb in relations:
        ~relations[verb]

    return relations

class Note:
    def __init__(self, bundle, notename, source_file):
        self.bundle = bundle
        self.notename = notename
        self.source_file = source_file
        self._word_count = None
        self._date_string = None

    def __repr__(self):
        return 'Note(%r, %r, %r)' % (self.bundle, self.notename, self.source_file)

    def link_ley(self, level=1):
        return a(self.title(), href=("../" * level + urllib.quote(self.localpart())))

    def date_string(self):
        if self._date_string is None:
            self._date_string = self.compute_date_string()
        return self._date_string

    def compute_date_string(self):
        written = self.bundle.relation('written')[self.notename]
        updated = self.bundle.relation('updated')[self.notename]

        if not written and not updated:
            return ''

        date = (written or updated)[0]
        if updated and written != updated:
            date += ' (updated ' + updated[0] + ')'

        return date

    def extra_ley(self):
        date = self.date_string()
        return [' ', date, ' ' if date else '', self.minutes_string()]

    def minutes_string(self):
        # Wikipedia’s Reading article says “reading for comprehension”
        # is 200–400 words per minute.  I’m going to figure that
        # enough of these notes involve equations and source code that
        # we should halve that.
        minutes = round(self.word_count() / 150)
        return '(%d %s)' % (minutes, pluralize('minute', minutes))

    def word_count(self):
        if self._word_count is None:
            with open(self.source_file) as f:
                self._word_count = sum(1 for line in f for word in line.split())
        return self._word_count

    def flavor(self):
        f = self.bundle.relation('flavor')[self.notename]
        if f:
            return markup_flavors[f[0]]
        return markdown_replacing_links(self.bundle)

    def render_if_outdated(self, print=lambda *args: None):
        if self.is_outdated():
            print("rendering", self.output_filename())
            vomit_html(self.output_filename(), self.render().encode('utf-8'))

    def output_filename(self):
        return self.bundle.output_filename(self.localpart())

    def localpart(self):
        return self.bundle.note_localpart(self.notename)

    def title(self):
        return self.bundle.note_title(self.notename)

    def render(self):
        with open(self.source_file) as f:
            body = f.read()

        categories = sorted(self.categories(),
                            key=self.bundle.category_size,
                            reverse=True)
        html = note_html(self.bundle, self.title(), self.flavor()(body),
                         div(h2('Topics'),
                             ul([li(self.bundle.category_link(category),
                                    " (%d notes)" % self.bundle.category_size(category),
                                    "\n")
                                 if len(self.bundle.notes_in_category(category)) > 1
                                 else li(self.bundle.category_title(category))
                                 for category in categories]))
                         if categories else [])

        subtitle = ley(div(self.author(), ', ', self.date_string(),
                           ' ', self.minutes_string(),
                           **{'class': "metadata"}))
        return html.replace('</h1>', '</h1>' + subtitle, 1)

    def author(self):
        return (self.bundle.relation('note-by')[self.notename]
                or self.bundle.relation('by')['dercuano']
                or ['Anonymous'])[0]

    def categories(self):
        return set(self.bundle.relation('concerns')[self.notename])

    def is_outdated(self):
        source_stat = os.stat(self.source_file)
        try:
            output_stat = os.stat(self.output_filename())
        except OSError as err:
            if err.errno == errno.ENOENT:
                return True
            raise

        return output_stat.st_mtime <= source_stat.st_mtime

    # For classify.py
    def read_words(self):
        with open(self.source_file) as f:
            for line in f:
                for word in re.findall(r'\w+', line):
                    yield word.lower()


def pluralize(noun, number):
    return noun if number == 1 else noun + 's'

def vomit_html(output_filename, html_contents):
    dirname, _ = os.path.split(output_filename)
    if not os.path.exists(dirname):
        os.makedirs(dirname)

    if isinstance(html_contents, unicode):
        html_contents = html_contents.encode('utf-8')

    with open(output_filename + '.tmp', 'w') as f:
        f.write(b'<!DOCTYPE html>\n' + html_contents)

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
                    h1('Notes concerning “', category_title, '”'),
                    ul([li(note.link_ley(), note.extra_ley(), "\n")
                        for note in sorted(bundle.notes_in_category(category_name),
                                           key=note_date)
                        ])))

def note_date(note):
    return note.date_string()

def index_html(bundle):
    notes = sorted(bundle.notes, key=note_date)
    note_years = []
    last_year = None
    for note in notes:
        year = re.compile('[- ]').split(note.date_string())[0]
        if year != last_year:
            if last_year != None:
                note_years.append(ol(current_ol))
            note_years.append(h3(year))
            current_ol = []
            last_year = year
        current_ol.append(li(note.link_ley(level=0), note.extra_ley(), "\n"))

    if last_year != None:
        note_years.append(ol(current_ol))

    bundle_title = bundle.get_title()
    categories = sorted(bundle.categories())
    return ley(html(title(bundle_title, ' version ', bundle.get_version()),
                    head_stuff(level=0),
                    h1(bundle_title),
                    bundle.get_intro(),
                    h2('Notes'),
                    note_years,
                    div(h2('Topics'),
                        ul([li(bundle.category_link(category, level=0),
                               " (%d notes)" % bundle.category_size(category),
                               "\n")
                            for category in sorted(categories,
                                                   key=bundle.category_size,
                                                   reverse=True)
                            if len(bundle.notes_in_category(category)) > 1]))
                    if categories else [],
                    script(src="liabilities/addtoc.js"),
    ))

def word_count(note):
    return note.word_count()

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
        return u'<%s%s%s>%s</%s>' % (
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

html, title, script, h1, h2, h3 = tags('html', 'title', 'script', 'h1', 'h2', 'h3')
div, ul, ol, li, a = tags('div', 'ul', 'ol', 'li', 'a')

class RawHTML:
    def __init__(self, html):
        self.html = html

    def as_html(self):
        return self.html

def note_html(bundle, note_title, body, footers):
    return ley(html(title(note_title, ' ⁑ ', bundle.get_title()),
                    head_stuff(),
                    '' if '<h1>' in body else h1(note_title),
                    RawHTML(body),
                    script(src="../liabilities/addtoc.js"),
                    footers))

ad_hoc_link_re = re.compile(r'(?:[fF]ile\s+)?<code>(.*?)</code>')
def markdown_replacing_links(bundle):
    def replace(s):
        def repl(mo):
            note = bundle.note_map.get(mo.group(1))
            return ley(note.link_ley()) if note else mo.group(0)

        return ad_hoc_link_re.sub(repl, markdown.markdown(s.decode('utf-8')))

    return replace

markup_flavors = {
    '<pre>': lambda s: ley(tag('pre')(s)),
}

def head_stuff(level=1):
    stylesheet = '../' * level + 'liabilities/style.css'
    return [tag('meta')(charset="utf-8"),
            tag('link')(rel='stylesheet', href=stylesheet),
            tag('meta')(name="viewport",
                        content="width=device-width, initial-scale=1.0"),
    ]
