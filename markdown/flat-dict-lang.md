A homoiconic language with a finite-map-based data model rather than lists?
===========================================================================

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
to Lisp.  I think it’ll necessarily have more redundancy than Lisp,
since a map with *N* keys has *N*! equivalent permutations (so the
parsing process discards lg (*N*!) bits), but that may not be a bad
thing; after all, we can diminish redundancy further by dropping to
Forth, PostScript, or APL.

After examining some clumsy alternatives, I think I have a reasonable
alternative based on a forgotten SourceForge project for text munging.

The magic of READ and PRINT
---------------------------

Although LuaJIT is amazing, the experience of debugging things at the
LuaJIT REPL made me wish for Python, JS, OCaml, or Lisp — languages
where your data structures can be automatically serialized in a
parseable form, a very handy feature not only for interactive testing
but also for network communication, ad-hoc filesystem persistence,
manual fixup of broken systems, primitive user interfaces, and
shared-nothing message-passing parallel and concurrent processing,
as with fork().  Here’s
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
“[Cant][2]”, previously “Squeam”, in which the fundamental
procedure-call mechanism uses a pattern-matching mechanism on the
argument list to select a method to invoke on the receiver object.
That is, you don’t have procedures as such, just receivers.  This
provides a very nice unification of ML-style pattern matching and
Smalltalk-style object orientation.

[2]: https://github.com/darius/cant/

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

or

    do: (=: nx: (.: (.: c, *: (.: xs, at: i)), +: (.: s, *: (.: zs, at: i)))):
        (.: zs, at: i, put: (.: (.: -: s, *: (.: xs, at: i)),
                             +: (.: c, *: (.: zs, at: i)))):
        (.: xs, at: i, put: nx)

Well, they’re both pretty fucking bad compared to the FORTRAN-style
code above, but I think the second one is worse.

[3]: http://canonical.org/~kragen/sw/dev3/rotcube.cpp

Edge-labeled graphs: now is the winter of our discontent made glorious summer
-----------------------------------------------------------------------------

Years ago I saw a project on SourceForge that treated text as an
edge-labeled graph (similar to Suciu’s UnQL unstructured query
language) delimited by whitespace and structured by indentation, and
provided tools to query it and to reformat a number of Unix commands
to make them more amenable to processing with it.  (Unfortunately, I
forget the name, and I haven’t been able to find it again.)  So, for
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
the nodes they lead to, but in a more general graph it can matter.  It
might make more sense to think of all of the following as having tags
on nodes rather than edges.)

Note how this generalizes a subset of the finite-map-tree model: the
names are just strings, as in JS and Perl, rather than general
objects, as in Python, Lua, and Clojure, but there’s no distinction
between keys and values — the values are just the labels after the
level where your query stopped traversing edges.  Also, the keys need
not be unique.  (They may or may not be sequenced; those are different
variants of the data model.)

Suppose we try to use this approach for our homoiconic language,
although using parentheses rather than indentation to indicate side
branches — the above graph comes out as `time (real 0m1.694s) (user
0m1.524s) sys 0m0.168s`.

The grammar here is something like

    tree ::= [ \n]* ("(" tree [ \n]* ")" | [-A-Za-z0-9*]+) tree | ε

Here the three alternatives amount to three different ways to grow a
tree: by branching it, by extending a branch by a segment, and by
terminating a branch.  This apparently has one more alternative than
the original `sexp` grammar given above, but this is an illusion; the
`sexp` grammar contained `sexp*`, which hides an alternative in its
Kleene closure.

### A homoiconic language using edge-labeled graphs? ###

In a sense, this is similar to the Lisp cons
rotated 90°: nesting (car) is the default and parentheses turn it off!  But
let’s say that the sequence of branches is not important, so the above example is
equivalent to say `time (user 0m1.524s) (sys 0m0.168s) real 0m1.694s`.

#### Sequencing is now easy, but what do expressions look like? ####

With this approach, we could use sequencing not only for imperative statement
sequences but also for argument lists.  A sequence of statements might
look like `(some action) ; (some other action) ; a third action`, with
`;` edges connecting the sequence of statement nodes.

And the problem we previously had with difficulty
determining what operation to invoke is gone — the label leading us into
an expression node can be the variant tag that tells the interpreter
unambiguously how to handle that expression — or, as in Common Lisp,
either an identifier of a special form or the name of a function.
This suggests that, as in Forth,
variables (and perhaps constants) are just zero-argument
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

#### Function calls are kind of hairy ####

Unary operations and commutative, associative operations like `+`
might conceivably just attach their arguments directly to their node:
`+ (x) (y) * (a) b`, for example, for *x* + *y* + *a* × *b*.  But more
general function calls might require named arguments `fib (n 10)` or
an argument sequence analogous to statement sequences `cat2 (leaf "x")
, leaf "y"`.  Also, if duplicate edges are not allowed, `* (x) x`
would be a problem.

#### What if math operators are messages sent to numbers? ####

As before, a possible alternative to applying (typically global and
constant) functions to arguments is to send messages to objects, which
would seem to allow syntax like `x + 1` or `xs (at i) put nx`.
However, though the actors and closures models are formally
equivalent, this poses a real problem for chains of operators of the
kind we commonly see in mathematical expressions — it would seem to
require the equivalent of Lisp’s FUNCALL function, GlyphicScript’s `;`
operator, or Haskell’s `$` function to separate the two operators.
For example, *x* + *y* - *a* × *b* could be written, for example, as
`(o (f x + y) - a * b)` or as `(x + y) $ - a * b`.

The problem with the obvious way of writing it `(x + y) - a * b` is, I
think, that the root expression node has the `-` edge coming directly
out of it, and we’re considering here a universe where root expression
nodes instead have edges coming out of them that denote message
receivers, not operators, and it isn’t clear who is supposed to be
receiving the `-` message.  Maybe it could be made to work, though,
even for things like `(x + y) - (a * b) - 3` and `x + (y) - (a * b) -
3`, by making operators like `+` and `-` link together a sequence of
expressions in the same way that `;` and `,` are suggested to do
above.

This will inevitably lead to somewhat of an impedance mismatch with
conventional mathematical precedence, as did the systematic rules of
APL and Smalltalk, which may lead to bugs in programs.  In this case,
it might be possible to refuse to parse most expressions that have
such problems, but not, for example, `a * b + c`.

#### How about currying? ####

If the difficulty only pertains to functions that must distinguish
between their arguments, such as `<` or `÷`, can we solve it by
currying?  In the function paradigm, this seems to require a function
analogous to FUNCALL or APPLY:

    funcall (< 2) x

Maybe in the message-receiver paradigm it works better?

    x . (2 <)

This (equivalent to `x . 2 <`) doesn’t seem promising.

#### The other programming constructs are simple enough ####

By contrast with primitive operations and function calls,
there are relatively few difficulties with looping,
conditionals, assignment, and function declarations.

A simple while loop poses no difficulty:

    while (condition)
       do body

Perhaps we can use `:` as a tag for such bodies:

    for (x in mylist): some body expression

More generally, looping can be written in a way quite analogous to
Common Lisp, introduced with a `loop` tag and containing an
unsequenced set of keyword-driven clauses:

    loop (for i = 1 to 10)
         (for x in mylist)
         (if ((> x) (< 2)) then collect i)

Conditionals can be written either in a variant of the if-then-else
style described earlier, with the `if` pulled out into an introductory
tag, as

    if ((< x) (> 2)) (then 1) else recursive expression

or in a cond sequence, since now we have a reasonable way of writing
sequences:

    cond ((condition a) -> consequent a)
       | ((condition b) -> consequent b)
       | else other consequent

Or

    if ((condition a) then consequent a)
    elseif ((condition b) then consequent b)
    else other consequent

And lambda-expressions can be written with a delimiter to distinguish
the body from the argument list:

    fn (x y z) => some expression of x y z
    λ (x y z) . some expression of x y z

Assignment could be written in a conventional way:

    x = 3
    x ← 3
    x <- 3
    x := 3

Or in a parallel-assignment way, like `letrec` or `setq`:

    fn (a b) => (while (a): setq (b a) (a (b % a))); b

#### What if we represent branching with infix operators rather than parens? ####

It’s rather jarring in the above that, for example, these two
expressions are equivalent, even though the second looks like a
typographical error:

    while (a): setq (b a) (a (b % a))
    while (: setq (b a) (a (b % a))) a

The fact that the associative and commutative operation of attaching
two branches x and y to the same node is represented using the
asymmetric syntax `(x) y` is, I think, the root of this difficulty.
In a one-dimensional media it is unavoidable that we put them in some
order, but we could imagine using a more visually symmetrical operator
to separate the two symmetrical branches.

For example, `,`, as explored briefly in the ill-fated “Flat dict
syntax” section above.  But we don’t want to write

    while a, do setq ...

because as long as comma binds more loosely than juxtaposition (as it
should), that attaches the `setq` and `while` edges to the same root.
Instead we get

    while (a, do setq (b a, a b % a))

which seems potentially reasonable, though perhaps it gives us back
the extreme nesting we were hoping to escape.  It echoes Python’s
named-parameter syntax, but more placidly; instead of `f(g=h, i=j)` we
have `f(g h, i j)`.

#### Maybe we should use indentation rather than parentheses to indicate side branches ####

A purely indentation-based version of this syntax is doable, replacing
the line-noise punctuation and recursive nesting parentheses with
preattentively-comprehensible horizontal juxtaposition for path
concatenation and vertical juxtaposition for branching.  Maybe using
parentheses rather than indentation to indicate side branches wasn’t
such a hot idea after all!

    while a
          do setq b a
                  a b % a

Alternatively, with more vertical syntax:

    while
      a
      do
        setq
          b a
          a b % a

These variants at last seem like they might actually be an ergonomic
improvement over Lisp syntax rather than a regrettable compromise, at
least if there’s a solution to the problem with arithmetic
expressions.

It unfortunately gets us back to the problem of representing sequences
of statements with progressively increasing nesting:

    do setq nx sum product c
                   *       xs at i
               +   product s
                   *       zs at i
       then do zs at i
                  put sum product - s
                          *       xs at i
                      +   product c
                          *       zs at i
               then xs at i
                       put nx

Or maybe

    let nx sum product c
               *       xs at i
           +   product s
               *       zs at i
        in do zs at i
                 put sum product - s
                         *       xs at i
                     +   product c
                         *       zs at i
              then xs at i
                      put nx

Or maybe, using `,` as an argument-sequencing graph label this time
instead of a syntactic branching operator:

    let nx + * c
               , xs at i
             , * s
                 , zs at i
        in do zs at i
                 put + * - s
                         , xs at i
                       , * c
                           , zs at i
              then xs at i
                      put nx

This seems pretty bug-prone because it took me a couple of tries to
get the `, zs at i` lines to the right indentation level.

This is less nauseatingly bloated than the earlier versions but it
still compares poorly to the C++ version:

      nx = c*xs[i] + s*zs[i];
      zs[i] = -s * xs[i] + c*zs[i];
      xs[i] = nx;

You could argue that maybe syntactic sugar can compensate, but the
right syntactic sugar is precisely what I’m looking for here.

I may be asking too much, since even in Common Lisp it’s still uglier
and more bug-prone than the C++:

    (let ((nx (+ (* c (aref xs i)) (* s (aref zs i)))))
      (setf (aref zs i) (+ (* (- s) (aref xs i)) (* c (aref zs i))))
      (setf (aref xs i) nx))

But that’s not in the same league of noise bloat as most of the
examples above.

We could imagine an infix-formula-evaluating macro like the ones in sh
and Tcl, called, say, `[` (since `FORTRAN` would be a tasteless name,
*Σ* is hard to type and too specific, and `eval` probably means
something else):

    let nx [ c
             * xs at i
             + [ s
                 * zs at i ] ]
        in do zs at i
                 put [ - s
                       * xs at i
                       + [ c
                           * zs at i ] ]
              then xs at i
                      put nx

However, that won’t work as written; `[` has no way to tell whether
you wrote `x * y + z` or `x + z * y`.  If you want it to have a whole
*sequence* of labels to compile, you have to put them on one line,
which also means you can’t inline-evaluate arbitrary bits of code like
`xs at i` without some kind of magic tag.  If you do it that way you
could say

    let nx [ c * [ xs at i ] + s * [ zs at i ] ]
        in do zs at i
                 put [ - s * [ xs at i ] + c * [ zs at i ] ]
              then xs at i
                      put nx

In practice this is maybe not the best example since you would
probably want array indexing in your numeric expression evaluator and
also because a better way to do the whole calculation is

    let xi xs at i
        zi zs at i
        in do xs at i
                 put [ c * xi + s * zi ]
              then zs at i
                      put [ - s * xi + c * zi ]

or maybe even some kind of parallel assignment.  I just picked an
example that’s too easy, I guess.

A potential problem with the proposed embedding syntax: what happens
if you have branching inside the embedded expression?  I mean, you
could imagine something like

    [ 2 * [ gcd a x ] + 3 ]
                b 2

where we invoke `gcd` with named arguments `a` and `b`, which upon
some thought it can be seen can be made to work just fine — the `[`
parser just needs to look down all the branches to find the
terminating `]` of the embedded expression, not just one.  This gets
uglier if you have two such things; this will not work:

    [ 2 * [ gcd a x ] + 3 * [ lcm a x ] ]
                b 2               b 2

But it will work if expressed this way:

    [ 2 * [ gcd a x ] + 3 * [ lcm a x ] ]
                                  b 2
                b 2

This is complex enough to be confusing.

##### How is that different from SRFI-49 I-expressions, Wisp, or LISPIN? #####

In the above proposal, as long as arcs out of a node remain unordered,
these two expressions are equivalent:

    a b c
        d
      e

and

    a e
      b d
        c

as well as two more variations.  Moreover, as mentioned toward the
beginning, code written for the following structure will also work on
the above structure without change:

    a b c

##### An unpolished parser in Python #####

I just wrote [the following simple parser in Python][4] which seems to
handle the syntax outlined above properly and translates it into
graphviz files you can view with, for example, `dot -Tx11`.  It’s
maybe 50% longer than the S-expression parser above in Lua.  It
contains some duplication to factor out, would need to be extended to
handle quoted strings, can break its graphviz output if you put
special characters in the input, wastes memory, doesn’t handle tabs,
and (as always with Python) breaks on Unicode input in environmentally
dependent ways, but hopefully it represents some kind of clarifying
sketch.

    from __future__ import print_function
    import re
    import sys


    def parse(lines):
        stack = []
        node_counter = 1
        edges = []

        for line in lines:
            col = len(re.match(r'\s*', line).group(0))
            while stack and stack[-1][0] >= col:
                stack.pop()
            word, start, empty = [], col, ()

            while col < len(line):
                c = line[col]
                if word and re.match(r'\s', c):
                    nw = ''.join(word)
                    word[:] = empty
                    if stack:
                        edges.append((stack[-1][2], nw, node_counter))
                    else:
                        edges.append((0, nw, node_counter))
                    assert start is not None
                    stack.append((start, nw, node_counter))
                    node_counter += 1
                    start = None

                elif re.match(r'\S', c):
                    if not word:
                        start = col
                    word.append(c)

                col += 1

            if word:
                nw = ''.join(word)
                if stack:
                    edges.append((stack[-1][2], nw, node_counter))
                else:
                    edges.append((0, nw, node_counter))

                assert start is not None
                stack.append((start, nw, node_counter))
                node_counter += 1
                start = None

        return edges

    def graphviz(edges, name='cosas'):
        yield 'digraph '; yield name; yield ' {\n'
        yield '    rankdir=LR;\n'
        yield '    node [label="", shape=circle];\n'
        for start, label, end in edges:
            yield '    '; yield str(start); yield ' -> '; yield str(end)
            yield ' [label="'; yield label; yield '"];\n'
        yield '}\n'


    if __name__ == '__main__':
        sys.stdout.writelines(graphviz(parse(sys.stdin)))

So for example it renders the first example above as follows:

    digraph cosas {
        rankdir=LR;
        node [label="", shape=circle];
        0 -> 1 [label="while"];
        1 -> 2 [label="a"];
        1 -> 3 [label="do"];
        3 -> 4 [label="setq"];
        4 -> 5 [label="b"];
        5 -> 6 [label="a"];
        4 -> 7 [label="a"];
        7 -> 8 [label="b"];
        8 -> 9 [label="%"];
        9 -> 10 [label="a"];
    }

[4]: http://canonical.org/~kragen/sw/dev3/treeify.py

Since it took me about 40 minutes to write, test, and (mostly) debug
that, including the graphviz output, this syntax is probably not too
complex for a language whose first-draft compiler you want to write in
an afternoon.

### Functions for manipulating edge-labeled graphs ###

What is our equivalent of the ur-Lisp’s CAR CDR CONS NULL ATOM QUOTE
EQ?  The fundamental traversal operation should presumably be
`go(node, tag)`, which returns the node (if any) obtained by
traversing the edge labeled `tag` from `node`, equivalent to
`node[tag]` in JS or Lua syntax; if duplicate edges are allowed,
probably both its `node` argument and its return value should be
*sets* rather than individual nodes, and possibly `tag` should also be
a set.  Invoking the tag as a function `tag(node)` is an alternative
possibility.

(If they are sets of nodes, we need to be able to iterate over them;
we need to be able to test whether they are empty, but iterating over
them with side effects may be an adequate interface for that.)

In the case where they are indeed individual nodes, there is the
possibility of returning nil, in which case we need a way to detect
nil — in a functional paradigm, `isnil(node)`, but alternatives
include treating nil as false in conditionals (making the function
implicit); a pattern-matching `ifnil(node, consequent, alternate)`
function which takes two functions to invoke, one with the node if it
is not nil, and the other if it is; and the λ-calculus-like
`node(consequent, alternate)`, which does the same without a separate
function.

It’s also necessary to iterate over the edges out of a node, since
arbitrary values such as 57 are also stored as tags in the above
model.  (This wouldn’t have to be the case — 57 could be a node, as it
is in Lisp — but without this ability to iterate over edges you also
can’t write PRINT or the macro transformer for LETREC.)  You can do
this with a function `kids(node)` or `pairs(node)` which returns a
list in the usual car–cdr or first–rest form; perhaps each node in the
resulting list contains both a key — the edge label — and a
value — the child node that it leads to.  (That’s superfluous, though,
since `go(parent, tag)` will give you the child node.)

If we consider tags to attach to nodes rather than to the edges
leading to them, we might be able to conflate nodes with tags, so that
the `go()` function above takes two arbitrary node arguments.  (The
alternative is to have special “tag nodes”.)  But we still need to be
able to compare tags for equality, thus `eq(tag1, tag2)` or
`sametag(node1, node2)` is needed.

With `go`, `isnil`, `kids`, and `eq` (or the other alternatives
discussed above), we can traverse the graph as we please, just as with
CAR, CDR, NULL, ATOM, and EQ.  However, constructing new graph
structure — as with CONS — requires another operation: `add(node, tag,
kid)`, which returns a new node identical to `node` except that it now
has an edge with tag `tag` to node `kid`.  However, this is not quite
enough — it doesn’t allow us to produce new nodes with no children.
So we need `new()` to produce such a fresh node.

And of course we can provide QUOTE (and, more interestingly,
quasiquote) just as Lisp does.  That’s what homoiconicity means!
