#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Binary relations: a tiny subset of Binate, as a Python DSL.

Designed for read-heavy workloads.

This version is somewhat unsatisfactory because it computes the
inverse on demand and memoizes it, while for what I’m doing, I’d
prefer that it compute the inverse eagerly, at creation time.  The
reason is that I want to store each verb in Dercuano’s triple store as
a binary relation like this, and I want queries on both them and their
inverses to be fast; even if I fork off a bunch of subprocesses, I
don’t want each subprocess to redundantly recompute the inverse
relations.

I think that for now I’ll just resort to computing the inverse for
each verb explicitly in Dercuano and hope I don’t forget.

"""
import doctest

class Relation:
    """Binary relation.

    >>> x = Relation([(3, 4), (3, 5), (4, 6)])
    >>> x
    Relation([(3, 4), (3, 5), (4, 6)])
    >>> list(x)
    [3, 4]
    >>> x[3]
    [4, 5]
    >>> x[4]
    [6]
    >>> x | x
    Relation([(3, 6)])
    >>> x | Relation([(3, 'c'), (4, 'd'), (5, 'e'), (6, 'f')])
    Relation([(3, 'd'), (3, 'e'), (4, 'f')])
    >>> ~x
    Relation([(4, 3), (5, 3), (6, 4)])
    >>> x[10]
    []
    >>> x.put(4, 2)
    >>> x[4]
    [2, 6]
    >>> ~x
    Relation([(2, 4), (4, 3), (5, 3), (6, 4)])
    >>> Relation()
    Relation([])
    """

    def __init__(self, pairs=()):
        self._contents = {}
        self._inverse = None
        for k, v in sorted(pairs):
            self.put(k, v)

    def put(self, k, v):
        if k not in self._contents:
            self._contents[k] = []

        if v not in self._contents[k]:
            # This is going to suffer scalability problems on large
            # relations of course; a quick test making a list of 50000
            # integers in IPython reports 20–50 μs to index into the
            # list, ≈90 μs to append to its end, and then 3000–6000 μs
            # to sort it (with or without the out-of-order item),
            # which is on the order of 100 ns per item.  So building
            # up a list of N values associated with a single key like
            # this will take about 50N² ns.  For what I’m doing at the
            # moment, it seems preferable to storing the items in a
            # set() and sorting the items every time they’re read,
            # delivering them in a nondeterministic order,
            # implementing a B-tree, or maintaining a per-key dirty
            # bit, any of which would avoid this N² term.
            self._contents[k].append(v)
            self._contents[k].sort()
            self._inverse = None

    def __repr__(self):
        return 'Relation(%s)' % [(k, v) for k in sorted(self._contents.keys())
                                 for v in self._contents[k]]

    def __iter__(self):
        return iter(self._contents)

    def __getitem__(self, k):
        try:
            return self._contents[k]
        except KeyError:
            return []

    def __or__(self, other):
        return Relation((k, v2) for k in self
                        for v in self[k]
                        for v2 in other[v])

    def __invert__(self):
        if self._inverse is None:
            self._inverse = Relation((v, k) for k in self for v in self[k])
        return self._inverse

if __name__ == '__main__':
    doctest.testmod()
