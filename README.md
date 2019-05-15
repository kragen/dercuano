Dercuano
========

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

Over the last three weeks I've importe

I’ve spent about 30 hours putting this together,
which means that at this point it’s gone from an “afternoon hack”
to a “week-long hack”, and now it’s looking kind of okay actually.  I have about
1200 individual notes to stick in here, totaling almost 5 megs
compressed.  I
am about two or three doublings away from finishing the job;
at this point I’m able to import existing notes into the system
at about 16–32 notes per hour, which I hope to speed up soon.
Unfortunately at this point it’s taking 15 seconds to rebuild
the HTML tree from scratch.  The
notes are now considerably easier to read in this form than as plain
text files, due to the substantially improved formatting, hyperlinks
between notes, chronological organization, and tagging by topics.

I may hack together some kind of web UI for adding things to the
triple store, but so far I’ve been adding them by hand.  But now it
seems like the time is starting to be linear in the number of
documents I add, largely having to do with manual categorization more
than writing code.

Dependencies
------------

Dercuano depends on the Python Markdown module, the one started by
Manfred Stienstra, and Python 2.  I’m using 2.7.12, but it seems to
also work with 2.7.3 and 2.7.6.  It does not work with Python 3.

Time log
--------

2019-04-26 21:41 to 02:25 (4½ hours): initial version: 11 notes, tables of contents, HTML generation  
2019-04-27 10:38 to 14:30 (4 hours): get titles from Markdown, add links between notes, add CSS, clean up categorization, add 11 more notes  
2019-04-27 16:28 to 21:34 (5 hours): fix CSS to be pretty nice instead of outstandingly shitty; test on Android; push to Gitlab  
2019-04-28 01:16 to 02:30 (1 hour): add 21 more notes, bringing the total to 44  
2019-04-28 13:27 to 16:24 (3 hours): add 46 more notes, bringing the total to 90  
2019-04-28 17:25 to 19:55 (2½ hours): tweak CSS some more, add introduction to main page, add note counts and word counts  
2019-04-28 22:13 to 22:45 (½ hour): add start and end dates to notes  
2019-05-01 00:00 to 01:00 (1 hour): add 9 more notes, tweak CSS  
2019-05-01 10:00 to 12:00 (2 hours): add 19 more notes, change sort order, add author to pages  
2019-05-01 18:40 to 19:20 (½ hour): try to hack together a Bayesian classifier for new notes  
2019-05-04 14:00 to 18:00 (4 hours): add 50 more notes  
2019-05-04 18:00 to 21:30 (3½ hours): add 71 more notes  
2019-05-07 19:00 to 21:00 (2 hours): add ET Book font, tweak CSS to accommodate it  

After that, I stopped logging my time.