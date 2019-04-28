Toward a lightweight, high-performance software prototyping environment
=======================================================================

I was thinking that it might be worthwhile to prototype a client
project, but I don’t have a reasonable environment to do it in.  The
easiest way is to use a high-level language to write the high-level
app logic, while using existing libraries for storage, cryptography,
and networking; the necessary user interface can be provided portably
by an embedded HTTP server.

I’m going to talk a lot about performance in here, along three axes:
speed, memory usage, and package size.  If you can do something ten
times as fast, often that means you can do ten times as much of it,
and in many contexts if you can do it in a tenth of the memory, you
can also do ten times as much of it.  A lot of computing resources are
available in the form of fungible megabyte-seconds.  Package size is
probably less important, except as a proxy for implementation
complexity, but there are cases where it matters because of either
limited storage or limited network bandwidth.  For example, if you’re
embedding an interpreter compiled with Emscripten or wasm in a web
page, it’s okay if it’s 1 MB but probably not if it’s 100 MB.

It turns out that software has advanced significantly, and there are
several pieces of software out there that offer one to three orders of
magnitude performance improvements over commonly-used alternatives.

High-level language: Lua
------------------------

Lua is a safe, simple, easy-to-embed scripting language, with
semantics similar to JS — but its whole grammar fits on one page of
the 79-page reference manual.  Its interpreter performance is better
than that of other languages at a similar level, such as Python, Perl,
Tcl, and even most implementations of Scheme, and there’s a tracing
JIT implementation called LuaJIT whose performance [exceeds even that
of best-in-class JS JIT implementations like V8][5] [and even, on some
scientific benchmarks, C][4].

More specifically, Lua is a dynamically-typed Algol-like
lexically-scoped statement-oriented imperative language with a
mark-and-sweep GC (incremental since version 5.1), closures,
dynamically-growing hash tables, eval (but no apply), tail-call
elimination, a reified global environment, exception handling (with
stack traces by default), a metaobject protocol, dynamic method
dispatch, reflection, lightweight cooperative threads, a generic
iterator protocol, finalizers, weak references, operator overloading,
multiple-value returns, multiline strings, goto, variadic functions,
and an immutable 8-bit-clean encoding-agnostic string type.

Lua **does not have** classes, ML-style pattern-matching, inheritance
(though you can implement it), integers (until 5.3), complex numbers,
first-class continuations, built-in serialization, first-class tuples,
function overloading, named or default arguments (though there is
syntactic sugar that comes close), preemptive threading, Prolog-style
backtracking, lazy evaluation, sequence slicing, unwind-protect,
UCS Unicode strings,
macros, or much of a standard library.

Like PHP, Lua uses the same mutable type for sequences and finite
maps, and a single value can have properties of both.  Despite
guaranteeing tail-call elimination, Lua’s closure syntax is
heavyweight enough to preclude using it to define custom control
structures as in Smalltalk or Ruby, and it has no macro facility.

The standard Lua 5.1 interpreter is only 171 KiB on my machine, and
LuaJIT 2.0.4 is only 443 KiB.
The documentation says, “The virtual
machine (VM) is API- and ABI-compatible to the standard Lua [5.1]
interpreter and can be deployed as a drop-in replacement.”  LuaJIT is,
unfortunately, orphaned,
as is Lua 5.1,
but its FFI is to die for (it includes a runtime parser for C)
and its performance is seriously impressive.
The current version of Lua is 5.3; its stock interpreter is 215KiB.

I’m not quite as comfortable in Lua as I am in Python, and I find that
Lua is a bit more bug-prone and a bit more verbose.  However, modern
Python is now also extremely bug-prone due to serious mistakes in how
Unicode support was added, and Python is becoming quite unwieldy;
/usr/lib/python3.5 on my laptop contains 183,000 SLOC of Python code,
and the interpreter itself is another roughly half-million lines of C,
half of which is in extension modules.  This is roughly 30× the size
of the Lua 5.3 codebase.  A Python installation is 100 MB; a Lua
installation is 171 KiB, or
443 KiB if you use LuaJIT.

Lua is particularly appealing for [high-concurrency applications like
network servers because it supports “coroutines”][6], which are really
cooperative threads rather than coroutines; this is similar to
Python’s “generator” construct used in the asyncio library, though it
differs in some significant details.  Even more closely, it resembles
the “greenlet” construct used in the now-orphaned Stackless Python EVE
Online is written in.  Coroutines allow programming of network
protocols in a much more structured fashion than that permitted by
promises in JS.

Lua is somewhat easier to extend with modules in C than Python or even
Tcl, although its style is not to everyone’s liking.

A freshly started Lua 5.1 virtual machine on my laptop has a resident
set size of 2.7 MB.  In modern terms this is exceedingly lightweight,
some 300 times smaller than a browser tab with Slack open, but it’s
still large enough that this environment is not going to be usable for
deeply-embedded processing (though [NodeMCU][2] provides a Lua 5.1
environment on an ESP8266, which has 96KiB of RAM — as of September
2018 it supports XIP for Lua code, so you can have 256KiB of Lua code
and constants).  LuaJIT is even smaller, at 908 KiB resident set size.

Software embedding Lua includes Grim Fandango, Escape from Monkey
Island, Vim, awesome, Elinks, VLC, World of Warcraft, nmap, Wireshark,
haproxy, Haka, sigrok, MediaWiki, LuaTeX, the Battle for Wesnoth,
LÖVE2D, OpenResty, and Adobe Lightroom.

[2]: https://learn.adafruit.com/adafruit-huzzah-esp8266-breakout/using-nodemcu-lua
[4]: http://lua-users.org/lists/lua-l/2009-10/msg01098.html
[5]: http://factor-language.blogspot.com/2010/05/comparing-factors-performance-against.html
[6]: http://leafo.net/posts/itchio-and-coroutines.html

### Bug-proneness ###

Above I said Lua was pretty bug-prone; I will elaborate on that here,
because I think it’s the main disadvantage of Lua, though one that’s
worth accepting in order to get the rather awesome features described
above.  Eventually this bug-proneness seems likely to limit the
fraction of your code that’s worth writing in Lua.

Of course, Lua is dynamically typed, which isn’t really a problem in
itself, but does slightly exacerbate the other problems.

In several cases, it attempts to DWIM in ways that can cover up bugs;
Lua does not believe that “errors should never pass silently”, as the
Zen of Python says.  Specifically:

- Reads of nonexistent variables and table entries simply returns
  `nil` rather than raising an error;
- I/O errors do not raise errors by default when using the more
  general I/O library;
- worse, writing to nonexistent variables creates new global (!)
  variables;
- function argument list and return value adjustment similarly
  introduces nils, and also silently discards extra values.
- In Lua 5.3, which adds integers, implicit numeric coercion (int to
  float, and vice versa) is the rule, and integer math can produce
  different results from floating-point math;
- concatenating numbers to strings implicitly converts them to
  strings; and
- as in JS, writing to nonexistent sequence indices extends the length
  of the sequence.

In a few cases, the special nature of `nil` can create bugs analogous
to SQL injection and blueboxing — `a[b] = c` will delete the table
entry `a[b]` if `c` is unexpectedly nil; worse, if `b` was a number,
that may unexpectedly change the length of the sequence `a`.
Similarly, unintentionally returning a `nil` value will terminate an
iterator early.

Lua’s choice of indices for sequences — 1, 2, … n rather than the
now-conventional 0, 1, … n-1 — is slightly more bug-prone, for
precisely the reasons described by Dijkstra.

As in multitasking Forth systems, but unlike Python generators (or for
that matter JS promise callbacks), any function invoked by a Lua
coroutine has the possibility of yielding control.  But because
coroutines are resumed explicitly, rather than using an implicit
global run queue, there is no locking mechanism that could block
potentially interfering concurrent executions.  Ierusalimschy claims
this makes the coroutine mechanism “more powerful”, which is certainly
true, and precisely the problem.  It’s precisely analogous to
unchecked exceptions, aspect-oriented programming, or dynamic method
dispatch: by allowing a local change to have an effect that would have
otherwise required a global change, this power means that to determine
a certain property of the program that would have been local, instead
a global search is needed.

Storage: LevelDB
----------------

LevelDB is a high-performance persistent bytestring key-value store by
Jeff Dean and Sanjay Ghemawat, supporting ordered traversal and a
limited form of transactions; on my laptop, it can handle about
300,000 key-value-pair insertions per second, about 10 to 100 times
faster than Postgres and [2 to 20 times faster than SQLite][7].  Unlike
Berkeley DB, LevelDB remains fast when inserting many widely scattered
keys into a large existing data store, even on high-capacity
spinning-rust disks rather than lower-capacity SSDs, using a data
structure sometimes known as the “LSM-tree” or “log-structured merge
tree”.

The library itself is 359 KiB, but it depends on libsnappy, the
high-speed compression library previously known as Zippy, which is
another 30 KiB.

Other popular alternatives for this kind of thing include Berkeley DB,
Redis, MongoDB, SQLite, or using some kind of serialization library
(such as a JSON implementation, FlatBuffers, Protocol Buffers, or
Thrift) to generate bytes that your code then manually writes to a
file; and then there’s RocksDB, which is a fork of LevelDB.  Most of
these are very large, very featureful, and very slow.

Redis and MongoDB involve running separate processes, and their
authors are playing dishonest games to confuse people about free
software.

Berkeley DB is 1.7 MiB and many times slower at bulk insertions; also,
it’s controlled by Oracle.

SQLite is 922 KiB and many times slower at everything except inserting
large blobs and reading.

RocksDB was written as a fork of LevelDB with improved performance,
but it’s 3.1 MiB.

LevelDB is used by the official Ethereum client, [formerly the
official Bitcoin client][9], the high-performance distributed
filesystem Ceph, Chrome, PouchDB, and Riak; Parse was built on
RocksDB.

[7]: https://web.archive.org/web/20110820001028/http://leveldb.googlecode.com/svn/trunk/doc/benchmark.html
[9]: https://github.com/bitcoin-core/leveldb-old/blob/bitcoin-fork/doc/table_format.txt

Cryptography and networking: libsodium
--------------------------------------

Libsodium is a [better-packaged version][10] of the highly-regarded
NaCl networking and cryptography library,
with some extra functionality added.  Unlike other popular
libraries such as OpenSSL, libsodium doesn’t expose a wide variety of
cryptographic primitives; instead, it provides a small number of
functions that are easy to use securely, based on a small and
conservatively chosen set of cryptographic primitives, including
Salsa20, AES-256-GCM, SHA-256, SHA-512, ChaCha20, Poly1305, and
Ed25519.  In many cases, it includes the fastest available
implementations of these primitives for many platforms.

The only plausible alternatives here are NaCl itself and monocypher, a
fork of libsodium.

[10]: https://umbrella.cisco.com/blog/2013/03/06/announcing-sodium-a-new-cryptographic-library/

Compression: Snappy and zlib
----------------------------

LevelDB optionally compresses the data it writes using Snappy, since
Snappy compression and especially decompression is significantly
faster than spinning-rust disks ([250MB/s per core for compression,
twice that for decompression][8]).  Since the platform embeds
LevelDB, it necessarily includes Snappy, so we might as well expose it
at the Lua level.

However, zlib — the universally-used implementation of LZ77
compression — compresses sufficiently better than Snappy that it’s
worth including it as well.  In particular, for compressing library
code which is loaded at startup, zlib is a big win; it also permits
implementing compressed HTTP and accessing zipfiles.  zlib is only
about 100 KiB, and the lua-zlib binding is 9 KiB.

As a quick test, I compressed a [Lua source file][0] I wrote a few
years ago with Snappy and zlib.  It compressed to 0.50 times its
original size with Snappy and 0.34 times its original size with zlib.

[0]: http://canonical.org/~kragen/sw/inexorable-misc/hdl.lua
[8]: https://web.archive.org/web/20110822213330/http://code.google.com:80/p/snappy

HTTP server
-----------

You can hack together an adequate HTTP/1.0 server in [about 300
machine instructions][1] on top of Linux sockets, or a similar or
smaller number of lines of code in higher-level languages.  (Often the
worse performance of higher-level languages requires a bit more
complexity to compensate, but even the fairly rich implementation in
Python’s `BaseHTTPServer`, `SimpleHTTPServer`, `urllib`, `urlparse`,
and `cgi` modules only works out to about 2600 lines of code.)

There exists a fairly full-featured webserver in Lua called Xavante
(142K, plus dependencies on coxpcall (46K), copas (99K), and
luafilesystem (82K), for a total of 369K).

Embedding an HTTP server is by far the easiest way to provide a modern
user interface, even on the local machine.

[1]: http://canonical.org/~kragen/sw/dev3/server.s

Miscellaneous libraries
-----------------------

The Lua standard library contains very little; even sockets are
provided by the external “luasocket” package (563K, including
implementations of HTTP, SMTP, and FTP), and although the built-in
filesystem interface allows you to read and write files, it doesn’t
support directory creation or listing; until Lua 5.3, the language
doesn’t natively include an integer type or bitwise operations.  The
“luaposix” library is a smaller alternative (204K, plus bitop, a 75K
dependency) to the luasocket and luafileystem libraries, providing the
full POSIX API.

Total weight
------------

The total virtual machine should be 0.45 MB of LuaJIT + 0.37 MB of
LevelDB + 0.38 MB of libsodium + 0.03 MB of Snappy + 0.10 MB of zlib +
0.10 MB of other library code (mostly Lua), for a total of
1.43 MB, a floppy disk’s worth.

However, *those are the uncompressed sizes*.  The zlib-compressed
sizes of the various pieces are as follows:

    |                                               | KiB | KiB (gz) |
    | LuaJIT                                        | 443 |      227 |
    | /usr/lib/x86_64-linux-gnu/libleveldb.so.1.18  | 359 |      151 |
    | /usr/lib/x86_64-linux-gnu/libsodium.so.18.0.1 | 376 |      165 |
    | /usr/lib/x86_64-linux-gnu/libsnappy.so.1.3.0  |  30 |       13 |
    | /lib/x86_64-linux-gnu/libz.so.1.2.8           | 102 |       55 |
    | misc                                          |     |      100 |

If we figure we need an uncompressed zlib to bootstrap uncompressing
the rest of the platform, then the total is 758 KiB.

Other candidates for inclusion
------------------------------

I’d really like to include support for high-performance numerical
computation, machine learning, windowing user interfaces, GPGPU,
audio, ØMQ or similar, and FlatBuffers (or Cap’n Proto or SBE).
[Torch 7][3] has numerical array support for Lua; it’s billed as “a
scientific computing framework [for LuaJIT] with wide support for
machine learning algorithms that puts GPUs first,” and it also
supports non-LuaJIT Lua 5.2; [unfortunately it’s orphaned][11] in
favor of a C++ replacement called “ATen”.

[3]: http://torch.ch/
[11]: https://github.com/torch/torch7/blob/master/README.md
