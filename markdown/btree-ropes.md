I just hacked together [a quick rope-based string system in Lua][0],
but it has rather alarming worst-case performance characteristics.
I was thinking about improving such characteristics with B-trees.

[0]: http://canonical.org/~kragen/dev3/macrope.lua

The string and rope problem
---------------------------

If you build up a long string through successive concatenations, many
string systems will suffer an O(*N*²) slowdown; for example, in LuaJIT
this takes 2.4 seconds, which works out to 42 kilobytes per second;
PUC Lua 5.2.4 is only slightly faster at 1.9 seconds:

    N = 100000
    s = ''
    for i = 1, N do s = s .. 'x' end

CPython used to be really slow at this, but has a special optimization
for this case now, so it takes such a small amount of time that it is
difficult to measure accurately; the following slight variation still
takes 700 ms, which works out to 140 kilobytes per second:

    N = 100000
    s = ''
    for i in range(N): s = t = s + 'x'

This shows the expected O(*N*²) curve, taking 2.5 seconds for *N* =
200 000 instead of *N* = 100 000.

Moreover, in these systems, if the same large string occurs as part of
*M* other strings, it uses up *M* times the space, and many of the
concatenation operations are redundant.

It’s common for such string-concatenation operations to consist of
essentially variable interpolation — filling variable holes in
otherwise-constant templates.  Ideally we wouldn’t be looping over all
that unchanging data every time we render a web page or whatever.

Ropes
-----

Ropes are trees representing immutable trees which originated in
Cedar; you could describe the essential core of the idea in OCaml as
follows:

    type rope = Leaf of string | Cat of rope * rope

The idea is that `Leaf "foo"` represents the constant string `"foo"`,
while Cat represents the concatenation of two ropes; `Cat (Leaf "foo",
Leaf "bar")` is one possible representation of the immutable string
`"foobar"`.  This gives you constant-time string concatenation (if
garbage collection is okay) and plenty of structure sharing, and you
can convert the rope to a flat string in linear time when
necessary — or just a `struct iovec` to send over the network with
`writev`.

If the leaves are nonempty, this data structure has worst-case linear
space overhead, although it can be quite large, on the order of 64×
the plain string.

If you augment this structure with lengths, you can additionally index
and slice it in logarithmic time, if it’s well balanced:

    type rope = Leaf of int * string | Cat of int * rope * rope

If we define the function `rope_length`

    let rope_length = function Leaf(a, _) -> a | Cat(a, _, _) -> a

we can state the invariant that `rope_length (Cat(a, g, d)) ==
rope_length g + rope_length d` (using “g” and “d” for *gauche* and
*droit*) and maintain this with concatenation and lifting functions:

    let leaf s = Leaf(String.length s, s)
    let cat a b = Cat(rope_length a + rope_length b, a, b)

and define a function to drop the first *n* bytes:

    let rec rope_drop n = function
     | Leaf(a, s) -> leaf (String.sub s n (a - n))
     | Cat(a, g, d) -> if n < rope_length g
         then cat (rope_drop n g) d
         else rope_drop (n - rope_length g) d

It is straightforward to define analogous functions to take the first
*n* bytes, etc.

These functions will take logarithmic time and space if the tree is
well balanced, but they can take linear time and space if the tree is
imbalanced.  Looking at the structure of `rope_drop` we can see that
it’s closely analogous to a binary-tree search where the search key in
each `Cat(a, g, d)` node is `rope_length g`, though augmented by the
past search keys.  It’s binary-searching the tree for the breakpoint.

It’s also straightforward to write a function that converts a `rope`
as defined above into a flat byte sequence; in OCaml, we invoke
`Bytes.create` with the size of the string to be created, use
`Bytes.blit_string` to copy each of the leaf nodes into the new
sequence, and finally invoke `Bytes.to_string`; alternatively you can
build up a string list and invoke `String.concat ""` on it, which does
the same thing under the covers.  This takes linear time and linear
space regardless of the balance or imbalance of the tree, but it is
necessary to be somewhat careful to avoid stack overflows.

My Lua implementation `macrope`
-------------------------------

This implementation has four kinds of nodes rather than two — it
additionally contains “variable nodes”, representing template
variables to be replaced, and “environment nodes”, which provide
values for those variables.  This allows you to instantiate a template
rope once and then use it repeatedly with different variable bindings
without having to copy it around to modify it.

Because the size of the variable nodes can vary depending on their
environment, the nodes don’t know their size, so these ropes can’t be
sliced and indexed efficiently as the above OCaml code does.

The module exports a function `var` to define variable nodes and a
function `macrope` which idempotently coerces strings to macropes.
Concatenation and parameter passing are done with the Lua `..`
concatenation operator and the normal parameter-passing mechanism:

    > macrope = require 'macrope'
    > v = macrope.var 'name'
    > s = v .. ' is the best friend of ' .. v
    > = s { name='Bob' }
    Bob is the best friend of Bob

Macropes can support large strings with linear, though poor,
efficiency:

    > x = macrope.macrope 'x'
    > for i = 1, 25 do x = x .. x end
    > =#tostring(x)
    33554432

The first two lines execute instantaneously; the third line takes
about 30–40 seconds on my laptop.  No attempt is made to cache the
results.

The O(*N*²) code above runs faster with `macrope` as follows, for *N*
above about 10,000:

    > s = macrope.macrope ''
    > for i = 1, N do s = s .. 'x' end
    > s = tostring(s)

The source code is organized as follows.  `macrope` calls a `const`
function if necessary, which is forward declared because I’m leery of
Lua’s scoping.  Each node type has its own metatable:

    # (in macrope.lua)
    local catmeta, envmeta, varmeta, constmeta, const, macrope

All these metatables “inherit from” a common prototype metatable, but
using a function that generates copies from it, rather than delegating
to it using `__index`.  They *do* share an `is_macrope` property via
`__index`, which allows the `macrope` function to be idempotent.

    local function meta()
       return {
          __index = {is_macrope = true},

The string concatenation operation is overridden to construct
concatenation nodes:

          __concat = function(car, cdr)
             return setmetatable({car=macrope(car), cdr=macrope(cdr)}, catmeta)
          end,

The function-call operation is overridden as follows to create an
environment node; note that each variable binding is coerced to a
`macrope`:

          __call = function(self, vars)
             local nvars = {}
             for k, v in pairs(vars) do nvars[k] = macrope(v) end
             return setmetatable({vars=nvars, child=self}, envmeta)
          end,

Finally, coercion to a string as implemented by the standard
`tostring` function (invoked implicitly by `print`) is done by using
an explicit stack — because the worst cases I was alluding to above
cause LuaJIT to kill the function if the stack gets more than a few
tens of thousands of stack frames deep:

          __tostring = function(self)
             local items, stack, env = {}, {}, {}
             local function put(item) table.insert(items, item) end

             self:visit(put, stack, env)

             while #stack > 0 do
                local item = table.remove(stack)
                item(put, stack, env)
             end

             return table.concat(items)
          end,
       }
    end

Mostly what remains are the `visit()` methods, which avoid recursion
by pushing continuation closures on the explicit stack — which I
managed to do in the wrong order at one point:

    catmeta = meta()
    function catmeta.__index.visit(self, put, stack, env)
       table.insert(stack, function(...) self.cdr:visit(...) end)
       return self.car:visit(put, stack, env)
    end

The environment node needs to modify the environment, then arrange to
restore it after its descendants finish executing:

    envmeta = meta()
    function envmeta.__index.visit(self, put, stack, env)
       local saved = {}
       for k, v in pairs(self.vars) do
          saved[k] = env[k]
          env[k] = v
       end

       table.insert(stack, function(put, stack, env)
                       for k in pairs(self.vars) do env[k] = saved[k] end
       end)
       return self.child:visit(put, stack, env)
    end

Note that it’s not safe to do `for k, v in pairs(saved)` because the
saved value may have been a `nil`, in which case Lua would skip it in
the iteration!

Variable nodes just delegate to their value (which, remember, was
coerced to a `macrope` when the environment node was created),
assuming the value exists:

    varmeta = meta()
    function varmeta.__index.visit(self, put, stack, env)
       local val = env[self.name]
       if val == nil then error("name not found: " .. self.name) end
       return val:visit(put, stack, env)
    end

We need a function to export from the module to instantiate variables:

    local function var(name)
       return setmetatable({name=name}, varmeta)
    end

Constant nodes, the `Leaf` of the OCaml implementation above, simply
invoke `put` to append their contents to the growing output buffer:

    constmeta = meta()
    function constmeta.__index.visit(self, put, stack, env)
       put(self.value)
    end

There is a `const` constructor which could perhaps be inlined into the
`macrope` coercion function:

    const = function(value)
       return setmetatable({value=value}, constmeta)
    end

Finally, the main entry point to the module does this type-testing
DWIM magic:

    macrope = function(thing)
       if type(thing) == 'number' then thing = tostring(thing) end
       if type(thing) == 'string' then return const(thing) end
       if thing.is_macrope then return thing end
       -- XXX maybe try to invoke tostring on it?
       error("not a macrope or string: " .. thing)
    end

And the module exports:

    return { macrope = macrope, var = var }

How worst-case ropes arise
--------------------------

One worst case is building up an extremely imbalanced tree of single
bytes:

    macrope = require 'macrope'
    N = 100000
    s = macrope.macrope ''
    for i = 1, N do s = s .. 'x' end
    s = tostring(s)

As I said above, this takes 250 milliseconds, working out to 400
kilobytes per second.  Although at this scale this is 12 times faster
than the O(*N*²) native-Lua implementation, it’s still ridiculously
slow, and three times slower than when I wasn’t using an explicit
stack.  For perspective, this takes about the same time, with 1000
times as many iterations:

    macrope = require 'macrope'
    function doit(N)
        s = 0
        for i = 1, N do s = s + i end
        s = tostring(s)
        return s
    end
    =doit(100*1000*1000)

Building the same string this way instead gets a further 5× speedup:

    macrope = require 'macrope'
    N = 10000
    s = macrope.macrope ''
    for i = 1, N do s = s .. 'xxxxxxxxxx' end
    s = tostring(s)

Most of this speedup is in the explicit loop there, which took two
thirds of the time before and now runs one tenth as many iterations.

This is the linear-search worst case that forced me to use an explicit
stack in the `__tostring` function to avoid stack overflows, at the
cost of a 2.5× slowdown in the `tostring` call.  If you did some kind
of tree balancing during the construction of the graph, it probably
wouldn’t speed it up (doing more work on each iteration would probably
slow it down instead, even if the working set shrank) but it could
speed the final tree traversal substantially.

A different kind of worst case is the other example above:

    macrope = require 'macrope'
    x = macrope.macrope 'x'
    for i = 1, 25 do x = x .. x end
    tostring(x)

This doesn’t take long to construct, because there are only 26 nodes
in the DAG, but in the `tostring` call the single leafnode is visited
33 million times; that’s why it takes 30–40 seconds.  Constructing the
same string as follows instead takes 1.3 seconds, about 30 times
faster:

    macrope = require 'macrope'
    x = macrope.macrope 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
    for i = 1, 20 do x = x .. x end
    #tostring(x)

So it wouldn’t take a lot of tree optimization to speed things up by
quite a lot in this case.

Leafnode coalescence, and when it isn’t enough
----------------------------------------------

The simplest measure would be to have a special case for concatenating
short const leafnodes: if the total length of the result is under some
threshold, somewhere in the range of 16–128 bytes, it’s better to just
copy all the bytes into a new const node instead of making a
concatenation node.  This would help a lot with the million-laughs DAG
above but would only slightly worsen the problem of successive
concatenation at the end.

You could be a little more sophisticated and get a linear improvement
by having your concatenation operator coalesce with non-root
leafnodes, something that’s dramatically easier to expressin a
language with pattern-matching (here `^` is OCaml’s string
concatenation operator):

    let cat2 a b = match (a, b) with 
    | (Leaf(n1, s1), Leaf(n2, s2)) when n1+n2 < 128 ->
        leaf(s1 ^ s2)
    | (Cat(_, x, Leaf(n1, s1)), Leaf(n2, s2)) when n1+n2 < 128 ->
        cat x (leaf(s1 ^ s2))
    | (Leaf(n1, s1), Cat(_, Leaf(n2, s2), x)) when n1+n2 < 128 ->
        cat (leaf(s1 ^ s2)) x
    | (_, _) ->
        cat a b

This successfully reduces the tree depth by a linear factor — 128 in
this case — in the simple scenarios considered above.  It might speed
up or slow down the tree construction, though if it does slow it down,
that’s probably just because 128 is a bit too big.  However, it
doesn’t help in all cases — consider the case of alternately adding to
the beginning and the end of the string:

    cat2 (cat2 (leaf "x") (cat2 (cat2 (leaf "x")
                                 (leaf (String.make 128 'h')))
                           (leaf "x")))
         (leaf "x")

The initial `String.make 128 'h'` produces a large leafnode, and the
following operations of appending or prepending a single character are
then blocked from coalescing.

Evidently it would be useful to have a tree structure with rigorous
guarantees on worst-case behavior.

B-tree ropes
------------

B-trees are great for worst-case performance.  The tree has a uniform
depth on every path from the root to the branches, and the high
branching factor minimizes the number of internal nodes on which we
must waste storage space and the amount of memory needed for tree
traversal.  And, at least in principle, they’re simpler than other
popular self-balancing trees such as red-black trees, AVL trees, and
treaps.  (They also tend to be much faster, especially on modern deep
memory hierarchies.)

But can we use B-trees for ropes like the above?  I
[started an OCaml implementation in 2015 and never finished it][1] but
I think that in principle it’s straightforward.  To concatenate, you
may need to add tree levels to the smaller rope, and then you can
merge (by concatenating) newly-adjacent nodes moving down from the
root until you encounter a place where merging would make the new node
too big; then you stop.

[1]: http://canonical.org/~kragen/dev3/brope.ml

I still need to read Okasaki’s masterwork and the follow-on work in
the decades since, but there’s a trap in amortized analysis of
FP-persistent data structures — typically, amortized complexity
analysis assumes that once you’ve done some big messy reorganization,
like rehashing a hash table into a larger array of buckets, you can be
sure that you won’t need to do it again anytime soon.  But with
FP-persistent data structures (like ropes!) the state of the data
structure immediately prior to the reorganization may still be
accessible, and so it may be possible to provoke the reorganization
over and over again by deriving new states from it.

This suggests that to get good amortized performance from
FP-persistent data structures, either you need mutability behind the
curtain or you need good *worst-case* performance per update
operation.  This is a connection I hadn’t previously suspected between
the world of FP-persistent algorithms and the world of bounded-time
algorithms, which are usually on opposite ends of the universe.

B-trees in particular are relatively friendly to this.  Suppose you
decide on nodes of about 128 bytes: 64–256 bytes of text for
leafnodes, 8–32 pointers for internal nodes†.  The worst-case B-tree
for a 4-gibibyte rope is 2²⁶ = 67108864 leaf nodes, which is at worst
9 levels of internal nodes.  So, to concatenate it with another such
rope, at worst you’d have to merge together 9 pairs of nodes, about
2 KiB of memory traffic.  This is definitely worse than the 32 bytes
or so of memory traffic used by `cat` or `__concat` above, by about a
factor of 64, but it’s also fairly closely bounded.  Note that with a
minimal branching factor of 8, the internal nodes are guaranteed to
use no more than ⅐ of the leafnode memory.

For smaller strings the cost is smaller — with those parameters,
everything up to 512 bytes is guaranteed to fit into a single level of
B-tree.

For perspective, this suggests that the process of inserting a
character (or arbitrary string) into the middle of an FP-persistent
4-gibibyte rope will require on the order of a microsecond and ten
kilobytes of allocation:

- 18 new nodes, totaling 4 kilobytes in cache to break the tree into
  two slices at the insertion point;
- 9 new nodes, totaling 2 kilobytes in cache, to create the tree for
  the new byte;
- 9 new nodes, totaling 2 kilobytes in cache, to concatenate the new
  byte to the left tree fragment;
- 9 new nodes, totaling 2 kilobytes in cache, to concatenate the right
  tree fragment onto that.

Filling up these 10 newly allocated kilobytes of memory is going to
take a few thousand instructions, which takes about a microsecond on
modern CPUs.  You could probably reduce this cost in the average case
with a simplified “buffer gap” approach in which you maintain separate
left and right trees, so that you normally only pay the cost of
creating the new byte’s tree and concatenating it onto the left tree.

I feel like there may still be aspects of B-tree rebalancing I’m not
appreciating, even without slicing.

† CLRS claims that allowing nodes to be less than ½ full, as in the
factor of ¼ in this example configuration, makes it no longer really a
B-tree, and if we don’t allow nodes to be less than ⅔ full it becomes
a “B\*-tree”.  However, CLRS gets terminology wrong pretty often, so
this might not be right.  My rationale for the extra factor of 2
slack, which probably doesn't really apply in an FP-persistent context
(at least not without more work), is to prevent pathological
modification sequences from thrashing between splitting and joining
the same node.