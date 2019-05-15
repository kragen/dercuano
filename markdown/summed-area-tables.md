a logarithmic-time alternative to summed-area tables for reducing arbitrary semigroup operations over arbitrary ranges (a generalization of RMQ segment trees)
====

Kragen Javier Sitaker <kragen@canonical.org>
Thu Dec 6 03:37:01 EST 2012

## Summary ##

There's an alternative to summed-area tables with a small, linear
space cost and linear construction time and space, providing worst-case
logarithmic-time reduction over arbitrary intervals under arbitrary
semigroup operations, and which supports updates efficiently, unlike
summed-area tables.  The algorithm is like twenty fricking lines of code
if you leave out the "update" and "small" parts.

I am surely not the original discoverer of any of this.

## Introduction to abstract algebra ##

Abstract algebra is the study of what you can deduce from minimal sets
of axioms about some set of things and operations on them.  A lot of it
seems to be taxonomic, assigning names to particular sets of axioms.
This is cool because once you establish that, say, 32-bit bitstrings
form a semilattice under the bitwise-OR operation, you can apply every
theorem that anybody's ever proven about semilattices to 32-bit
bitstrings and OR.

In particular, as I think Stepanov first realized, the correctness of an
algorithm depends on these algebraic properties of the data it's
manipulating.  (Typically it also depends on operations being
computable, and its efficiency depends on the complexity of that
computation, which are perhaps unfortunately not within the purview of
abstract algebra.)

A magma is a set associated with a binary operation that's closed over
that set.

A semigroup is an associative magma.  An example is the set of nonempty
finite strings over some alphabet, with concatenation as the binary
operation.

A semilattice is a semigroup whose operation is commutative and
idempotent; in general a semilattice is a partially ordered set of some
kind, with a unique smallest element, where the binary operation is the
operation of finding the largest upper bound of the elements.  Aside
from the obvious examples of totally ordered sets like integers, things
like 32-bit bitstrings under bitwise OR or AND form semilattices.

A monoid is a semigroup with identity.  String concatenation is the
usual example; the empty string is the identity element.

A group is a monoid where every element has inverse for every element.
It's sufficient to have a left inverse for every element; from that you
can get identity (I think!) and right inverse.

## Summed-area tables ##

Franklin Crow's 1984 paper, "Summed-area tables for texture mapping"
calls them "summed-area tables", and Graphics Gems called them "sum
tables".  More recently, they're known as "integral images".  In the
one-dimensional case, they allow you to calculate the sum of values in
an arbitrary interval in constant time by subtracting the values from
the summed-area table at the ends of the interval: sum(f[m:n]) =
-sat(f)[m] + sat(f)[n], where sat(f)[i] = sum(f[0:i]), assuming f's
indexes start at 0.

### N-dimensional case ###

You can compute an N-dimensional sum table; sat(f)[i0, i1, ... in] is
sum(f[0:i0, 0:i1, ... 0:in]).  In some interesting sense, more
dimensions makes it more powerful: the set of queries that can be
answered in constant time grows exponentially with the number of
dimensions, while the constant-time factor only grows linearly with the
number of dimensions.

### Decimation ###

As an extension, you can use a decimated summed-area table, with
values only present every (e.g.) 16th or 32nd index, without losing
the constant-time property.  You may have to consult the original
array, but only up to 2\*(16-1) or 2\*(32-1) values of it, which is
constant.  If you needed to keep the original array around anyway, this
dramatically reduces the space cost of the technique without slowing it
down too much, which (I speculate) might actually make it faster.

N-dimensional decimation is nontrivial because you can't just store the
values at the lattice points; to keep the constant-time guarantee, you
have to store values for every point *at least one* of whose coordinates
is a round number.  This means decimation basically only saves you a
linear factor of 16 or 32 or whatever, and you have to use a
sparse-array representation to get any good out of it.

### Generalization over operations ###

This problem, sum(f[m:n]), is a specific case of the general idea of
"[range queries][]".

[range queries]: http://en.wikipedia.org/wiki/Range_Queries

Sum tables generalize beyond integer addition.  Clearly they work fine
for mod-N integer addition, vector addition, and the combination of the
two (e.g. XOR).  In fact, you can use summed-area tables over arbitrary
groups, as long as the group operation and inverse are computable.  (The
range query is constant time only as long as those computations are
constant time.)

(For the N-dimensional case, I think you may also need commutativity,
but I'm not sure.)

## A logarithmic-time alternative to sum tables for semigroups ##

But what do you do if you're interested in an operation that doesn't
have a left inverse?  For example, the "minimum" operation (or in
general the meet operation of a meet-semilattice) can't have inverses
of elements, because it's idempotent, so you can't compute it with a
sum table.

But you *can* compute it in logarithmic time with a tree.  Let

    mint(f, m, n) = nil if m == n
                  = (m, n, min(f[m:n]), mint(f, m, floor((m+n)/2)),
                                        mint(f, floor((m+n)/2), n)) otherwise

You can compute this in linear time, assuming a constant-time binary min
operation, as follows:

    mint(f, m, n) = nil if m == n else
                    (m, n, f[m], nil, nil) if m == n - 1 else
                    (m, n, a, b, c) where
                        k = floor((m+n)/2) and
                        (_, _, a0, _, _) = b = mint(f, m, k) and
                        (_, _, a1, _, _) = c = mint(f, k, n) and
                        a = min(a0, a1)

Now if you precompute mint(f, 0, f.length), which is a balanced binary
tree with 2*f.length - 1 nodes, not counting the nils, and which can
be computed in linear time, you can compute min(f[m:n]) for arbitrary
m, n in logarithmic time given that tree.  That algorithm is
straightforward:

    tmin((a, b, c, d, e), m, n) =
        c   if a >= m and b <= n
        nil if a >= n or b <= m
        nmin(tmin(d, m, n), tmin(e, m, n)) otherwise

    where nmin(a, b) = b if a == nil
                       a if b == nil
                       min(a, b) otherwise

This algorithm applies to any semigroup over the elements; it can be
used to calculate sums as easily as it can be used to calculate minima,
although less efficiently than a sum table.

### Space reduction: decimation ###

Analogously to sum tables, if your leaf nodes represent spans of some
16 or 32 elements instead of 1, you get a dramatic space reduction
without losing the logarithmic-time asymptotic performance.

### Space reduction: array storage ###

The contents of the tree produced by the mint() function depends only
on m and n, except for the min(f[m:n]); and if f.length is a power of
2, it is a full binary tree.  A full binary tree can be stored, as in
the classic binary heap, in an array a such that the children of the
element at a[i] are at a[2i+1] and a[2i+2] (zero-based).  So you can
store the minima for the tree in an array (without decimation, of
2*f.length - 1 elements) rather than allocating numerous nodes on the
heap.

This requires a slight enhancement to the lookup algorithm to
recompute the same (m, n) as the construction algorithm, rather than
looking them up in the tree.

### Constant-space bottom-up construction ###

If you construct the tree recursively, in addition to the O(N) space
for the results, you need O(log N) stack space.  But that is not
necessary.  If you're using the array storage suggested in the
previous section, you can fill the array starting from the end, so
that the only auxiliary storage you need for the construction process
is a simple counter.

### Enhancement: updates in logarithmic time ###

If you update an element of the original array, you can update the tree
nodes going back up to the root to reflect your update in worst-case
O(log N) time.  Appending or removing elements at the end of the array
can be handled similarly, although sometimes appending an element will
involve creating a new root node, which (in the array representation of
the tree) is worst-case O(N), but amortized constant time.

This is a reason you might actually want to use these trees to handle
range-sum queries rather than using sum tables: updating this tree takes
O(log N) time, while updating a sum table takes O(N) time.

### Enhancement: indices ###

In the case where the semigroup operation is exactly minimum or
maximum over a totally ordered set, the value stored in each treenode
will be the value of one of the items in the original array.  In this
case it is strictly more powerful to store the index of that item
rather than its value.  This may be useful if you have some other data
that are indexed the same way.

This allows the algorithm to solve the "range minimum query" or RMQ
problem, for which it is known as the "segment tree" algorithm.  Danielp
wrote a [really awesome tutorial on RMQ][] on Topcoder.

[really awesome tutorial on RMQ]: http://community.topcoder.com/tc?module=Static&d1=tutorials&d2=lowestCommonAncestor

The constant-time "sparse table" algorithm given in that article
unfortunately only works for semilattices rather than general semigroups
including arbitrary monoids.

### N-dimensional case ###

This generalizes easily to quadtrees, octrees, etc., although the
efficiency guarantees are not as good.

## A constant-time alternative to sum tables for semigroups ##

A.C. Yao published one in 1982, "Space-Time Tradeoff for Answering Range
Queries", but I don't know it.  I think it's explained in the
aforementioned [really awesome tutorial on RMQ][], involving a reduction
to the least-common-ancestor problem, but I don't understand it yet.

## Thanks ##

To John Cowan, Gian Perrone, and Seth David Schoen for discussion.

<link rel="stylesheet" href="greyonbeige.css" />

<style>
/**************************************** paragraph layout, typography */

body {
     font-family: Optima, sans-serif;
     font-size: 1.3em;
     margin: 1.3em;
}

p {
     line-height: 1.5em;
     text-align: justify;
     max-width: 40em;
     margin: 0 0 0 2em;
     text-indent: -1em;
}

pre {
    margin-left: 2em;
    max-width: 100%;
    overflow-x: auto;
}

/* versals; commented out:

p:first-letter { font-size: 3em; float: left; line-height: 1em; margin: 0 0.1em 0 -0.333em }
p + p:first-letter, pre + p:first-letter { font-size: 1em; float: none }
body p { text-indent: 0 }
body p + p, body pre + p { text-indent: -1em }

/**/


/**************************************** headers */

h1, h2, h3, h4, h5, h6, .addtoc_title {
      font-family: Palatino, serif;
      font-weight: normal;
      font-variant: small-caps;
      margin-left: 0.25em; margin-right: 0.25em;
}

h1 { letter-spacing: 6px; padding-bottom: 6px; font-size: 1.5em; }
h2 { letter-spacing: 6px; padding-bottom: 6px; font-size: 1.25em; }
h3 { letter-spacing: 4px; padding-bottom: 4px; font-size: 1.1em; }
h4 { letter-spacing: 3px; padding-bottom: 3px; font-size: 1em; }


/**************************************** table of contents */

body .addtoc_toc {
     float: right;
     background-color: inherit;
     color: inherit;
     border: 0;
     width: 16em;
     margin-left: 1em;
}

.addtoc_toc li { line-height: 1.5em }

</style>

<script src="http://canonical.org/~kragen/sw/addtoc.js"></script>
