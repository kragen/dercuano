Dercuano is a self-contained downloadable HTML tarball containing a
book’s worth of disorganized notes I’ve made over the last few years.
As an alternative option for computer systems incapable of handling a
downloadable HTML tarball, I've hacked together an inferior PDF
rendering of it as well, which comes to some 4000 pages, formatted for
comfortable reading on hand computers.

Buried among the errors, red herrings, and ratholes, there
are numerous wonderful insights (perhaps even a few of them original),
many fascinating facts about the world (many of which are true, and a
few of which are original observations), and a wide variety of
inventive ideas about what is possible and what could be done, in
particular ideas about how to improve the world with new hardware and
software — a few of them workable.  I’ve published little of it
previously.

Disclaimer, preface, and warning
--------------------------------

Mostly, I made
these notes for myself, though with the intention of someday getting
most of them into shape for publication, but lacking the discipline imposed by
regular publication, that’s probably not going to happen.  It may not
happen anyway.  So, fuck it!  Here it is, incomplete as it is — I hope
you enjoy it!

### Beware, this is (almost) all wrong ###

Much of what is written here is wrong in a variety of ways.

- Some of it is factually wrong (for example, on many occasions I confused
  the vector space GF(2)³² with the very different field GF(2³²) of degree-32
  polynomials over GF(2));
- some of it was factually correct at one point but has since become outdated;
- some of it is okay at a factual level but has led me to incorrect
  conclusions due to my misunderstanding of the relationships between
  the facts;
- some of it is just a farrago of incoherent sentence fragments;
- some of it is a collection of atomic facts that are individually
  coherent and could, in theory, be assembled into a meaningful whole,
  but so far have not been;
- some of it documents the embarrassingly long path of reasoning by
  which I eventually argued myself around to a reasonable conclusion
  which was, in retrospect, obvious from the start; and
- some of it, perhaps most of it, amounts to getting distracted from
  the most important aspects of an issue by some minor detail.

On the other hand, some of it is correct.  Of the correct part, most
is unoriginal — sometimes I’m just taking notes on well-established
concepts, and sometimes I’m laboriously rediscovering things that are
already obvious to others — while some small part is original.
Unfortunately, I don’t know which part.

Most of these notes are about things I barely understood, or
didn’t really understand at all, when I wrote the notes.  In some
cases, I later came to understand them better, but in other cases I’ve
lost even what understanding I had.  Nearly every note is incomplete;
of those that are complete, very few have been checked for correctness
or revised for readability.  So, beware.

Many of the dates are only approximate.

### Dercuano is scholarly work in progress, but not a completed scholarly publication ###

One of the distinguishing features of scholarly publications, as currently
understood, is that they are consciously situated with regard to the
existing state of knowledge: they are aware of the state of the art;
build on its successes (rather than falling victim to known
pitfalls); they explicitly describe how they relate to that existing
knowledge, declaring which pieces of its foundation are sourced from
existing work and what its novel contributions are; and they give
credit to existing scholarly work.

By and large, I appreciate these values, and I would like to do work
that practices them.  Sometimes, in the past, I have.  Dercuano is not
such a work.  It is full of cases where I rediscovered known ideas
(sometimes incorrectly) and cases where I think something is true, due
to other people’s previous work, but I don’t remember who demonstrated
it, or in many cases, precisely what they demonstrated.  In many cases
there’s existing work in a field that I haven’t done the work to
understand; often I find that attempting to rederive such work from
first principles is the best way for me to understand it, and much of
Dercuano consists of such attempts.  This is not due to malice, but
simply because doing scholarly work properly is a lot of effort, and I
haven’t finished that work, and in fact I’ve given up on ever finishing it for
most of the notes in Dercuano.  From a scholarly perspective, Dercuano
is best understood as a collection of unfinished notes on ideas that
mostly seem promising and merit further investigation, which could lead to
a scholarly publication, rather than a scholarly publication in itself.

The work that leads up to a scholarly publication invariably involves
a great deal of information-gathering, experimentation, thinking,
revision, and usually discussion before reaching the point of actually
representing an advance on the state of the art.  When you begin
learning about a topic, you have no idea what the state of the art is,
what is true or false, or what will work;
bit by bit, you find these things out.  Sometimes this
process is recorded, for example in laboratory notebooks, but it
usually remains secret, in part because of all of the embarrassing
errors during the process.  Preregistration of clinical trials is
starting to reduce this secrecy in medicine, but it would be wonderful
to see more people doing more of their thinking in the open.  Dercuano
is an example of what I would like to see more of: scholarly work
exposed and done in the open even before reaching the level of
a scholarly publication.  I am fortunate to have been in the position
where I could do this.

### Size and public-domain dedication ###

On 2019-12-28 as I write this, the Dercuano tarball is 3.6 megabytes
and contains some 1.2 million words in 882 notes,
about 3500 paperback pages’
worth of text.  The PDF rendering mentioned above uses a page size
slightly smaller than standard for improved readability on hand
computers.

As far as I’m concerned, everyone is free to redistribute Dercuano, in
whole or in part, modified or unmodified, with or without credit; I
waive all rights associated with it to the maximum extent possible
under applicable law.  Where applicable, I abandon its copyright to
the public domain.  I wrote and published Dercuano in Argentina.

The exception to the above public-domain dedication is the ET Book
font family used, licensed under [the X11
license](liabilities/LICENSE.ETBook).  This doesn’t impede you from
redistributing or modifying Dercuano but does prohibit you from
removing the font’s copyright notice and license (unless you also
remove the font).

(The source repository also contains some other fonts which are used
to produce a PDF, but those are not included in the HTML tarball.)

### Gitlab ###

At this writing, there’s [a replica of this repo on
Gitlab](https://gitlab.com/kragen/dercuano).