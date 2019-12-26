#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Parse HTML output to generate a PDF.

This is still just the crudest sketch of PDF generation for Dercuano.
Missing pieces include:

- <pre>
- Unicode subscripts (superscripts are OK)
- bullets
- Greek (all of "ε₀ ≈" is no good)
- tables
- Chinese
- internal links (between pages)
- external links (to URLs)
- an outline that doesn't zoom you out to a whole page
- font sizes
- bold
- not resetting <code> and <em> when spilling onto a new page
- dingbats like × (no, that one is okay, also centered dot and degrees)
- topic pages
- main table of contents
- JS tables of contents for individual notes
- a layout engine capable of handling varying font sizes in a line
- chronological ordering
- font fallbacks for missing characters
- handling of non-well-formed HTML (maybe PyTidyLib)?
- not putting spaces after tags
- maybe making the output file less than 6.8 megabytes?? not using
  base85 would fucking help
- wrapping overlong lines so they don't get cut off
- colored titles
- hyphenation and justification

It also takes three minutes to run on my netbook and generates a 3803-page PDF,
so maybe some kind of output caching system would be useful.

"""
from __future__ import print_function

import cgitb
import sys
import os
import xml.etree.cElementTree as ET

from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont



roman = 'et-book-roman'
italic = 'et-book-italic'
# see dercuano-hand-computers for the origins of these numbers
em = 12
pagesize = (24 * em, 60 * em)
left_margin = top_margin = bottom_margin = right_margin = 0.5 * em

def start_page(c):
    c.setFont(roman, em)
    return c.beginText(left_margin, pagesize[1]-top_margin-em)

def newline(c, t):
    t[0].textLine()
    if t[0].getY() < bottom_margin + 8*em:  # XXX fudge factor for layout bugs
        c.drawText(t[0])
        c.showPage()
        t[0] = start_page(c)

def render_text(c, t, text, font):
    max_y = pagesize[0] - right_margin
    words = text.split()
    for word in words:
        width = c.stringWidth(word, *font)
        if t[0].getX() + width > max_y:
            newline(c, t)

        t[0].textOut(word + ' ')

block_fonts = {
    'p': (roman, 1*em),
    'h1': (roman, 2*em),
    'h2': (roman, 1.7*em),
    'h3': (roman, 1.4*em),
    'h4': (roman, 1.2*em),
    'h5': (roman, 1.1*em),
    'h6': (roman, 1*em),
    'li': (roman, 1*em),
    }

def italicize(font):
    return italic, font[1]

def codify(font):
    return 'Courier', font[1]

inline_fonts = {'i': italicize,
                'em': italicize,
                'code': codify}

def push_font(t, font_stack, font):
    font_stack.append(font)
    t[0].setFont(*font)

def render(filename, c, xml):
    c.bookmarkPage(filename)
    title = filename
    t = [start_page(c)]
    stack = [('element', xml.getroot())]
    font_stack = [(roman, 1*em)]
    while stack:
        kind, obj = stack.pop()
        new_font = False
        if kind == 'element':
            if obj.tag in block_fonts:
                font = block_fonts[obj.tag]
                size_diff = font[1] - font_stack[-1][1]
                push_font(t, font_stack, font)
                new_font = True
                newline(c, t)
                if size_diff > 0:
                    t[0].moveCursor(0, size_diff * 1.2)
            if obj.tag in inline_fonts:
                font = inline_fonts[obj.tag](font_stack[-1])
                push_font(t, font_stack, font)
                new_font = True
            if obj.tag == 'title':
                title = obj.text
            if obj.text is not None:
                render_text(c, t, obj.text, font_stack[-1])
            if obj.tail is not None:
                stack.append(('text', obj.tail))
            if new_font:  # must go atop the tail!
                stack.append(('restorefont', None))
            for kid in reversed(list(obj)):
                stack.append(('element', kid))
        elif kind == 'text':
            render_text(c, t, obj, font_stack[-1])
        else:
            assert kind == 'restorefont'
            font_stack.pop()
            t[0].setFont(*font_stack[-1])
            #newline(c, t)

    c.drawText(t[0])
    c.showPage()
    c.addOutlineEntry(title, filename, level=0)

def main(path):
    notes = path + '/notes'
    liabilities = path + '/liabilities'
    rfname = liabilities + '/et-book-roman-old-style-figures.ttf'
    pdfmetrics.registerFont(TTFont(roman, rfname))
    ifname = liabilities + '/et-book-display-italic-old-style-figures.ttf'
    pdfmetrics.registerFont(TTFont(italic, ifname))

    canvas = Canvas('dercuano.tmp.pdf', invariant=True, pageCompression=True,
                    pagesize=pagesize)
    for html in os.listdir(notes):#[:22]:
        try:
            # Although this chews through all of Dercuano in 1.3
            # seconds on this netbook, it fails to parse 3% of the
            # notes because they have things like raw HTML blocks in
            # them, which Python Markdown doesn't XMLify (e.g., ``<tr>
            # <td>1 <td>0.4%``.)  Maybe I can preprocess everything
            # with HTML Tidy or something.  sgmllib and htmllib are
            # removed in Python 3, and HTMLParser (html.parser) is a
            # tag-soup parser.
            tree = ET.parse(notes + '/' + html)
        except Exception:
            print("parse error on", html + ":", sys.exc_info()[1])
        else:
            render(html, canvas, tree)

    canvas.save()

if __name__ == '__main__':
    cgitb.enable(format='text')
    main(sys.argv[1])