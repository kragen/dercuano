#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Classify new notes using a naïve Bayesian classifier.  Doesn’t work yet.

For each word W, we estimate the probability that a note contains that
word P(W).  For each topic or category C, we estimate the probability
that a note belongs to that category P(C).  Finally, for each pair
(W, C) we estimate the probability that a note both contains the word
and belongs to the category P(W ∧ C).  We use Laplace smoothing (“not
to be confused with Laplacian smoothing”, says Wikipedia) to avoid
deriving absurdities.

If we have a new note of unknown categorization but known contents,
given that it contains some word W, we can estimate the probability
that it belongs to a category C by modifying its prior probability
P(C) using Bayes’ Theorem.

But what is Bayes’ Theorem?  It is phrased in terms of *conditional*
probabilities, which we can define as P(A|B) = P(A∧B) / P(B) — the
probability that A is the case given that B is the case is the
probability that both are the case, divided by the probability that B
is the case.  Solving for P(A∧B), we have P(A∧B) = P(A|B) P(B), and
since mutatis mutandis P(B|A) = P(B∧A) / P(A) = P(A∧B) / P(A), we can
derive that P(B|A) = P(A|B) P(B) / P(A).  (This comes out neater with
odds ratios, but this is good enough.)

So in this case we want to derive P(C | W), which we can calculate as
P(W|C) P(C) / P(W), or to reformulate it more conveniently, 
(P(W|C) / P(W)) P(C).

Now, if we have two independent words W₁ and W₂, then we can simply
use the result of this Bayesian inference based on one of them as the
prior probability for the other: (P(W₁|C) / P(W₁)) (P(W₂|C) / P(W₂)) P(C).
(This is the point at which the conditional formulation really starts
to shine.)  And so on for larger independent sets.  It’s going to be
more convenient to do this logarithmically; the log of the posterior
log₁₀(Pₚ(C)) = log₁₀(P(C)) + Σᵢ log₁₀(P(Wᵢ|C) / P(Wᵢ)).  That way we
can run inference without doing any multiplications, and we avoid the
risk of underflow and overflow.

What makes this a *naïve* Bayesian classifier is that we assume that
all sets of words are independent, so we can just use that naïve
procedure for all of them.  In theory we could also use words that do
*not* occur, but I’m not going to, because if I were to concatenate
two notes, the ideal set of topics for the combined post would be the
union of the topics for the original two notes; I think omitted words
will mostly give information about post length.

At the end of the inference process, for every (note, category) pair,
I have a probability.  How do I convert those probabilities into sets
of tags?  Probably the best solution for bootstrapping is to use some
quantile of the probabilities, one that gives about the right number
of categories to average posts, and include in the output an
additional set of candidate topics of similar size.

Right now my training and test sets contain 127 notes, and I have 130
topics relevant to more than one note and about 26,000 words as
currently defined, though less than 11,000 that occur in more than one
note.  This suggests that in the training phase I’ll be estimating
some 1.4 million conditional probabilities, most of which won’t be
very significant.  Each note contains on average about 900 unique
words, so doing the inference using the simple approach of just using
all the probabilities will cost about 900 lookups and addition per
topic, or 100k per note being inferred.  That’s fast enough to get
some feedback on the algorithm; in all likelihood, I could drop all
but the most informative 1% or so of words with an insignificant loss
of inferential precision.

This is giving me the wrong answer, though.  Take, for example, the
word “000919”, and the category “bicicleta”, each of which occur in
only one out of 102 training notes, which happen to be the same one.
Using Laplace smoothing, we estimate that P(“000919”) = 1/52,
P(#bicicleta) = 1/52, and P(“000919” ∧ #bicicleta) = 1/52.  From this,
we totally incorrectly calculate that P(“000919” | #bicicleta) = 1, and
thence that P(#bicicleta | “000919”) = 52 P(#bicicleta), which also
seems like it can’t be a valid form of inference, since the prior
P(#bicicleta) might be larger than 1/52.  I suppose I could just divide
counts, but I think I’ll see if reading about Bayes’ theorem and
Bayesian inference corrects my head.

In particular it seems like a single observation of “000919” ∧
#bicicleta, and no other observations of either, ought to give us
P(#bicicleta|“000919”) = P(“000919”|#bicicleta) = 0.67 or so, in the
sense that initially, lacking other information, we would expect all
four possible combinations of events to be equally likely, so Laplace
smoothing suggests that after observing a single event, our
probability estimates should be 1:2:1:1.

However, we’re trying to take into account the 101 documents where
“000919” did *not* occur; we know it’s a fairly rare word.  If we
simply estimate P(“000919”|¬#bicicleta) as 1/103 ≈ 0.0097 or
P("000919") as 2/103 ≈ 0.019, we find that P(“000919”|#bicicleta) at
.67 is really high by comparison, so we should really have great
confidence that any new document that mentions “000919” is about
bicicleta.  This is clearly wrong.  And it isn’t helped much by
supposing that the word distribution of the smoothing
instances — other documents that turn out to be about #bicicleta — are
also about .002 or .001 “000919”, unless we assume that there are a
great number of them.

This is actually sort of the problem Bayes was tackling in his
original paper, where he derived the beta distribution.  You have the
chance to observe some Bernoulli trials of some process whose success
probability you don’t know.  Will this document about #bicicleta
“succeed” at containing “000919” or not?  Initially the success
probability could be anywhere between 0 and 1; it has some prior
distribution, which Bayes assumed was uniform.  After you have
observed some number of trials, what is its distribution?  If you
observe a lot of trials, its distribution should be pretty bunched up,
approaching a Dirac delta, but after you observe only one or two
trials, you still don’t have very much information, so the
distribution should be pretty spread out.  Wikipedia tells me that,
precisely, if you’ve observed s successes and f failures, the
distribution pdf is Be(s-1, f-1), where Be(n, h) = (xⁿ⁻¹(1-x)ʰ⁻¹)/Β(n, h),
where Β(n, h) is a normalizing constant called the “beta function”;
for the integers its value is (n-1)!(h-1)!/(n+h-1)!.

Even after lots of “trials” and deriving a very precise “success
probability”, it might be that the probability isn’t very
informative — maybe 14% of your large sample of #household documents
say “security”, but so do 14% of your large sample of non-#household
documents, so the word “security” doesn’t tell you anything about
whether a document is #household or non-#household.  But if the
success probability is still largely unknown (because your sample of
#bicicleta documents only has one document in it, say), it can’t
possibly tell you very much of anything.  That doesn’t mean the
classifier as a whole is unable to classify new documents as
#bicicleta, but it will need more than one term.

(The *expectation* of the beta distribution in this case is precisely
the (s+1)/(s+1+f+1) number we get from Laplace smoothing.)

"""
from __future__ import print_function, division
import collections
import math
import random

import dercuano


class Model:
    def __init__(self, notes):
        self.categories = set().union(*(note.categories()
                                            for note in notes))
        print("%d training categories" % len(self.categories))
        words_by_note = {n: set(n.read_words()) for n in notes}
        all_words = set().union(*words_by_note.values())
        print("%d distinct words" % len(all_words))

        self.cat_counts = {cat: sum(1 for note in notes
                                    if cat in note.categories())
                           for cat in self.categories}
        self.word_counts = {w: sum(1 for note in notes
                                   if w in words_by_note[note])
                            for w in all_words}
        self.word_prob = {w: (1 + count) / (2 + len(notes))
                          for w, count in self.word_counts.items()}

        self.word_cat_counts = collections.Counter(
            (word, cat) for note in words_by_note
            for cat in note.categories()
            for word in words_by_note[note])

        self.word_cat_log_likelihoods = {}
        for k, count in self.word_cat_counts.items():
            word, cat = k
            # Here we want log₁₀(P(Wᵢ|C) / P(Wᵢ)).  First, calculate
            # P(Wᵢ|C):
            pwc = ((1 + count) / (2 + self.cat_counts[cat]))

            # To get the likelihood, we need to divide
            # that by the word’s prior probability:
            p = pwc / self.word_prob[word]
            print(word, cat, "count", count, "cn", self.cat_counts[cat],
                  "pw", self.word_prob[word], "pwc", pwc, "p", p)
            self.word_cat_log_likelihoods[k] = math.log10(p)

    def infer_cat_log_likelihoods(self, note):
        words = set(note.read_words())
        return {cat: math.log10(self.cat_prob[cat])
                for cat in self.cat_prob}

if __name__ == '__main__':
    b = dercuano.Bundle('.')
    all_notes = list(b.notes())
    random.seed(0)
    random.shuffle(all_notes)
    test_boundary = len(all_notes) // 5
    test_notes = all_notes[:test_boundary]
    training_notes = all_notes[test_boundary:]
    print("%d test notes, %d training notes" %
          (len(test_notes), len(training_notes)))
    model = Model(training_notes)
    for cat in sorted(model.cat_prob, key=model.cat_prob.__getitem__):
        print(model.cat_prob[cat], cat)
    print("%d distinct (W, C) pairs out of %d possible"
          % (len(model.word_cat_counts),
             len(model.cat_prob) * len(model.word_prob)))

    print("Most informative 0.01%:")
    def absinfo(k):
        return abs(model.word_cat_log_likelihoods[k])
    for i, (w, c) in enumerate(sorted(model.word_cat_log_likelihoods,
                                      key=absinfo,
                                      reverse=True)):
        if i > len(model.word_cat_counts) * 0.0001:
            break
        print("%+.1f%% %s %s (%.3f %.3f %s)"
              % (100 * 10**model.word_cat_log_likelihoods[w, c],
                 w, c,
                 model.word_prob[w],
                 model.cat_prob[c],
                 model.word_cat_counts[w, c]))

    # for note in test_notes:
    #     print(note.notename, ':')
    #     chances = model.infer_cat_log_likelihoods(note)
    #     for cat, log_likelihood in chances.items():
    #         print('  ', log_likelihood, cat)
