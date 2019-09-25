A homoiconic language with a finite-map-based data model rather than lists
==========================================================================

I wrote [a mock Lisp the other night][0], which was a surprisingly
pleasant experience.  Thanks to LuaJIT, it took me only a couple of
hours to get from nothing to generating reasonably fast native
code — wasting only 70% of the CPU’s performance rather than 80% as
with [Ur-Scheme][1] or 95% as with CPython.  The mock Lisp isn’t
powerful enough for a metacircular interpreter, since it lacks data
structures, but it’s powerful enough to write a recursive Fibonacci
number function.

[0]: http://canonical.org/~kragen/sw/dev3/terp.lua
[1]: http://canonical.org/~kragen/sw/urscheme

This led me to wonder whether an imperative homoiconic programming
language based on maps rather than lists could be a better alternative
to Lisp.

The magic of READ and PRINT
---------------------------

Although LuaJIT is amazing, the experience of debugging things at the
LuaJIT REPL made me wish for Python, JS, OCaml, or Lisp — languages
where your data structures can be automatically serialized in a
parseable form, a very handy feature not only for interactive testing
but also for network communication, ad-hoc filesystem persistence,
manual fixup of broken systems, and primitive user interfaces.  Here’s
a rehearsed interaction with the OCaml interpreter:

    $ ocaml
            OCaml version 4.02.3

    # type rope = Leaf of int * string | Cat of int * rope * rope ;;
    type rope = Leaf of int * string | Cat of int * rope * rope
    # let rope_length = function Leaf(a, _) -> a | Cat(a, _, _) -> a ;;
    val rope_length : rope -> int = <fun>
    #   let leaf s = Leaf(String.length s, s)
        let cat a b = Cat(rope_length a + rope_length b, a, b)
        let cat2 a b = match (a, b) with 
        | (Leaf(n1, s1), Leaf(n2, s2)) when n1+n2 < 128 ->
            leaf(s1 ^ s2)
        | (Cat(_, x, Leaf(n1, s1)), Leaf(n2, s2)) when n1+n2 < 128 ->
            cat x (leaf(s1 ^ s2))
        | (Leaf(n1, s1), Cat(_, Leaf(n2, s2), x)) when n1+n2 < 128 ->
            cat (leaf(s1 ^ s2)) x
        | (_, _) ->
            cat a b
    ;;

    val leaf : string -> rope = <fun>
    val cat : rope -> rope -> rope = <fun>
    val cat2 : rope -> rope -> rope = <fun>
    # cat2 (cat2 (leaf "x") (cat2 (cat2 (leaf "x")
                                     (leaf (String.make 128 'h')))
                           (leaf "x")))
         (leaf "x")
    ;;
    - : rope =
    Cat (132,
     Cat (131, Leaf (1, "x"),
      Cat (130,
       Cat (129, Leaf (1, "x"),
        Leaf (128,
         "hhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh")),
       Leaf (1, "x"))),
     Leaf (1, "x"))
    # 

(This experimentally confirms that the leafnode-coalescence strategy
used by `cat2`, proposed in file `btree-ropes.md`, does indeed
experience pathological fragmentation for some workloads.)

Here’s JS, though you can’t see the pleasant syntax highlighting Node
applied to its output:

    $ node
    > x = {a: [3, 4], b: 5}
    { a: [ 3, 4 ], b: 5 }
    > x.b += 4
    9
    > x.c = ['okay']
    [ 'okay' ]
    > x.c.push('now')
    2
    > x
    { a: [ 3, 4 ], b: 9, c: [ 'okay', 'now' ] }
    >

Here’s the same interaction in Python, which is quite a bit fussier
than JS, but still comes through:

    >>> x = {"a": [3, 4], "b": 5}
    >>> x["b"] += 4
    >>> x["c"] = ['okay']
    >>> x["c"].append('now')
    >>> x
    {'c': ['okay', 'now'], 'a': [3, 4], 'b': 9}

### Lua has READ but not PRINT ###

Now contrast Lua, which is eminently capable of handling the same kind
of flexible data structures, but doesn’t come with any way to print
them:

    $ luajit
    LuaJIT 2.0.4 -- Copyright (C) 2005-2015 Mike Pall. http://luajit.org/
    JIT: ON CMOV SSE2 SSE3 SSE4.1 fold cse dce fwd dse narrow loop abc sink fuse
    > x = {a = {3, 4}, b = 5}
    > x.b = x.b + 4
    > x.c = {'okay'}
    > table.insert(x.c, 'now')
    > =x
    table: 0x40542160
    > =x.a
    table: 0x405485a8
    > =x.a[1]
    3
    > =x.a[2]
    4
    > =x.b
    9
    > =#x.a
    2
    > =#x.c
    2
    > =x.c[1]
    okay
    > =x.c[2]
    now
    > =table.unpack(x)
    stdin:1: attempt to call field 'unpack' (a nil value)
    stack traceback:
            stdin:1: in main chunk
            [C]: at 0x004044a0

I guess `table.unpack` wasn’t added until Lua 5.2, and LuaJIT is a Lua
5.1.  Doesn’t matter, because it wouldn’t have helped
anyway — `table.unpack` is only for lists, not for dictionaries.
There’s a `pairs` function in core Lua for iterating over
dictionaries, but just printing it isn’t useful; it returns an
iteration state, not an unpacked sequence:

    > =pairs(x)
    function: builtin#4     table: 0x4163d160       nil

You actually have to write code to iterate over the pairs:

    > for k, v in pairs(x) do print(k, v) end
    b       9
    a       table: 0x405485a8
    c       table: 0x40548920

And of course it doesn’t recurse; you have to do that yourself:

    > for k, v in pairs(x.a) do print(k, v) end
    1       3
    2       4
    > for k, v in pairs(x.c) do print(k, v) end
    1       okay
    2       now
    > 

S-expressions and their discontents
-----------------------------------

Lisp S-expressions are probably a sort of minimum-complexity way to
give you fully general data structures that are readable and
printable, with a syntax you can write in a single-rule BNF grammar:

    sexp ::= [ \n]* "(" sexp* [ \n]* ")" | [ \n]* [-A-Za-z0-9*]+

And once you implement that, which is flexible enough to use for any
kind of tree data structure, it’s straightforward to use them for your
source code as well as your data structures, although many people
complain about the clarity of the resulting code.  Here’s the
recursive-descent parser I hacked together in half an hour (plus a
couple of cleanups), using Lua’s built-in list structure and
`string.match`, although I probably should have used LPEG:

    function read_sexp(c, getc)
       while c:match("[%s]") do c = getc() end
       if c == '(' then return read_list(getc(), getc) end
       return read_atom(c, getc)
    end

    function read_list(c, getc)
       while c ~= nil and c:match("[%s]") do c = getc() end
       if c == ')' then return nil end

       local car, c2 = read_sexp(c, getc)
       if c2 == nil then c2 = getc() end

       return {car=car, cdr=read_list(c2, getc)}
    end

    function read_atom(c, getc)
       local name = {}

       while c ~= nil and c:match("[^%s()]") do
          table.insert(name, c)
          c = getc()
       end

       name = table.concat(name)
       if not name:match("[^%d.]") then return tonumber(name), c end
       return name, c
    end

With this, the compiler can successfully parse and compile programs
such as the following:

    (letrec (fib (lambda (n)
                   (if (< n 2)
                       1
                       (+ (fib (- n 1)) (fib (- n 2))))))
      (fib 40))

S-expressions have some real merits.  They have great simplicity of
implementation, and they’re relatively light on delimiters, which
makes them easy t type; compare JS’s `{ a: [ 3, 4 ], b: 9, c: [
'okay', 'now' ] }` or Python’s `{'c': ['okay', 'now'], 'a': [3, 4],
'b': 9}` to `(a (3 4) b 9 c (okay now))` or even `((a (3 4)) (b 9) (c
(okay now)))`.

### The discontents ###

However, S-expressions also have some real drawbacks.

As you can see in the string `))))))` in the above mock Lisp program,
they expose the deeply nested nature of the data structure rather
crudely; this is often unhelpful to the humans.  Tim Peters’s line in
the Zen of Python, “Flat is better than nested”, is a response to
this.  Although the humans are capable of recursive thought, it is a
lot of effort for them, so they do much better when they can stick to
finite state machines and Markov chains.

Code that stores data as S-expressions can be somewhat inscrutable and
therefore bug-prone; consider this Elisp snippet from files.el:

	      (if (and mode
		       (consp mode)
		       (cadr mode))
		  (setq mode (car mode)
			name (substring name 0 (match-beginning 0)))
		(setq name nil))

What are `(car mode)` and `(cadr mode)` (that is, the second item of
the list `mode`)?  They’re some kind of fields of a data structure,
but it’s hard to tell what they intend.  Fairly often Elisp will
unpack such lists at the entry to a function or the top of a loop,
which inflates the code a bit (this from Ken Manheimer’s allout.el
outliner mode):

      (while pairs
        (let* ((pair (pop pairs))
               (name (car pair))
               (value (cadr pair))
               (qualifier (if (> (length pair) 2)
                              (caddr pair)))
               prior-value)
        ...

A perhaps more subtle problem of S-expressions is their extensibility.
The last example above handles tuples of the structure `(name value)`,
which may be extended with an optional `qualifier` to become `(name
value qualifier)`.  Perhaps at some future point a `scope` or `mode`
will be added.

As with Protocol Buffers, it’s safe to add new items at the end of
such tuple-shaped lists — but only if nobody else is doing so
concurrently somewhere else, or you’ll end up misinterpreting each
other’s data.  That is, if I add a `scope` item as the fourth item,
and you add a `mode`, and for whatever reason I end up running my code
on your data (from your .emacs.d/init.el, perhaps), something will go
wrong.

(An example of this is how Racket doesn’t really parse your program
into cons nodes; instead it parses it into things that are similar to
cons nodes but also contain file, line number, and column number
information, so that it can report runtime errors in context.  Adding
such a feature using normal cons nodes in a way that wouldn’t break
existing users would be infeasible.)

Lists being used as lists are much worse, though — there’s no way to
add any extra data to them (other than per list item) without breaking
backward compatibility.

Finally, S-expressions use a buttload of memory, especially on 64-bit
machines: at least two pointers per list item, plus potentially extra
space for type tags, garbage collection tags, locks, and so on.

These aren’t really drawbacks of Lisp, except for `))))))`; Common
Lisp, Scheme, Racket, Clojure, and even Elisp have a variety of other
data structures and aren’t limited to cons chains.  It’s a drawback of
just storing data in cons chains.

Problems like these are why awk, Python, JS, and Lua privilege finite
maps (also known as dictionaries, tables, associative arrays, or
hashes) over lists or arrays, and OCaml is instead based on
discriminated unions (although it has lists and tuples).  Finite maps,
sets of name-value pairs, have a sterling record of
backward-compatibility in things like email headers, HTML element
attributes, and library APIs.

However, none of these non-Lisp languages has attempted to use the
same syntax for code and for data.  I think it might be a fun thing to
try.

Nested dicts
------------

The simplest approach to a homoiconic language syntax consisting of
finite maps is to just use S-expressions with an even number of items,
and interpret them as finite maps.  Clojure does something like this:

    user=> {:a [3 4] :b 5}
    {:b 5, :a [3 4]}

(The leading `:` in Clojure marks a keyword, which is autoquoted in
much the same way as in Common Lisp or Ruby.)

The grammar for such a dictionary-expression approach is very nearly
as simple as that for ordinary S-expressions:

    dexp ::= [ \n]* "{" (dexp dexp)* [ \n]* "}" | [ \n]* [-A-Za-z0-9*]+

It remains to be seen how to encode programs in this form in a usable
fashion.  First, though, some exploration of a subtle point that can
produce a lot of confusion.

### Reading, evaluation, and auto-quoting ###

There’s a subtle distinction which is glossed over above.  Python
reads “dictionary displays” like `{3: 4}` differently from the way
Lisp parses S-expressions.  Python, like Lua, JS, Ruby, and OCaml, is
*evaluating* these expressions, with potentially Turing-complete
consequences.  Lisp’s READ, by contrast, just *parses* them, though if
you type them in at the REPL prompt it will evaluate them, and they
may evaluate to themselves.  Here’s an edited interaction with the
SBCL implementation of Common Lisp:

    * (read)
    (x y z)
    (X Y Z)
    * 

That is, I typed `(read)` at the prompt, and then it waited for
another S-expression of input; I typed `(x y z)`, and it responded by
parsing that and returning a list of those three symbols, which
unfortunately it prefers to print in uppercase, as if it were still
1962.  By contrast, if I type `(x y z)` at the prompt, first it parses
(“reads”) that into the same list as before, and then attempts to
evaluate it, which fails because I haven’t defined the variable `y`:

    * (x y z)
    ; in: X Y
    ;     (X Y Z)

...(many lines omitted)...

    debugger invoked on a UNBOUND-VARIABLE in thread
    #<THREAD "main thread" RUNNING {100399C553}>:
      The variable Y is unbound.

If you actually want that list of three symbols, you can use `quote`,
optionally abbreviated as `'`, both for input and for output:

    * (quote (x y z))
    (X Y Z)
    * (list (quote x) (quote y) (quote z))
    (X Y Z)
    * '(x y z)
    (X Y Z)
    * (list 'x 'y 'z)
    (X Y Z)
    * '(quote (x y z))
    '(X Y Z)

It happens that, in Common Lisp and in Elisp, evaluation of lists does
things such as call functions and apply macros, but evaluation of
other data such as integers or strings just returns that data (it is
“auto-quoting”).  In fact, this rule even extends to things like
“vectors”, which is to say, arrays:

    * (defvar x 99)
    X
    * #(3 x 9)
    #(3 X 9)

We got the symbol `X` rather than the value 99.  What happened is that
the whole vector `#(3 X 9)` was read, and vectors are auto-quoting, so
evaluating it simply returned the vector.  If we want to build up a
vector from values computed at run-time, we have to call the function
`vector`:

    * (vector 3 x 9)
    #(3 99 9)

Smalltalk originally had the same problem, although Squeak has a fix.
Clojure, on the other hand, follows Common Lisp by separating reading
from evaluation, but follows Python by evaluating items inside of
aggregate data structures unless they are explicitly quoted; like
Elisp, JS, and Python, but unlike Common Lisp and Lua, it uses `[]` to
delimit vectors/arrays:

    $ clojure
    Clojure 1.6.0
    user=> (def x 99)
    #'user/x
    user=> [3 x 9]
    [3 99 9]
    user=> '[3 x 9]
    [3 x 9]
    user=> {x 3 (+ x 1) 4}
    {99 3, 100 4}
    user=> '{x 3 (+ x 1) 4}
    {x 3, (+ x 1) 4}
    user=> (type [3 x 9])
    clojure.lang.PersistentVector
    user=> (type '[3 x 9])
    clojure.lang.PersistentVector
    user=> ({x 3 (+ x 1) 4} x)
    3
    user=> ({x 3 (+ x 1) 4} 'x)
    nil
    user=> ('{x 3 (+ x 1) 4} 'x)
    3
    user=> (read)
    [3 x 9]
    [3 x 9]

In Clojure, only primitive atomic data types like numbers, strings,
and keywords are auto-quoting.  But it happens that, if the only
things in your map or vector are auto-quoting, it evaluates to itself:

    user=> {:x 3 :y 4}
    {:y 4, :x 3}

(The comma is optional.)

This can be confusing because it obscures the fact that an evaluation
is happening, as in Python, unlike in Common Lisp.  Python is fussy
enough to remind you of this if you forget, requiring a lot of extra
line-noise punctuation in your literal “dictionary displays”:

    >>> x = {a: [3, 4], b: 5}
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
    NameError: name 'a' is not defined
    >>> x = {"a": [3, 4], "b": 5}
    >>> x
    {'a': [3, 4], 'b': 5}

JS and Lua, on the other hand, have special cases in their syntax so
that you can forget most of the time:

    > x = {a: [3, 4], b: 5}
    { a: [ 3, 4 ], b: 5 }

Lua:

    > x = {a = {3, 4}, b = 5}

If you really want to force the evaluation of an expression for a key
consisting of just a variable, there is special syntax for this in
Lua:

    > a = 5
    > x = {[a] = 8}
    > =x[5]
    8
    > =x.a
    nil

And in JS:

    > a = 8
    8
    > x = {a: 4}
    { a: 4 }
    > x = {[a]: 4}
    { '8': 4 }

### Encoding fundamental imperative-language constructs ###

An imperative programming language contains at least sequence,
assignment, and looping; a normal programming language also contains
identifiers, subroutine definitions, subroutine invocations,
conditionals, and primitive operations.  How can you encode these
usably in a tree of maps?

I mean, obviously you can write an abstract syntax tree of the form

    {nodetype binop operator +
     left {nodetype identifier name x}
     right {nodetype constant value 1}}

but this results in a very poor signal to noise ratio.  Even if you
don’t use maps to represent the leafnodes, it’s pretty bad:

    {nodetype binop operator + left x right 1}

But can we do better?

Consider the example mock Lisp program I mentioned earlier:

    (letrec (fib (lambda (n)
                   (if (< n 2)
                       1
                       (+ (fib (- n 1)) (fib (- n 2))))))
      (fib 40))

#### Built-in operation invocations ####

A Smalltalk-like approach, treating things like addition like method
calls, could reduce the noise factor somewhat:

    {: x + 1}

We could treat function invocation in a similar way, providing named
arguments.  With this approach the Lisp expression

    (+ (fib (- n 1)) (fib (- n 2)))

becomes

    {: {: fib n {: n - 1}} + {: fib n {: n - 2}}}

which seems, if not ideal, at least potentially tolerable.

Because the sequence of name-value pairs is undefined, though, this
could just as well be rendered as follows:

    {+ {n {- 2 : n} : fib} : {n {- 1 : n} : fib}}

which seems pretty confusing; the interpreter is going to be looking
for the `:` to see if the node is such a method-invocation node, and
not having it first makes it harder to determine what is going to
happen.

#### Conditionals ####

Lisp-style `cond` is not easy to obtain, but an if-then-else node is
easy:

    {if {: n < 2}
     then 1
     else {: {: fib n {: n - 1}} + {: fib n {: n - 2}}}}

#### Assignments ####

Lisp-like `let` or `letrec` fits very nicely into this sort of scheme;
consider this Elisp (also from allout.el):

    (let ((start (point))
          (ol-start (overlay-start ol))
          (ol-end (overlay-end ol))
          first)
      body)
      
This translates to

    {let {start {: point}
          ol-start {: overlay-start overlay ol}
          ol-end {: overlay-end overlay ol}
          first nil}
     in body}

Imperative side-effecting assignments like this one (also from
allout.el) demand a different approach:

          (when (not first)
            (setq first (point)))

I mean there are lots of ways you could spell that:

    {set first to {: point}}
    {let first = {: point}}
    {my first is {: point}}
    {make first be {: point}}

However, I favor these, because they comfortably support parallel
assignments (like the many-argument `setq` in one of the examples
above) and have less noise words:

    {= {first {: point}}}
    {set! {first {: point}}}

#### Subroutine definitions ####

Darius Bacon has been working on a new dialect of Scheme called
“[Cant][1]”, previously “Squeam”, in which the fundamental
procedure-call mechanism uses a pattern-matching mechanism on the
argument list to select a method to invoke on the receiver object.
That is, you don’t have procedures as such, just receivers.  This
provides a very nice unification of ML-style pattern matching and
Smalltalk-style object orientation.

[1]: https://github.com/darius/cant/

You could do something similar here, defining functions as sets of
argument-list/body pairs.  To guarantee determinism the compiler would
have to verify that the argument lists were mutually exclusive.

This allows us to translate the Lisp above:

    (letrec (fib (lambda (n)
                   (if (< n 2)
                       1
                       (+ (fib (- n 1)) (fib (- n 2))))))
      (fib 40))

as

    {let {fib {lambda {{n {}}
                       {if {: n < 2}
                        then 1
                        else {: {: fib n {: n - 1}}
                              + {: fib n {: n - 2}}}}}}}
     in {: fib n 40}}

which in this case contains only a single argument list, containing
`n`.  It’s not clear what kind of values to associate with the
arguments; maybe `{n {default 2}}` would be a valid specification.

#### Looping ####

The Common Lisp LOOP macro provides a good example of how you can
usefully specify a loop as a set of name-value pairs: `{while foo do
bar}` and `{for i = 1 to 10 do bar}` are simple examples, but it is
reasonable to support also `{for x in mylist collect {: f n x} when {:
x > 2}}` and the like.

#### Sequencing ####

I’ve saved the worst for last.  In the language as described above the
only obvious way to sequence is by nesting; things that aren’t nested
have no sequence.  You could potentially use line numbers:

    {prog {10 {print "HOWIE IS AWESOME"}
           20 {goto 10}}}

but failing that you are stuck with constructs of the form `{do x then
y}`, which you must nest to get sequences of an arbitrary number of
steps.

Flat dict syntax
----------------

So, what if we use infix syntax to build our dicts instead of
circumfix syntax?  I think I’ve written a bit about this before; the
idea is that you use parentheses merely for grouping, and you have two
operators `:` and `,` which you can use to build up an arbitrary dict.
`x: y` is a single-entry dict in which the key `x` has the value `y`,
and `a, b`, with lower operator precedence, is the union of the dicts
`a` and `b`, with some kind of rule about key conflicts (either it’s
an error or there’s a defined winner).

We need to change the name of the invocation-target tag `:` to
something else, ideally something inoffensive; `.` is a reasonable
candidate.

So our translation above

    {let {fib {lambda {{n {}}
                       {if {: n < 2}
                        then 1
                        else {: {: fib n {: n - 1}}
                              + {: fib n {: n - 2}}}}}}}
     in {: fib n 40}}

could be spelled

    let: (fib: (lambda: ((n: ()):
                         (if: (.: n, <: 2),
                          then: 1,
                          else: (.: (.: fib, n: (.: n, -: 1)),
                                 +: (.: fib, n: (.: n, -: 2))))))),
    in: (.: fib, n: 40)

I think I’ve made it even worse, if that’s possible!  If we decree
that `:` associates to the right, so `x: y: z` means `x: (y: z)`, we
can remove all of the parentheses that neither contain a comma nor
precede a colon:

    let: fib: lambda: ((n: ()):
                       (if: (.: n, <: 2),
                        then: 1,
                        else: (.: (.: fib, n: (.: n, -: 1)),
                               +: (.: fib, n: (.: n, -: 2))))),
    in: (.: fib, n: 40)

So far, so abysmal.  But consider the above example:

    {set! {first {: point}}}

Now we can write this example as

    set!: first: .: point

This gives us a potential way to write semantically nested execution
sequences as syntactically flat ones, but at the cost of putting our
statements in the “name” field of name-value pairs, which means that
there’s no way to attach other data to these nodes in an unambiguous
way.  (This is something that is already true of, for example,
argument lists.)

Consider this snippet of code from [this bit of C++ 3-D ASCII-art
animation][3]:

      // Rotate by theta.
      nx = c*xs[i] + s*zs[i];
      zs[i] = -s * xs[i] + c*zs[i];
      xs[i] = nx;

It’s necessary to either do the three statements in the order in which
they’re written or to do parallel assignment.  For a moment let’s
disregard the much better option of parallel assignment and pretend
it’s a case where we have to write a sequence.  Which of the following
horrors is the less bad translation?

    {do {= {nx {. {. c * {. xs at i}} + {. s * {. zs at i}}}}}
     then {do {. zs at i put {. {. {- s} * {. xs at i}}
                              + {. c * {. zs at i}}}}
           then {. xs at i put nx}}}

    do: (=: nx: (.: (.: c, *: (.: xs, at: i)), +: (.: s, *: (.: zs, at: i)))):
        (.: zs, at: i, put: (.: (.: -: s, *: (.: xs, at: i)),
                             +: (.: c, *: (.: zs, at: i)))):
        (.: xs, at: i, put: nx)

Well, they’re both pretty fucking bad compared to the FORTRAN-style
code above, but I think the second one is worse.

[3]: http://canonical.org/~kragen/sw/dev3/rotcube.cpp

Edge-labeled graphs
-------------------

Years ago I saw a project on SourceForge that treated text as an
edge-labeled graph (similar to Suciu’s UnQL unstructured query
language) delimited by whitespace and structured by indentation, and
provided tools to query it and to reformat a number of Unix commands
to make them more amenable to processing with it.  (Unfortunately, I
forget the name, and I haven't been able to find it again.)  So, for
example, given this input:

    time    real    0m1.694s
            user    0m1.524s
            sys     0m0.168s

it would decide that from the start node there was an arc labeled
“time”, and from the node it led to three more arcs labeled “real”,
“user”, and “sys”, each of which led to a node with one further arc
labeled with a string such as “0m1.524s”.  This of course means that
you can easily query `time.user` and get that response.

(In a tree, it’s immaterial whether the labels are on the arcs or on
the nodes they lead to, but in a more general graph it can matter.)

Note how this generalizes a subset of the finite-map-tree model: the
names are just strings, as in JS and Perl, rather than general
objects, as in Python, Lua, and Clojure, but there’s no distinction
between keys and values — the values are just the labels after the
level where your query stopped traversing edges.  Also, the keys need
not be unique.  (They may or may not be sequenced; those are different
variants of the model.)

Suppose we try to use this approach for our homoiconic language,
although using parentheses rather than indentation to indicate side
branches — the above graph comes out as `time (real 0m1.694s) (user
0m1.524s) sys 0m0.168s`.  In a sense, this is just the Lisp cons
rotated 90°: nesting is the default and parentheses turn it off!  But
let’s say that the sequence of branches is not important, so it’s
equivalent to say `time (user 0m1.524s) (sys 0m0.168s) real 0m1.694s`.

Now we could use sequencing not only for imperative statement
sequences but also for argument lists.  And the label leading us into
an expression node can be the variant tag that tells the interpreter
unambiguously how to handle that expression — or, as in Common Lisp,
either an identifier of a special form or the name of a function.
This suggests that, as in Forth, variables are just zero-argument
functions, but in this case — unlike in Forth — they can look to see
if they’re being invoked with arguments, such as maybe `=`.  (And you
can of course have a FUNCALL function as in Common Lisp or a `value`
message as in Smalltalk, so if you store a function pointer in a
variable, you can still invoke it.)

The fundamental benefit of property-list-like systems is that you can
always attach new “properties” to some well-defined set of nodes
without bothering the things that are already using those nodes,
because they only look at the properties they care about.  In this
system this is somewhat vitiated by the fact that since property
values are just arc labels, just like property names, there are
inevitably a lot of nodes where this benefit does not obtain — any new
property you attach at those nodes might be mistaken for the property
value!

Still, it’s an interesting idea to explore.  I’m not sure what the
code would look like yet.