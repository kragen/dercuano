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

I’ve been hacking on this thing for 24 hours,
which means that at this point it’s gone from an “afternoon hack”
to a “weekend hack”, and now it’s looking kind of okay actually.  I have about
1200 individual notes to stick in here, totaling almost 5 megs
compressed.  I
am about three or four doublings away from finishing the job;
the last doubling, adding 46 documents, took less than three hours, but
the last doubling, adding 21 documents, took six hours,
though only the last hour was adding documents;
the previous one, adding 11 documents, took three hours;
the doubling (well, near tripling) before that
took an hour, and the doubling before that took half an hour.
Unfortunately at this point it’s taking five entire seconds to rebuild
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
Manfred Stienstra, and Python 2.  I’m using 2.7.12.

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