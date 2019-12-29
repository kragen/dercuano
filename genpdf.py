#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Parse HTML output to generate a PDF.

This is still very poor PDF generation for Dercuano.
Missing pieces include:

- Greek
- other math characters; ℓ doesn't even exist in Courier, and in ET Book,
  all of "ε₀ ≈" is no good
- a layout engine capable of handling varying font sizes in a line (also this
  one seems to have difficulty with varying font sizes on a page; see "fudge
  factor" in the code)
- Unicode subscripts (superscripts are OK, at least the ones in Latin-1)
- bullets
- tables
- Chinese
- wrapping overlong lines so they don't get cut off
- dingbats like × (no, that one is okay, also centered dot and degrees, but
  not ⁑)
- JS tables of contents for individual notes
- <sub> and <sup> (maybe using t.setRise)
- chronological ordering
- font fallbacks for missing characters
- not putting spaces after close tags
- maybe making the output file less than 12.4 megabytes?? not using
  base85 would fucking help
- colored titles
- hyphenation and justification
- need to include ET Book license
- not putting more newlines in random places when there are elements inside
  a <pre> (as in, for example, escheme.html)

It also takes over seven minutes to run on my netbook and generates a 4685-page PDF,
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
import os
import re
import sys
import xml.etree.cElementTree as ET

from reportlab.pdfgen.canvas import Canvas
import reportlab.lib.pagesizes
from reportlab.lib.colors import toColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont


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

class Textobject:
    def __init__(self, canvas, x, y, style):
        self.c = canvas
        self.x = x
        self.y = y
        self.font = style['font-family'], style['font-size']

    def start_page(self, style):
        self.c.setFont(*self.font)
        self.t = self.c.beginText(self.x, self.y)
        self.tfont = self.font

    def newline(self, style):
        self.t.textLine()
        if self.t.getY() < bottom_margin + 8*em:  # XXX fudge factor for layout bugs
            self.end_page()
            self.start_page(style)

    def end_page(self):
        self.c.drawText(self.t)
        self.c.showPage()
        del self.t
        del self.tfont

    def text_out(self, style, text):
        self.font = style['font-family'], style['font-size']
        if self.tfont != self.font:
            self.t.setFont(*self.font)
            self.tfont = self.font
        self.t.textOut(text)

    def move_cursor(self, dx, dy):
        self.t.moveCursor(dx, dy)

    def get_x(self):
        return self.t.getX()

    def get_y(self):
        return self.t.getY()

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

def render_text(c, t, text, style):
    max_x = pagesize[0] - right_margin
    pre = style['white-space'] == 'pre'
    words = (re.split('\n', text) if pre else re.split('[ \n\r\t]+', text))
    x, y = t.get_x(), t.get_y()
    font_family = style['font-family']
    font_size = style['font-size']
    box = [x, y - font_size * 0.1, x, y + font_size]
    for word in words:
        width = c.stringWidth(word, font_family, font_size)
        if pre or t.get_x() + width > max_x:
            t.newline(style)
            add_link(c, box, style['link destination'])
            x, y = t.get_x(), t.get_y()
            box = [x, y - font_size * 0.1, x, y + font_size]

        # XXX while it's still sticking past the right margin, chop it
        t.text_out(style, word + ' ')
        box[2] = t.get_x()

    add_link(c, box, style['link destination'])

block_fonts = {
    'p': (roman, 1*em),
    'h1': (roman, 2*em),
    'h2': (roman, 1.59*em),
    'h3': (roman, 1.26*em),
    'h4': (bold, 1.1*em),
    'h5': (bold, 1*em),
    'h6': (italic, 1*em),
    'li': (roman, 1*em),
    'div': (roman, 1*em),
    # With Latin Modern Mono Light Condensed, I need just over 28 ems for 80
    # columns, so font-size:98% seems about right.
    'pre': (lmtlc, 0.98*em),
    'br': (roman, 1*em),
    }

def italicize(font):
    return italic, font[1]

def codify(font):
    return ('Courier-Bold' if font[0] == bold or font[0].endswith('-Bold') else
            lmtlco if font[0] == italic or font[0].endswith('-Oblique') else
            lmtlc, font[1])

def embolden(font):
    return bold, font[1]

inline_fonts = {'i': italicize,
                'em': italicize,
                'code': codify,
                'b': embolden,
                'strong': embolden,
                }

def get_link(node):
    return node.get('href') if node.tag == 'a' else None

def push_style(stack, current_style, prop, value):
    stack.append(('restore', (prop, current_style[prop])))
    current_style[prop] = value

def render(corpus, bookmark, c, xml):
    print("PDFing", bookmark)
    c.bookmarkPage(bookmark, fit='XYZ')  # `fit` to suppress zooming out to whole page
    title = bookmark
    current_style = {
        'font-family': roman,
        'font-size': 1*em,
        'link destination': None,
        'white-space': 'normal',
    }

    t = Textobject(c, left_margin, pagesize[1]-top_margin-em, current_style)
    t.start_page(current_style)
    stack = [('element', xml)]
    while stack:
        kind, obj = stack.pop()
        if kind == 'element':
            if obj.tail is not None:
                stack.append(('text', obj.tail))

            if obj.tag in block_fonts:
                font_family, font_size = block_fonts[obj.tag]
                size_diff = font_size - current_style['font-size']
                push_style(stack, current_style, 'font-family', font_family)
                push_style(stack, current_style, 'font-size', font_size)
                t.newline(current_style)
                if size_diff > 0:
                    t.move_cursor(0, size_diff * 1.2)

            if obj.tag == 'p':
                t.text_out(current_style, ' ' * 4)  # paragraph indent
            elif obj.tag == 'li':
                # a bullet that happens to be in ET Book
                t.text_out(current_style, '• ')
            elif obj.tag == 'pre':
                push_style(stack, current_style, 'white-space', 'pre')

            if obj.tag in inline_fonts:
                # XXX maybe refactor how these are specced
                font = inline_fonts[obj.tag]((current_style['font-family'],
                                              current_style['font-size']))
                push_style(stack, current_style, 'font-family', font[0])
                push_style(stack, current_style, 'font-size', font[1])

            if obj.tag == 'title':
                title = re.compile(r'\s*Dercuano\s*$').sub('', obj.text).strip()
            if get_link(obj):
                push_style(stack, current_style, 'link destination',
                           resolve_link(corpus, get_link(obj)))

            if obj.text is not None and obj.tag not in ('title', 'script', 'style'):
                render_text(c, t, obj.text, current_style)

            for kid in reversed(list(obj)):
                stack.append(('element', kid))

        elif kind == 'text':
            render_text(c, t, obj, current_style)
        else:
            assert kind == 'restore'
            prop, val = obj
            current_style[prop] = val

    t.end_page()
    c.addOutlineEntry(title, bookmark, level=0)

def main(path):
    liabilities = path + '/liabilities'
    rfname = liabilities + '/et-book-roman-old-style-figures.ttf'
    pdfmetrics.registerFont(TTFont(roman, rfname))
    ifname = liabilities + '/et-book-display-italic-old-style-figures.ttf'
    pdfmetrics.registerFont(TTFont(italic, ifname))
    bfname = liabilities + '/et-book-bold-line-figures.ttf'
    pdfmetrics.registerFont(TTFont(bold, bfname))
    mypath = os.path.dirname(os.path.abspath(__file__))
    lmtlcname = mypath + '/LMMonoLtCond10-Regular.ttf'
    pdfmetrics.registerFont(TTFont(lmtlc, lmtlcname))
    lmtlconame = mypath + '/LMMonoLtCond10-Oblique.ttf'
    pdfmetrics.registerFont(TTFont(lmtlco, lmtlconame))

    canvas = Canvas('dercuano.tmp.pdf', invariant=True, pageCompression=True,
                    pagesize=pagesize)
    # pdf.js, gv, and MuPDF Mini display this:
    canvas.setTitle('Dercuano ' + os.path.basename(path)
                    + ', by Kragen Javier Sitaker, 2019')
    canvas.setAuthor('Kragen Javier Sitaker')

    corpus = OrderedDict()
    corpus['index.html'] = path + '/index.html'

    notes = path + '/notes'
    for basename in os.listdir(notes):#[::20]:
        corpus['notes/' + basename] = notes + '/' + basename

    topics = path + '/topics'
    for basename in sorted(os.listdir(topics)):#[::20]:
        corpus['topics/' + basename] = topics + '/' + basename

    for i, bookmarkname in enumerate(corpus):
        sys.stdout.write('%d/%d ' % (i, len(corpus)))
        filename = corpus[bookmarkname]
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
                render(corpus, bookmarkname, canvas,
                    ET.fromstring('<html>XML parse failure</html>'))
                continue

        render(corpus, bookmarkname, canvas, root)

    canvas.save()

if __name__ == '__main__':
    cgitb.enable(format='text')
    main(sys.argv[1])
