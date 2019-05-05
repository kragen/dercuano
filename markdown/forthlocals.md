This was a big epiphany for me in Forth: you usually shouldn’t use
function-local variables.  Instead, use “global” variables.  This is
true to some extent in PostScript, too, though less strongly.

> First, a disclaimer: don’t take what I say about Forth too
> seriously, because I’ve never written a significant program in
> Forth, only exercises like a self-compiling compiler.  I’ve never
> done anything more than a few hundred lines of code in PostScript,
> either.

Traditional Forth lacks function-local variables. Function-local
variables are crucial to Smalltalk, Lisp, and Algol-family programming
for three reasons: lexical locality, recursion, and closures. Forth
solves these in different ways, so **it’s okay to use
non-function-local variables instead**, and this has a benefit for
factorability of the code.  I would say “it’s okay to use global
variables instead”, but one of the reasons it’s okay is that they
aren’t really global in Forth.

Lexical locality
----------------

In Algol-family languages like Pascal or C, if a variable isn’t local
to a function, it’s global to the entire program, which means it be
modified by any code at all, including not only other files in your
project, but even library modules you don’t have the source code to.

By contrast, in Forth, a variable’s scope extends only from the point
of its declaration over the code that lexically follows it, up to the
point where you switch to a different wordlist (or, in traditional
Forths, vocabulary) or define another variable with the same name.
This is not as small a scope as a C or Pascal function, but it’s a
much smaller scope than a C or Pascal program, so the variable name
collision problem is manageable.

The point about another variable with the same name bears repeating:
if you declare another variable with the same name in Forth, the old
declaration stops being visible, and each part of the code uses the
version of the variable that was visible when it was being compiled.

Languages like Python or Common Lisp are somewhere in between: a
global variable (defined with `defparameter` or `defvar` in CL) is not
global to the entire program, but just a single module.  This reduces
the seriousness of the problem.

PostScript, with its odd hybrid of Forth and Lisp semantics, is closer
to the Algol family in this sense — its symbols (“name objects”) are
not module-scoped like Common Lisp symbols, nor are their scopes
lexical as in Forth.  You can dynamically add and remove dictionaries
from the dictionary stack, but this is clumsy (it must be done in
every function) and error-prone.

Recursion
---------

In languages like Pascal or C, any function is potentially recursive,
which means that if its local variables are not stored in
stack-allocated memory, they could get overwritten by recursive calls.
Moreover, local variables are the only language-native mechanism
provided for stack-allocation of memory; without them, simple things
like recursive-descent parsers become major feats of software
engineering.

In languages like Smalltalk and Python, the problem is even worse,
because nearly any infix operator in your method could result in a
recursive call chain that includes the same method.  So even methods
that are not intended by their authors to be recursive are likely to
need to be re-entrant.  (The gradual introduction of pervasive
multithreading in the modern C ecosystem has had a similar effect.)

Also, Smalltalk, Lisp, Python, and functional languages like ML
strongly encourage you to use recursively-defined data types.

The net effect of all of this is that, in these environments,
function-local variables are vastly preferable to statically allocated
variables.

By contrast, in Forth, recursion is very much the exception;
recursively-defined data types are unusual, and functions can only
call functions that are defined textually earlier in the program,
except using `RECURSE`, `DEFER`red words, or similar mechanisms, which
are unlikely to pop up without the author noticing them.  And, if you
want to save and restore the value of a variable for a recursive or
potentially recursive call, you can do so fairly easily using the
operand stack; `A @ B @ RECURSE B ! A !` saves the values of `A` and
`B` during a recursive self-call, doing explicitly what Perl 4 or a
dynamically-scoped Lisp would save local variables implicitly.

In PostScript, again, the situation is intermediate; recursive
function calls are just as easy as in Lisp, and it’s easy to define
recursive data structures, although at least the native list-like data
structure is an array, not a linked list.  But PostScript shares with
Forth relative ease at explicit saving and restoring variables on the
operand stack.  PostScript also doesn’t have the tricky ad-hoc
polymorphism that can give rise to unexpected recursion in Smalltalk
and Python; it does use first-class function values pretty often, but
rarely in ways that lead to unexpected recursion.

So function-local variables are not necessary to permit recursion in
stack languages, and recursion is typically less of a danger.

(It’s worth pointing out that function-local variables are not
sufficient to make recursion safe.  Recursive code can easily get
stack overflows or suffer re-entrancy bugs related to nonlocal data
structures, and so is prohibited in things like MISRA C.)

Closures
--------

Pascal has very limited closures, which are also present in GNU C,
although little-used.  In vanilla C, the only way to get the
equivalent of a closure — for example, for `qsort` — is to store the
data it needs in statically allocated variables, which breaks
re-entrancy and thus causes multithreading problems.  (glibc provides
a `qsort_r` function that takes a userdata parameter to solve this
problem.)

Languages like (modern) Smalltalk, Python, Common Lisp, Scheme, Ruby,
and JavaScript have closures and use them extensively.  So
function-local variables become a crucial mechanism for encapsulating
state in objects of indefinite extent.

In the Forths that have added local variables, local variables do not
provide closures; neither does PostScript support closures with local
variables, since PostScript’s dictionary stack amounts to purely
dynamic scoping, like Lisps before Scheme.  Forth, instead, provides
closures with the `CREATE DOES>` mechanism, which is explicit rather
than implicit about what state is being stored.  I don’t know what the
PostScript equivalent would be, although I bet you could hack
something together with runtime code generation.

So function-local variables do not provide closures to augment the
expressive power of PostScript or Forth, the way they do in many
modern programming languages.

It’s okay to use non-function-local variables in PostScript and especially Forth
--------------------------------------------------------------------------------

In summary, function-local variables in Forth aren’t needed for
lexical locality, recursion, or closures, and when they’re available,
they also don’t provide closures.  And function-local variables in
PostScript aren’t needed for recursion, and they don’t provide
closures.  So the advantages that make them a no-brainer in other
families of languages are weaker or absent.  What about the
disadvantages?

Function-local variables are more costly in Forth or, especially,
PostScript, than in other languages.  Consider this particularly
egregious case of stack abuse in PostScript (from
[Heckballs](http://canonical.org/~kragen/sw/laserboot/cut-7/heckballs.ps)):

    % Calculate distance from x1 y1 to x2 y2
    /dist { 3 2 roll sub  3 1 roll sub  dup mul exch  dup mul add  sqrt } bdef

Probably a better way to write this is as follows:

    /dist { 4 dict begin  /y2 exch def  /x2 exch def  /y1 exch def  /x1 exch def
            x1 x2 sub dup mul  y1 y2 sub dup mul  add sqrt  end } def

There are two interesting things to note here:

1. The new definition is almost twice as long, 32 rather than 19
   tokens, and includes a new error-prone `end` at the end.  Also, it
   isn’t clear that it’s more readable, as the parameters are
   necessarily listed in reverse order.
2. The new definition isn’t as safe to use with `bind def`, because
   that introduces the danger that the variables `x1` and so on might
   accidentally be bound to some definition in the enclosing
   environment, rather than being local variables as intended.  (As it
   happens, in this case there are no such variables, and `bind def`
   would have worked fine.)

Suppose that instead we use non-function-local variables:

    /dist { /y2 exch def  /x2 exch def  /y1 exch def  /x1 exch def
            x1 x2 sub dup mul  y1 y2 sub dup mul  add sqrt  } def

The size penalty is somewhat less, although we run an even worse
variable-collision risk, since this will clobber any values of x1, y1,
x2, and y2 that any other function is using at the time — a problem
much less likely in Forth.

We could conceivably refactor this into smaller pieces:

    /is-p1 { /y1 exch def  /x1 exch def } bdef
    /is-p2 { /y2 exch def  /x2 exch def } bdef
    /dx { x1 x2 sub } def  /dy { y1 y2 sub } def  /sq { dup mul } bdef
    /dist { is-p2 is-p1  dx sq  dy sq  add sqrt } bdef

In PostScript, you can still do this with function-local variables:

    /is-p1 { /y1 exch def  /x1 exch def } bdef
    /is-p2 { /y2 exch def  /x2 exch def } bdef
    /dx { x1 x2 sub } def  /dy { y1 y2 sub } def  /sq { dup mul } bdef
    /dist { 4 dict begin  is-p2 is-p1  dx sq  dy sq  add sqrt  end } bdef

You can’t do that in Forth, any more than you can in C, which makes
using function-local variables in Forth very costly to both the
flexibility and the predictability of your code.  To my mind,
predictability is key to its readability.

So using function-local variables, although it’s a viable strategy in
PostScript, isn’t nearly the slam-dunk obvious win that it would be in
more conventional languages.  In Forth, often, it’s actively
counterproductive.

<script src="http://canonical.org/~kragen/sw/netbook-misc-devel/addtoc.js">
</script>
<link rel="stylesheet" href="http://canonical.org/~kragen/style.css" />
