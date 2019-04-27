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

I've been hacking on this piece of shit for three hours.  I have about
1200 individual notes to stick in here, totaling almost 5 megs
compressed.  So far I have stuck two of them in, totaling 25K.  So I
am about eight or nine doublings away from finishing the job.  The
notes are currently slightly harder to read in this form than as plain
text files, due to the lack of CSS, date/time metadata, and tables of
contents.

I may hack together some kind of web UI for adding things to the
triple store, but so far I’ve been adding them by hand.

Dependencies
------------

Dercuano depends on the Python Markdown module, the one started by
Manfred Stienstra, and Python 2.  I’m using 2.7.12.
