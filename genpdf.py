#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Parse HTML output to generate a PDF.

This is surprisingly adequate PDF generation for Dercuano.
Missing pieces include:

- a layout engine capable of handling varying font sizes in a line
- proper indentation for lists (<ul>, <ol>)
- tables
- JS tables of contents for individual notes
- chronological ordering
- maybe making the output file less than 12.4 megabytes?? not using
  base85 would fucking help
- colored titles
- hyphenation and justification
- properly making the first part of a link a link when it crosses pages;
  instead the first part ends up at the bottom of the next page
- URLs for external links?

It also takes over 7 minutes to run on my netbook and generates a 3764-page PDF,
so maybe some kind of output caching system would be useful.

The codepoint coverage thing may be a bit tricky.  Really we probably need to
extract the coverage information from the fonts rather than guessing at them;
this seems to provide roughly the right information:

    >>> from reportlab.pdfbase.ttfonts import TTFontFile
    >>> f
    'etbook/et-book-display-italic-old-style-figures.ttf'
    >>> itf = TTFontFile(f)
    >>> itf.charToGlyph
    {0: 1, 8192: 198, 8194: 200, 8195: 201, 8196: 202, 8197: 203,
    8198: 204, 8193: 199, 8200: 206, 8201: 207, 8202: 208, 13: 2,
    8208: 209, 8209: 210, 8210: 211, 8211: 212, 8212: 213, 8216: 214,
    ...
    >>> sorted(itf.charToGlyph.keys())
    [0, 13, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45,
    46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61,
    62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77,
    ...
    124, 125, 126, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169,
    ...

Also the TTFont has a .face property which inherits from TTFontFile and
thus has ``charToGlyph`` too.  And TTFont has a .stringWidth method too.

No idea how to tell what the coverage of the built-in Courier is,
though.  Maybe I should just use whatever Android uses instead of
Courier?

I'm thinking that high-level fonts will really be "font cascades", like in
CSS, and a box styled with a particular cascade will get broken up into
one or more boxes each styled with a particular low-level font.
To allow ligatures and kerning to work, we want to avoid breaking it up
into more boxes than needed.  <https://gankra.github.io/blah/text-hates-you/>
goes into details on the complexities involved and advises you to just use
HarfBuzz.

"""
from __future__ import print_function

import cgitb
from collections import OrderedDict
import errno
import os
import re
import sys
try:
    from urllib import unquote
except ImportError:
    from urllib.parse import unquote
import xml.etree.cElementTree as ET

from reportlab.pdfgen.canvas import Canvas
import reportlab.lib.pagesizes
from reportlab.lib.colors import toColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont


def style_override(style, prop, val):
    rv = style.copy()
    rv[prop] = val
    return rv

class Cascade:
    """A font cascade is similar to a font (modulo point size) with fallback.

    For code points not in the most preferred font, it falls back to
    less-preferred fonts, finally using the fallback font if nothing
    else has it.  To do this, it must be able to figure out if a font
    has a given code point or not, which I don't know how to do for
    arbitrary Reportlab fonts.  But I do know how to do it for
    TrueType fonts, so those are the ones you can use in the cascade
    list.

    """
    def __init__(self, fonts, fallback):
        """Parameter ``fonts`` is a TTFont list, which have .face.charToGlyph.
        Parameter ``fallback`` can be any Reportlab font; it will be used
        peremptorily for any codepoint not found in ``fonts``.
        """
        self.fonts = fonts
        self.fallback = fallback
        self.default_postscript_font = (fonts[0] if fonts else
                                        fallback).fontName
        self.string_cache = {}
        self.char_cache = {}
        self.width_cache = {}

    def register(self):
        for font in self.fonts:
            pdfmetrics.registerFont(font)

        if self.fallback:
            pdfmetrics.registerFont(self.fallback)

    def find_fonts(self, string):
        "Map a string of chars to (char, font) pairs."
        char_cache = self.char_cache
        for c in string:
            if c in char_cache:
                yield c, char_cache[c]
                continue
            
            for f in self.fonts:
                if ord(c) in f.face.charToGlyph:
                    if len(char_cache) > 1024:
                        char_cache.clear()
                    char_cache[c] = f
                    yield c, f
                    break
            else:
                yield c, self.fallback

    def _map(self, string):
        last_font = object()
        rv = []
        for c, f in self.find_fonts(string):
            if f == last_font:
                chars.append(c)
            else:
                chars = [c]
                rv.append((f, chars))
                last_font = f

        return tuple((f, u''.join(chars)) for f, chars in rv)

    def map(self, string):
        "Map a string to a tuple of (font, substring) pairs."
        if string not in self.string_cache:
            if len(self.string_cache) > 1024:
                self.string_cache.clear()
            self.string_cache[string] = self._map(string)
        return self.string_cache[string]

    def width(self, string, size):
        "Equivalent of font.stringWidth or canvas.stringWidth."
        k = string, size
        if k not in self.width_cache:
            if len(self.width_cache) > 4096:
                self.width_cache.clear()
            self.width_cache[k] = sum(f.stringWidth(s, size)
                                      for f, s in self.map(string))
        return self.width_cache[k]

    def text_out(self, textobject, style, string):
        "Equivalent of Textobject.text_out."
        for f, s in self.map(string):
            #print(u"Setting '%s' in %s" % (s, f.fontName))
            substyle = style_override(style, 'postscript-font', f.fontName)
            textobject.text_out(substyle, s)
    

roman = 'et-book-roman'
italic = 'et-book-italic'
bold = 'et-book-bold'
lmtlc = 'lmtlc'
lmtlco = 'lmtlc-Oblique'
# see dercuano-hand-computers for the origins of these numbers
em = 12
# this is too thin: pagesize = (24 * em, 60 * em)
# This is too wide (35 em x 50 em) and doesn't give enough zoom options:
#pagesize = reportlab.lib.pagesizes.A5
# Hopefully this is a Goldilocks size:
pagesize = (29 * em, 66 * em)
left_margin = top_margin = bottom_margin = right_margin = 0.5 * em

def load_fonts(path):
    stsong = UnicodeCIDFont('STSong-Light')

    mypath = os.path.dirname(os.path.abspath(__file__))
    flmtlc = TTFont(lmtlc, mypath + '/LMMonoLtCond10-Regular.ttf')
    flmtlco = TTFont(lmtlco, mypath + '/LMMonoLtCond10-Oblique.ttf')

    freefont = mypath + '/freefont-built'
    
    free = {}
    for face in ['MonoBoldOblique', 'MonoBold', 'MonoOblique', 'Mono',
                 'SerifBoldItalic', 'SerifBold', 'SerifItalic', 'Serif']:
        free[face] = TTFont('Free' + face, freefont + '/Free' + face + '.ttf')

    dejavu = {}
    dejavupath = mypath + '/dejavu-built'
    for face in (['SansMono' + suffix
                  for suffix in ['', '-Bold', '-Oblique', '-BoldOblique']]
                 + ['Serif' + suffix
                    for suffix in ['', '-Bold', '-Italic', '-BoldItalic']]):
        dejavu[face] = TTFont('DejaVu' + face,
                              dejavupath + '/DejaVu' + face + '.ttf')

    liabilities = path + '/liabilities'
    etbookroman = TTFont(roman,
                          liabilities + '/et-book-roman-old-style-figures.ttf')
    etbookitalic = TTFont(italic,
                liabilities + '/et-book-display-italic-old-style-figures.ttf')
    etbookbold = TTFont(bold, liabilities + '/et-book-bold-line-figures.ttf')

    rv = {
        'serif': Cascade([etbookroman, free['Serif'], dejavu['Serif']], stsong),
        'serif-italic': Cascade([etbookitalic, free['SerifItalic'],
                                 dejavu['Serif-Italic']], stsong),
        'serif-bold': Cascade([etbookbold, free['SerifBold'],
                               dejavu['Serif-Bold']], stsong),
        'serif-bold-italic': Cascade([free['SerifBoldItalic'],
                                      dejavu['Serif-BoldItalic']], stsong),
        'fixed': Cascade([flmtlc, free['Mono'], dejavu['SansMono']], stsong),
        'fixed-oblique': Cascade([flmtlco, free['MonoOblique'],
                                  dejavu['SansMono-Oblique']], stsong),
        'fixed-bold': Cascade([free['MonoBold'], dejavu['SansMono-Bold']],
                              stsong),
        'fixed-bold-oblique': Cascade([free['MonoBoldOblique'],
                                       dejavu['SansMono-BoldOblique']], stsong),
    }

    for cascade in rv:
        rv[cascade].register()

    return rv


class Textobject:
    def __init__(self, canvas, x, y, style):
        self.c = canvas
        self.x = x
        self.y = y
        self.font = style['postscript-font'], style['font-size']

    def start_page(self, style):
        self.font = style['postscript-font'], style['font-size']
        self.c.setFont(*self.font)
        self.t = self.c.beginText(self.x, self.y)
        self.tfont = self.font
        self.drawn_anything = False

    def newline(self, style, extra_skip):
        self.t.textLine()
        y = self.t.getY() - extra_skip
        if y < bottom_margin:
            self.end_page()
            self.start_page(style)
        else:
            # XXX starting so many new texts and setting so many new
            # fonts is adding over a megabyte to the PDF file: 12.37
            # MB vs. 13.44 MB
            self.flush()
            self.font = style['postscript-font'], style['font-size']
            self.c.setFont(*self.font)
            self.t = self.c.beginText(self.x, y)
            self.tfont = self.font
            self.drawn_anything = False

    def flush(self):
        if self.drawn_anything:
            self.c.drawText(self.t)
        del self.t, self.tfont, self.drawn_anything

    def end_page(self):
        self.flush()
        self.c.showPage()

    def text_out(self, style, text):
        self.font = style['postscript-font'], style['font-size']
        if self.tfont != self.font:
            self.t.setFont(*self.font)
            self.tfont = self.font
        self.t.textOut(text)
        self.drawn_anything = True

    def get_x(self):
        return self.t.getX()

    def get_y(self):
        return self.t.getY()

    def set_rise(self, rise):
        return self.t.setRise(rise)

def resolve_link(corpus, url):
    while url.startswith('../'):
        url = url[3:]
    return 'bookmark' if url in corpus else 'URL', url

def add_link(c, box, link):
    if not link:
        return
    link_type, link_value = link
    if link_type == 'bookmark':
        # Though other viewers ignore it, pdf.js displays the first
        # argument in a popup.  Maybe look for @title?
        c.linkRect(link_value, link_value, box, thickness=0.1,
                       color=toColor('#9999ff'))
    else:
        c.linkURL(link_value, box, thickness=0.1, color=toColor('#ccccff'))

def chop(cascade, font_size, string, max_width):
    """Cut `string` into a left half that fits within max_width,
    and a possibly empty right half that didn't."""
    # Half-open interval for cut point: a:b.  len(string) is valid
    # (and most common!) cut point, thus b is initially len(string)+1.
    a, b = 0, len(string)+1
    while a < b - 1:
        c = a + (b - a) // 2
        if cascade.width(string[:c], font_size) <= max_width:
            a = c
        else:
            b = c

    return string[:a], string[a:]

def text_out(fonts, t, style, s):
    fonts[style['font-family']].text_out(t, style, s)

# Abbreviations not to put an extra space after
abbrevs = {'Mr.', 'vs.', 'cf.', 'Jr.', 'pp.', 'Ms.', 'Dr.', 'p.', 'St.', '(St.'}
spacepunct = tuple('.?!:;')

def render_text(c, t, text, style, fonts, abbrevs=abbrevs, spacepunct=spacepunct):
    max_x = pagesize[0] - right_margin
    pre = style['white-space'] == 'pre'
    words = (re.split('([^\n]+\n)', text) if pre else
             re.split('[ \n\r\t]+', text))
    x, y = t.get_x(), t.get_y()
    font_family = style['font-family']
    font = fonts[font_family]
    font_size = style['font-size']
    box = [x - font_size * 0.1, y - font_size * 0.1, x, y + font_size]
    newline_style = style_override(style, 'postscript-font',
                                   font.default_postscript_font)
    for wi, word in enumerate(words):
        ends_in_newline = word.endswith('\n')   # for <pre>
        if ends_in_newline:
            word = word[:-1]

        width = font.width(word, font_size)
        x = t.get_x()
        if x + width > max_x:
            t.newline(newline_style, 0)
            add_link(c, box, style['link destination'])
            x, y = t.get_x(), t.get_y()
            box = [x - font_size * 0.1, y - font_size * 0.1,
                   x + font_size * 0.1, y + font_size]

        # chop up words too wide for lines
        while word and x + width > max_x:
            left, right = chop(font, font_size, word, max_x - x)
            text_out(fonts, t, style, left)
            x = t.get_x()
            box[2] = x + font_size * 0.1
            add_link(c, box, style['link destination'])
            # Add circles to indicate a broken line
            c.circle(x + font_size * .2, y + font_size * .3, font_size/6)

            t.newline(newline_style, 0)
            x, y = t.get_x(), t.get_y()
            c.circle(x - font_size * .2, y + font_size * .3, font_size/6)
            box = [x - font_size * 0.1, y - font_size * 0.1, x, y + font_size]
            word = right
            width = font.width(word, font_size)

        # The last word in a string shouldn't have a space after it.
        # (re.split will give us an empty last word if the string ends
        # in whitespace.)  I tried emitting the space as a separate
        # textOut in order to share the caches across the width and
        # text_out operations, but that made the program slower, not
        # faster, presumably because of the larger number of textOut
        # operations.
        if wi < len(words) - 1 and not pre:
            word = word + ('  ' if (word[-1:] in spacepunct
                                    and word not in abbrevs) else ' ')

        text_out(fonts, t, style, word)
        if ends_in_newline:
            t.newline(newline_style, 0)

        x = t.get_x()
        box[2] = x + font_size * 0.1

    add_link(c, box, style['link destination'])

block_fonts = {
    'p': (None, None),
    'h1': ('serif', 2*em),
    'h2': ('serif', 1.59*em),
    'h3': ('serif', 1.26*em),
    'h4': ('serif-bold', 1.1*em),
    'h5': ('serif-bold', 1*em),
    'h6': ('serif-bold-italic', 1*em),
    'li': (None, None),
    'div': (None, None),
    # With Latin Modern Mono Light Condensed, I need just over 28 ems for 80
    # columns, so font-size:98% seems about right.
    'pre': ('fixed', 0.98*em),
    'br': (None, None),
    # Actual table support would be a lot better obviously but until then:
    'tr': (None, None),
    'blockquote': (None, 0.8409*em),  # sqrt(sqrt(2))
    'ul': (None, None),
    'ol': (None, None),
    }

extra_padding_ems_above = dict(h2=0.5, h3=0.5, h4=0.5, h5=0.5, h6=0.5, pre=1,
                               blockquote=0.5)

italicize_table = {
    'serif': 'serif-italic',
    'serif-italic': 'serif-italic',
    'serif-bold': 'serif-bold-italic',
    'serif-bold-italic': 'serif-bold-italic',
    'fixed': 'fixed-oblique',
    'fixed-oblique': 'fixed-oblique',
    'fixed-bold': 'fixed-bold-oblique',
    'fixed-bold-oblique': 'fixed-bold-oblique',
}

def italicize(font):
    return italicize_table[font[0]], font[1]

codify_table = {
    'serif': 'fixed',
    'serif-italic': 'fixed-oblique',
    'serif-bold': 'fixed-bold',
    'serif-bold-italic': 'fixed-bold-oblique',
    'fixed': 'fixed',
    'fixed-oblique': 'fixed-oblique',
    'fixed-bold': 'fixed-bold',
    'fixed-bold-oblique': 'fixed-bold-oblique',
}

def codify(font):
    return codify_table[font[0]], font[1]

embolden_table = {
    'serif': 'serif-bold',
    'serif-italic': 'serif-bold-italic',
    'serif-bold': 'serif-bold',
    'serif-bold-italic': 'serif-bold-italic',
    'fixed': 'fixed',
    'fixed-oblique': 'fixed-bold-oblique',
    'fixed-bold': 'fixed-bold',
    'fixed-bold-oblique': 'fixed-bold-oblique',
}

def embolden(font):
    return embolden_table[font[0]], font[1]

inline_fonts = {'i': italicize,
                'em': italicize,
                'code': codify,
                'b': embolden,
                'strong': embolden,
                }

def get_link(node):
    url = node.get('href') if node.tag == 'a' else None
    return None if url is None else unquote(url)

def push_style(stack, current_style, prop, value):
    stack.append(('restore', (prop, current_style[prop])))
    current_style[prop] = value

def render(pagenos, corpus, bookmark, c, xml, fonts):
    print("PDFing", bookmark)
    c.bookmarkPage(bookmark, fit='XYZ')  # `fit` to suppress zooming out to whole page
    pagenos[bookmark] = c.getPageNumber()
    title = bookmark
    current_style = {
        'font-family': 'serif',
        'font-size': 1*em,
        'link destination': None,
        'white-space': 'normal',
    }

    start_page_style = style_override(current_style, 'postscript-font',
        fonts[current_style['font-family']].default_postscript_font)
    t = Textobject(c, left_margin, pagesize[1]-top_margin-em, start_page_style)
    t.start_page(start_page_style)
    stack = [('element', xml)]
    top_of_block = True
    while stack:
        kind, obj = stack.pop()
        if kind == 'element':
            if obj.tail is not None:
                stack.append(('text', obj.tail))

            # Ignore whitespace so newlines don't clear top_of_block:
            if obj.text and not obj.text.strip():
                obj.text = None

            if obj.tag in block_fonts:
                font_family, font_size = block_fonts[obj.tag]
                if not top_of_block:
                    new_font_size = (font_size if font_size is not None else
                                     current_style['font-size'])
                    newline_style = style_override(current_style,
                                                   'postscript-font',
                        fonts[current_style['font-family']]
                            .default_postscript_font)
                    skip = ( new_font_size - 1*em
                           + new_font_size * extra_padding_ems_above.get(obj.tag, 0)
                           )
                    t.newline(newline_style, extra_skip=skip)

                if font_family is not None:  # inherit
                    push_style(stack, current_style, 'font-family', font_family)
                if font_size is not None:    # inherit
                    push_style(stack, current_style, 'font-size', font_size)
                was_top_of_block = top_of_block
                top_of_block = (obj.tag in ('li', 'blockquote'))
            else:
                top_of_block = False

            if obj.tag == 'p':
                # paragraph indent
                if not was_top_of_block:
                    text_out(fonts, t, current_style, ' ' * 4)
            elif obj.tag == 'li':
                text_out(fonts, t, current_style, u'• ')
            elif obj.tag == 'pre':
                push_style(stack, current_style, 'white-space', 'pre')

            if obj.tag in inline_fonts:
                # XXX maybe refactor how these are specced
                font = inline_fonts[obj.tag]((current_style['font-family'],
                                              current_style['font-size']))
                push_style(stack, current_style, 'font-family', font[0])
                push_style(stack, current_style, 'font-size', font[1])

            if obj.tag in ('sup', 'sub'):
                font_size = current_style['font-size']
                rise = 0.5 * font_size * (1 if obj.tag == 'sup' else -1)
                stack.append(('clear_rise',
                              t._rise if hasattr(t, '_rise') else 0))
                t.set_rise(rise)
                push_style(stack, current_style, 'font-size',
                           max(0.2*em, 0.7071 * font_size))

            if obj.tag == 'title':
                title = re.compile(r'\s*Dercuano\s*$').sub('', obj.text).strip()
            if get_link(obj):
                link_dest = resolve_link(corpus, get_link(obj))
                push_style(stack, current_style, 'link destination', link_dest)

                if link_dest[0] == 'bookmark':
                    stack.append(('text',
                            ' (p. %s)' % pagenos.get(link_dest[1], '???')))

            if obj.text is not None and obj.tag not in ('title', 'script', 'style'):
                render_text(c, t, obj.text, current_style, fonts)
                top_of_block = False

            for kid in reversed(list(obj)):
                stack.append(('element', kid))

        elif kind == 'text':
            render_text(c, t, obj, current_style, fonts)
            top_of_block = False
        elif kind == 'clear_rise':
            t.set_rise(obj)
        else:
            assert kind == 'restore'
            prop, val = obj
            current_style[prop] = val
            top_of_block = False

    t.end_page()
    c.addOutlineEntry(title, bookmark, level=0)

def read_plaintext(bookmarkname, filename):
    root = ET.XML('<html><title></title>'
                 + '<body><pre></pre></body>'
                 + '</html>')
    root[0].text = bookmarkname
    body = root[1]
    assert body.tag == 'body'
    for paragraph in open(filename).read().decode('utf-8').split('\n\n'):
        ptag = ET.Element('p')
        ptag.text = paragraph
        body.append(ptag)

    return root


class Pagenos:
    def __init__(self, filename):
        self.filename = filename
        self.pagenos = {}

    def load(self):
        try:
            f = open(self.filename)
        except IOError as e:
            if e.errno == errno.ENOENT:
                return
            raise

        with f:
            for line in f:
                pageno, bookmark = line.split()
                self.pagenos[bookmark] = int(pageno)

    def save(self):
        with open(self.filename + '.tmp', 'w') as f:
            for bookmark, pageno in self.pagenos.items():
                f.write('%d %s\n' % (pageno, bookmark))
            f.flush()
            os.fsync(f.fileno())

        os.rename(self.filename + '.tmp', self.filename)

    def get(self, bookmark, default):
        return self.pagenos.get(bookmark, default)

    def __setitem__(self, bookmark, pageno):
        assert len(bookmark.split()) == 1
        self.pagenos[bookmark] = pageno


def main(path):
    fast = False
    fonts = load_fonts(path)

    canvas = Canvas('dercuano.tmp.pdf', invariant=True, pageCompression=True,
                    pagesize=pagesize)
    # Avoid horking our page number database with fast debugging runs
    pagenos = (Pagenos('dercuano.fast.pagenos') if fast else
               Pagenos('dercuano.tmp.pagenos'))
    pagenos.load()

    # pdf.js, gv, MuPDF Mini, and Evince display this:
    canvas.setTitle('Dercuano ' + os.path.basename(path)
                    + ', by Kragen Javier Sitaker, 2019')
    canvas.setAuthor('Kragen Javier Sitaker')

    corpus = OrderedDict()
    corpus['index.html'] = path + '/index.html'

    notes = path + '/notes'
    for basename in os.listdir(notes)[1::20] if fast else os.listdir(notes):
        corpus['notes/' + basename] = notes + '/' + basename

    topics = path + '/topics'
    for basename in (sorted(os.listdir(topics))[::20] if fast else
                     sorted(os.listdir(topics))):
        corpus['topics/' + basename] = topics + '/' + basename

    corpus['liabilities/LICENSE.ETBook'] = (
        path + '/' + 'liabilities/LICENSE.ETBook')

    plaintexts = {'liabilities/LICENSE.ETBook'}

    for i, bookmarkname in enumerate(corpus):
        sys.stdout.write('%d/%d ' % (i, len(corpus)))
        filename = corpus[bookmarkname]

        if bookmarkname in plaintexts:
            root = read_plaintext(bookmarkname, filename)
        else:
            try:
                tree = ET.parse(filename)
                root = tree.getroot()
            except Exception:
                print("parse error on", bookmarkname + ":", sys.exc_info()[1])
                try:
                    # Although the above chews through all of Dercuano in 1.3
                    # seconds on this netbook, it fails to parse 3% of the
                    # notes because they have things like raw HTML blocks in
                    # them, which Python Markdown doesn't XMLify (e.g., ``<tr>
                    # <td>1 <td>0.4%``.)  So we preprocess everything
                    # with HTML Tidy.  sgmllib and htmllib are
                    # removed in Python 3, and HTMLParser (html.parser) is a
                    # tag-soup parser.
                    import tidylib
                    xml = tidylib.tidy_document(open(filename).read(),
                                                {'input-encoding': 'utf8',
                                                 'output-encoding': 'utf8',
                                                 'numeric-entities': True})[0]
                    root = ET.fromstring(xml)
                    # remove XML namespace prefixes:
                    deprefixnodes = [root]
                    while deprefixnodes:
                        node = deprefixnodes.pop()
                        deprefixnodes.extend(list(node))
                        node.tag = re.compile('{.*}').sub('', node.tag)
                    print("recovered using tidylib")
                except Exception:
                    print("tidylib failed too:", sys.exc_info()[1])
                    render(pagenos, corpus, bookmarkname, canvas,
                        ET.fromstring('<html>XML parse failure</html>'), fonts)
                    continue

        render(pagenos, corpus, bookmarkname, canvas, root, fonts)

    canvas.save()
    pagenos.save()

if __name__ == '__main__':
    cgitb.enable(format='text')
    main(sys.argv[1])
