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

I’ve been hacking on this piece of shit for four and a half hours.  I have about
1200 individual notes to stick in here, totaling almost 5 megs
compressed.  So far I have stuck 11 of them in, totaling 134K and
52,000 words.  So I
am about seven doublings away from finishing the job;
the last doubling (well, near tripling)
took an hour, and the doubling before that took half an hour.
Unfortunately at this point it’s taking an entire second or more to rebuild
the HTML tree from scratch.  The
notes are currently slightly harder to read in this form than as plain
text files, due to the lack of CSS and date/time metadata.

I may hack together some kind of web UI for adding things to the
triple store, but so far I’ve been adding them by hand.

Dependencies
------------

Dercuano depends on the Python Markdown module, the one started by
Manfred Stienstra, and Python 2.  I’m using 2.7.12.

Time log
--------

2019-04-26 21:41 to 02:25
2019-04-27 10:38 to ???
