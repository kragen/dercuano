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
- <pre>
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
- correct handling of files like high-temperature-semiconductors.html; I
  think maybe elementtidy is providing me with a different interface than
  ElementTree does, and it's also choking on the UTF-8

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
import sys
import os
import xml.etree.cElementTree as ET

from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.colors import toColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont


roman = 'et-book-roman'
italic = 'et-book-italic'
bold = 'et-book-bold'
# see dercuano-hand-computers for the origins of these numbers
em = 12
pagesize = (24 * em, 60 * em)
left_margin = top_margin = bottom_margin = right_margin = 0.5 * em

def start_page(c, font):
    c.setFont(*font)
    return c.beginText(left_margin, pagesize[1]-top_margin-em)

def newline(c, t, font):
    t[0].textLine()
    if t[0].getY() < bottom_margin + 8*em:  # XXX fudge factor for layout bugs
        c.drawText(t[0])
        c.showPage()
        t[0] = start_page(c, font)

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

def render_text(c, t, text, font, link):
    max_x = pagesize[0] - right_margin
    words = text.split()
    x, y = t[0].getX(), t[0].getY()
    box = [x, y - font[1] * 0.1, x, y + font[1]]
    for word in words:
        width = c.stringWidth(word, *font)
        if t[0].getX() + width > max_x:
            newline(c, t, font)
            add_link(c, box, link)
            x, y = t[0].getX(), t[0].getY()
            box = [x, y, x, y + font[1]]

        # XXX while it's still sticking past the right margin, chop it
        t[0].textOut(word + ' ')
        box[2] = t[0].getX()

    add_link(c, box, link)

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
    'pre': ('Courier', 0.8*em),
    }

def italicize(font):
    return italic, font[1]

def codify(font):
    return ('Courier-Bold' if font[0] == bold or font[0].endswith('-Bold') else
            'Courier-Oblique' if font[0] == italic or font[0].endswith('-Oblique') else
            'Courier', font[1])

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

def push_font(t, font_stack, font):
    font_stack.append(font)
    t[0].setFont(*font)

def render(corpus, bookmark, c, xml):
    print("PDFing", bookmark)
    c.bookmarkPage(bookmark, fit='XYZ')  # `fit` to suppress zooming out to whole page
    title = bookmark
    font_stack = [(roman, 1*em)]
    t = [start_page(c, font_stack[-1])]
    stack = [('element', xml)]
    link = None
    while stack:
        kind, obj = stack.pop()
        new_font = False
        if kind == 'element':
            if obj.tag in block_fonts:
                font = block_fonts[obj.tag]
                size_diff = font[1] - font_stack[-1][1]
                push_font(t, font_stack, font)
                new_font = True
                newline(c, t, font)
                if size_diff > 0:
                    t[0].moveCursor(0, size_diff * 1.2)
            if obj.tag in inline_fonts:
                font = inline_fonts[obj.tag](font_stack[-1])
                push_font(t, font_stack, font)
                new_font = True
            if obj.tag == 'title':
                title = obj.text
            if get_link(obj):
                link = resolve_link(corpus, get_link(obj))
            if obj.text is not None and obj.tag != 'title':
                render_text(c, t, obj.text, font_stack[-1], link)
            if obj.tail is not None:
                stack.append(('text', obj.tail))
            if new_font:  # must go atop the tail!
                stack.append(('restorefont', None))
            if get_link(obj):
                stack.append(('endlink', None))
            for kid in reversed(list(obj)):
                stack.append(('element', kid))
        elif kind == 'text':
            render_text(c, t, obj, font_stack[-1], link)
        elif kind == 'endlink':
            link = None
        else:
            assert kind == 'restorefont'
            font_stack.pop()
            t[0].setFont(*font_stack[-1])
            #newline(c, t)

    c.drawText(t[0])
    c.showPage()
    c.addOutlineEntry(title, bookmark, level=0)

def main(path):
    liabilities = path + '/liabilities'
    rfname = liabilities + '/et-book-roman-old-style-figures.ttf'
    pdfmetrics.registerFont(TTFont(roman, rfname))
    ifname = liabilities + '/et-book-display-italic-old-style-figures.ttf'
    pdfmetrics.registerFont(TTFont(italic, ifname))
    bfname = liabilities + '/et-book-bold-line-figures.ttf'
    pdfmetrics.registerFont(TTFont(bold, bfname))

    canvas = Canvas('dercuano.tmp.pdf', invariant=True, pageCompression=True,
                    pagesize=pagesize)
    # pdf.js and virtually nothing else displays this:
    canvas.setTitle('Dercuano ' + os.path.basename(path)
                    + ', by Kragen Javier Sitaker, 2019')

    corpus = OrderedDict()
    corpus['index.html'] = path + '/index.html'

    notes = path + '/notes'
    for basename in os.listdir(notes):#[:47]:
        corpus['notes/' + basename] = notes + '/' + basename

    topics = path + '/topics'
    for basename in sorted(os.listdir(topics)):#[:47]:
        corpus['topics/' + basename] = topics + '/' + basename

    for i, bookmarkname in enumerate(corpus):
        sys.stdout.write('%d/%d ' % (i, len(corpus)))
        filename = corpus[bookmarkname]
        try:
            # Although this chews through all of Dercuano in 1.3
            # seconds on this netbook, it fails to parse 3% of the
            # notes because they have things like raw HTML blocks in
            # them, which Python Markdown doesn't XMLify (e.g., ``<tr>
            # <td>1 <td>0.4%``.)  Maybe I can preprocess everything
            # with HTML Tidy or something.  sgmllib and htmllib are
            # removed in Python 3, and HTMLParser (html.parser) is a
            # tag-soup parser.
            tree = ET.parse(filename)
        except Exception:
            print("parse error on", bookmarkname + ":", sys.exc_info()[1])
            try:
                from elementtidy import TidyHTMLTreeBuilder
                tree = TidyHTMLTreeBuilder.parse(filename)
                print("recovered using elementtidy")
            except Exception:
                print("elementtidy failed too:", sys.exc_info()[1])
                render(corpus, bookmarkname, canvas,
                    ET.fromstring('<html>XML parse failure</html>'))
                continue

        render(corpus, bookmarkname, canvas, tree.getroot())

    canvas.save()

if __name__ == '__main__':
    cgitb.enable(format='text')
    main(sys.argv[1])
