Dercuano
========

(You can download the latest build, full of prerendered HTML, at
<http://canonical.org/~kragen/dercuano-20190630.tar.gz>.)

I have a few thousand pages of notes I mostly haven’t published in any
form, and I’m not confident I’ll be able to keep a server running to
serve them up.  So Dercuano (a mutated version of the Spanish word
“cuaderno”, “notebook”) is a quick system I hacked together to bundle
them up into an archive of pregenerated HTML, which anyone who has a
copy can unpack and read, without requiring any online resources.

I wrote it in Python 2, even though it’s 2019, for reasons of
expediency.  I still have a wider selection of Python 2 modules
installed on this machine.

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

Navigability leaves something to be desired, although it’s more
navigable than the kragen-tol archives were.

I’ve put this together over the last month and a half.  I have about
1200 individual notes I might include, totaling almost 5 megs
compressed.  I
am about two-thirds done;
at this point I’m able to import existing notes into the system
at about 16–32 notes per hour, which I might speed up with some more code.
The
notes are now considerably easier to read in this form than as plain
text files, due to the substantially improved formatting, hyperlinks
between notes, chronological organization, and tagging by topics.

I may hack together some kind of web UI for adding things to the
triple store, but so far I’ve been adding them by hand.  But now it
seems like the time is starting to be linear in the number of
documents I add, largely having to do with manual categorization more
than writing code.  I’ve made some crude efforts in the direction of
Bayesian classification, but they need more work.

Dependencies
------------

Dercuano depends on the Python Markdown module, the one started by
Manfred Stienstra, and Python 2.  I’m using 2.7.12, but it seems to
also work with 2.7.3 and 2.7.6.  It does not work with Python 3,
though fixing that shouldn’t be hard.
