Dercuano
========

(You can download the latest build, full of prerendered HTML, at
<http://canonical.org/~kragen/dercuano-20191215.tar.gz>.  It's also at
<https://perma.cc/RAA7-C6LE>.)

I have a few thousand pages of notes I mostly haven’t published in any
form, and I’m not confident I’ll be able to keep a server running to
serve them up.  So Dercuano (a mutated version of the Spanish word
“cuaderno”, “notebook”, and also delightfully an anagram of “educaron”,
as John Cowan points out) is a quick system I hacked together to bundle
them up into an archive of pregenerated HTML, which anyone who has a
copy can unpack and read, without requiring any online resources.

Status
------

At this point, the visual appearance of the text is about as good as
can be expected from web browsers and importing mass quantities of
Markdown; which is to say, it would look better with justification and
hyphenation, but that’s not in the cards, and there are a lot of
places where ASCII-art diagrams and tables are used instead of SVG
diagrams or something and HTML tables (see
[dercuano-drawings](markdown/dercuano-drawings) for some notes on this
situation), and none of the source code samples are
syntax-highlighted.

The ET Book fonts I’m using, although generally much nicer than more
everyday fonts, have some drawbacks, which hopefully I can improve
(see [dercuano-stylesheet-notes](markdown/dercuano-stylesheet-notes)
for more details.)

I’ve put this together over the last nine months. The
notes are now considerably easier to read in this form than as plain
text files, due to the substantially improved formatting, hyperlinks
between notes, chronological organization, and tagging by topics.

I may hack together some kind of web UI for adding things to the
triple store, but so far I’ve been adding them by hand.  But now it
seems like the time is starting to be linear in the number of
documents I add, largely having to do with manual categorization more
than writing code.  I’ve made some crude efforts in the direction of
Bayesian classification, but they need more work.

Copyright status
----------------

The text of Dercuano, and the overall compilation, are by me and are
in the public domain (see [`intro.md`](intro.md) for details); but it
includes the ET Book font, which has its own license (see
[`liabilities/LICENSE.ETBook`](liabilities/LICENSE.ETBook)), and as of
this writing, the source repository also includes Bogusław Jackowski
and Janusz M. Nowacki's font Latin Modern Mono Light Condensed
(regular and oblique) for generating PDF files, which is licensed
under the [GUST Font License](GUST-FONT-LICENSE.txt) and derived
originally from Knuth's Computer Modern Teletype, which is in the
public domain.  I translated it from [the OTF files on
CTAN](https://www.ctan.org/tex-archive/fonts/lm/fonts/opentype/public/lm)
using FontForge.

Dependencies
------------

Dercuano depends on the Python Markdown module, the one started by
Manfred Stienstra, and Python 2 or 3.  I’m using 2.7.12, but it seems to
also work with 2.7.3, 2.7.6, and 3.4.3.

The PDF generation depends on a Python PDF generation library called
Reportlab.  It attempts to use Janos Guljas's
PyTidyLib wrapper for the W3C's HTML Tidy library if it is
installed, but if not, it falls back on just using ElementTree's XML
parser, which is part of the Python standard library.