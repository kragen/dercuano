I was discussing eventual content synchronization for disconnected
operation through eventually-consistent data stores for
computer-mediated communication systems with an entity known as The
Doctor, and they suggested the use of the rsync algorithm and its
variants, which I thought was really interesting.

As it turns out, the rsync delta-transfer algorithm offers an
interestingly scalable approach to synchronizing eventually-consistent
data stores like these, one that has not been exploited previously to
my knowledge.

Broadcast and flooding
----------------------

The basic problem to solve here is how to distribute each of a large
number of messages originating from many different sources to each of
a large number of subscribers.  For example, you might want every
reader of alt.tasteless to be able to see all of the recent postings
from anyone to alt.tasteless, or everyone who joins #hottub to be able
to see all the messages someone sends to #hottub after they join, or
every host on your Ethernet to be able to see every ARP request any
host broadcasts on that Ethernet.  Moreover, rather than achieving
this through a centralized bulletin board or a shared broadcast medium
like thinnet, you want to achieve it via some potentially complex and
changing topology of interconnected network nodes (originally,
"gateways"; nowadays sometimes "routers").

(For the time being I will ignore the questions of multiple channels,
unicast messages as well as broadcast, whether the subscribers and the
publishers are the same set, whether there are some security
requirements on their membership, and whether there's some kind of
need for load-balancing or "sharding" for performance.)

The obvious thing to try is for each node to send each message it
receives to all of the other nodes to which it is connected.  So if
you have the topology A -- B -- C -- D; B -- E, then if node A sends a
message, it will arrive at node B, which will forward it to nodes C
and E; node C will then forward it to node D; and we're done.  This
simple flooding approach has one main problem: first, any cycle in the
connectivity graph will produce an infinite number of copies of every
message.

I know of four approaches to solving this problem: TTLs and
return-paths, the spanning-tree protocol, the Usenet message-id
approach, and the per-publisher log approach used in Kafka.  And I
think the rsync approach might offer some interesting benefits.

TTLs and return-paths
---------------------

The most basic approach to limiting broadcast message duplication by
routing loops is a "time-to-live" field on each message sent across
the network.  This field is decremented at each router, and messages
with TTL of 0 or less are discarded.  So a message originally sent
with a TTL of 5 is guaranteed to reach a distance of no more than 5
routers from the sender, and a message originally sent with a TTL of
10 is guaranteed to reach a distance of no more than 10 routers from
the sender.

This is a crude approach, but it does at least guarantee that the
number of duplicates of each message is *finite*.  Consider the
topology A -- B -- C -- A.  If A sends a message with a TTL of 30,
they will initially give a copy to both B and C.  One copy will travel
clockwise around the loop 10 times, while the other will travel
counterclockwise around the loop 10 times; each node will receive the
message (and every other message) 20 times.

But the number can be exponentially large.  Consider the "diamond
graph" A -- B -- C -- A; B -- D -- A.  Every time a message reaches B
or A, two copies of it will be made; for a copy arriving at B from D,
for instance, copies will be sent to C and A, and A will then send
copies to C and D.  So a message with a TTL of 5 sent from A will go
through the following population stages:

1. B 1; C 1; D 1.
2. B 2; C 1; D 1.
3. A 4 (2 from B, 1 from C, 1 from D); C 2 (from B); D 2 (from B).
4. A 4 (2 from C, 2 from D); B 2 (from A); C 3 (from A); D 3 (from A).
5. B 10 (4 from A, 3 from C, 3 from D); C 4 (2 from A, 2 from B); D 4
  (2 from A, 2 from B).

And at that point it stops because the TTL was 5.  But it should be
clear that even this simple graph with four nodes can produce
exponential growth of the message population to some exponential
function of the TTL with the simple flooding algorithm, making the TTL
approach of limited effectiveness.  This means that, at best, the
network will perform very poorly, and very likely will fail badly
under load.

A slight refinement of this approach was used on Usenet (though not as
the primary duplicate-suppression mechanism); each copy of a message
carries a "return path" that describes the path it took to get to
where it is, which could typically be used as an email routing path to
send a reply to the poster.  The obsolete SSRR option in IP and the
obsolete multihop mail routing system in SMTP work the same way
(@foo,@bar:baz@quux, I think was the SMTP notation).  This can serve
to suppress duplicates due to routing loops because if a message
received at node X has node X in its return path, then it is obviously
going nowhere useful and should be dropped.  This successfully
suppresses exponential message growth in simple networks like the
diamond graph above, but not in larger networks.  Consider, for
example, A -- B -- C -- D -- E -- F; A -- C -- E; B -- D -- F.  A
message injected at A goes through the following stages of evolution:

1. B!A, C!A
2. B!C!A, C!B!A, D!B!A, D!C!A, E!C!A
3. B!D!C!A, C!D!B!A, D!B!C!A, D!C!B!A, D!E!C!A, E!C!B!A, E!D!B!A,
   E!D!C!A, F!D!B!A, F!D!C!A, F!E!C!A
4. B!D!E!C!A, C!E!D!B!A, D!E!C!B!A, D!F!E!C!A, E!C!D!B!A, E!D!B!C!A,
   E!D!C!B!A, E!F!D!B!A, E!F!D!C!A, F!D!B!C!A, F!D!C!B!A, F!D!E!C!A,
   F!E!C!B!A, F!E!D!B!A, F!E!D!C!A
5. B!D!F!E!C!A, C!E!F!D!B!A, D!F!E!C!B!A, E!F!D!B!C!A, E!F!D!C!B!A,
   F!D!E!C!B!A, F!E!C!D!B!A, F!E!D!B!C!A, F!E!D!C!B!A

Then it ends, because every return-path contains all six nodes, so
there is nowhere else for any message to go.  It should be clear that,
although the amount of traffic generated on the network by this single
message is finite, it is already large and grows exponentially with
the size of the network because the number of simple paths by which a
message can reach each node grows exponentially with its distance from
the message origin.  Node F got 13 copies of the message.

The spanning-tree protocol
--------------------------

In order to achieve very high message rates without the above kinds of
explosive message duplication, IRC and networks of Ethernet switches
use essentially the simple flooding approach described above.  To
avoid the disaster of infinite message multiplication, they maintain a
strict spanning tree among the nodes: only enough links are active to
achieve full connectivity, deactivating any links that would create
cycles.

The topology of the network is assumed to change on a much slower
timescale than the transit time of individual messages.  Any message
that is transiting the network when the topology changes may be lost
or duplicated, so reliability and semantic deduplication must be done
by network endpoints; if a message's transit is slow enough to include
many topology changes, it may be duplicated many times.

Moreover, for the topology to avoid containing many cycles all the
time, the interval between topology changes must be large compared to
the end-to-end *latency* of the network, because activating two new
links on opposite sides of the network may form a cycle which requires
the deactivation of some link once detected.  If the latency is large,
this situation will go undetected for a long period of time.  However,
the same large latency will also limit the number of messages thus
duplicated.

This approach is not very suitable for networks like FidoNet and UUCP,
which in their heyday had end-to-end latencies typically on the order
of a week, organized around daily modem telephone calls, and each of
whose links might or might not function on any given occasion.  So
Usenet used a different approach for duplicate suppression.

The Usenet message-ID approach
------------------------------

The Usenet approach is to identify each message with a "Message-ID"
unique to that message, but much shorter than the entire message.
Then, before transmitting the entire message from one node to another,
the communicating nodes verify that the message isn't already present
on the receiving node; the Usenet protocol NNTP has commands called
IHAVE and SENDME for this purpose.  `IHAVE foo` indicated the
availability of the message with the message-ID `foo`; `SENDME foo`
requested its transmission, if possible.  In [the Bitcoin
protocol][1], the `inv` message lists data blocks, block headers, or
mempool transactions, like a bulk IHAVE; and the `getdata` message
plays the role of `SENDME`.

[1]: https://en.bitcoin.it/wiki/Protocol_documentation

A serious weakness of the Usenet implementation was that the
message-ID is chosen by the sender, typically a string something like
"trn.20190822.1830.10831@canonical.org", incorporating the hostname,
the date and time, the software being used, the PID of the running
process, and so on, in an effort to avoid accidental duplication.
Nevertheless, bugs did sometimes result in unintentional duplication,
and people sometimes engaged in intentional duplication to attempt
censorship.

Git uses a similar approach, but uses the SHA-1 of the "objects" as
the message-ID rather than a sender-computed string.  It is
conjectured to be computationally infeasible to produce a different
object with the same SHA-1, even intentionally, much less
accidentally.

I think FidoNet used this approach to propagate messages in its
"echos", which were distributed message bases similar to Usenet
newsgroups, but somewhat more primitive.  The Doctor tells me that the
message-IDs FidoNet could use to avoid unlimited duplication of
messages were tuples of the form (network, zone, region, board, sub,
message), where the (zone, region, board) was a hierarchically
assigned numerical address space uniquely identifying the particular
bulletin board on which the message originated, and "network"
presumably distinguished FidoNet proper from other networks that might
use the same protocols.

(However, I'm not as familiar with FidoNet's protocols as I am with
the internet protocols, and so I might have gotten that wrong.)

A weakness with the message-ID approach is that it still scales only
linearly with the number of messages.  If you have a billion messages
comprising ten terabytes, each with a 20-byte message-ID, then an
IHAVE command for each message-ID will still cost 28 gigabytes of
network bandwidth in every conversation, even if only one or two new
messages are to be transmitted.  There are protocols involving more
round trips, such as ping-pong breadth-first trie traversal
and some approaches using compressed Golomb sets
or Bloom filters, that can
reduce this cost by a significant factor, but still only a linear
factor.

Evidently some way of naming large, coherent groups of messages is
needed if we are to get the desired superlinear speedup.

The per-publisher log approach
------------------------------

Kafka is a distributed modern publish-subscribe system used in
high-bandwidth data-center environments.  The way it works is that
each new message is apended to a log and assigned an ordinal sequence
number in that log; subscribers send requests not for individual
messages but for ranges of ordinal numbers in a given log.  Each
subscriber remembers the ordinal number of the last log message it has
seen on a given log, and when it loses a connection and reconnects, it
requests the next, say, 100 messages after that point.  This frees the
server from maintaining any persistent per-subscriber state, allowing
it to scale both to large numbers of messages per second and large
numbers of subscribers.

This protocol permits a subscriber to efficiently mirror the log, if
it wishes.  It can then provide the same subscriber interface to other
subscribers, as long as only the origin server is assigning new
ordinal numbers to new messages.  In fact, it can update its mirror
from other subscribers in the same way; it doesn't need to talk to the
origin server directly.  (Kafka itself doesn't take advantage of this
possibility, as far as I know.)

I think this is the way Secure Scuttlebutt works, as well.  Each
participant in the chat has their own append-only log of messages that
it has published, and upon conversing with a peer, it asks for updates
to the logs that it is a subscriber to.

Van Jacobson's "Content-Centric Networking" project (a generalization
of which is known as "Named Data Networking", or NDN) uses this
approach to handle streams of data.

In CCN, routing is done by naming pieces of data, not network nodes.
Each router remembers some set of interests associated with its
network links and some set of messages; it exchanges interests and
messages with its peers.  When it sees a message whose identifier
matches an interest it has pending, it forwards the message to the
router from which it got the interest, and if it receives an interest
that matches a message that it has stored, it replies to the interest
with a copy of the message.  In either of these cases, it forgets the
interest, since it has been satisfied.

On the other hand, if it receives a new interest that it cannot
satisfy, it remembers it and uses some algorithm to choose which
network links to forward the interest on to, perhaps related to which
network links it has received similar messages on before, or some kind
of hierarchical network addressing scheme and dynamically updated
routing table.  The interest being forwarded through the network
leaves a path of backpointers which give a route back to the original
requester, without that requester needing any kind of network address.

In this way, messages are only forwarded to routers that have
requested them, eliminating many opportunities for denial-of-service
attacks, and one copy of a message going into a router can evantually
result in many copies flowing out of it, as if the router were a
caching HTTP proxy, eliminating many other opportunities for denial of
service.

The obvious question is how to handle things like streaming voice and
video in a system like this: interests in data that doesn't yet exist.
The answer is simply that you assign sequence numbers to the frames of
streaming data ("ElRubius/videostream/d8s0g03402e/frame/3302") and the
subscribers send interests for some window of sequence numbers that
have not yet been produced, but which will be delivered to them when
they have.  As long as the window is large enough to compensate for
the latency of propagation of new interests, this will result in
immediate and efficient streaming.

This works out to be precisely the same per-publisher log protocol
used by Kafka for the analogous problem.  And in some sense the
`getblocks` message in the Bitcoin protocol does the same thing ---
but the "publisher" is the Satoshi consensus of the participating
nodes, so blocks might sometimes be superseded.

Cryptographic authentication of messages in the log is useful in some
cases to prevent one publisher from interfering with another.  In the
message-ID IHAVE/SENDME protocol this could be done simply by using
cryptographic hashes as message-IDs, as Git does, but in the
log-appending protocol, some different approach is needed; for
example, each new message in the log could be signed with a private
key associated with that log.  Such an approach will only be
successful, however, if the routing nodes in the system are checking
the signatures, which is a potential scalability bottleneck.

XXX how does Git's protocol actually work?  Originally it used rsync,
but not the rsync delta-transfer algorithm mentioned below.

This per-publisher-log protocol is only more efficient than the
per-message ID IHAVE/SENDME protocol as long as the set of publishers
remains small, which, admittedly, covers many important cases.  But if
each message has a new publisher, it reduces to the per-message-ID
algorithm.

Approaches based on rsync's delta-transfer algorithm
----------------------------------------------------

Rsync contains [a delta-transfer algorithm] designed to save bandwidth
over Australia's undersea cables.  Transmitting data to or from
Australia was very expensive, so if you had slightly different copies
of a file on opposite sides of the Pacific, it was important to find
the parts that were different and transmit only those.  If you have
both versions of the file on one side of the connection, you can use
the standard longest-common-subsequence ("LCS") dynamic-programming
algorithm to find the minimal edit sequence.  But how do you
efficiently compute a small edit sequence between two files, each of
which is only available to one of the parties in the protocol?

[a delta-transfer algorithm]: https://rsync.samba.org/tech_report/

The simplest approach is of course to divide the file into blocks of
some fixed size and use the message-ID approach, using the SHA-256 or
whatever of each block.  This would work well for files that are
modified by overwriting some part of the middle of the file; only the
modified parts will have a different SHA-256, and so only those
modified parts (plus the rest of the blocks containing them) will be
transmitted.

But if you insert a byte at the beginning of the file, shifting the
rest of the data in the file by one byte, none of your hashes will
match, and so the entire file will be transmitted even though the edit
distance was one byte.

The bupsplit algorithm used by Avery Pennarun's bup backup program,
and also the basis of Jumprope, attempts to overcome this problem by
breaking the file into blocks of variable sizes in a way that will
usually be consistent after insertions and deletions, similar to the
"fuzzy hashing" used in forensics.  (See file `immutable-filesystem`
for some related notes.)

The rsync algorithm takes a different approach.  One of the versions
of the file is broken into fixed-size blocks in the usual way,
typically using a block size of a few hundred bytes, and each block is
hashed with two different algorithms: a weak linear [rolling-checksum]
algorithm (in rsync, a modified version of Adler32) and a stronger
hashing algorithm --- originally rsync defaulted to MD4 for this,
which was cryptographically very weak, and even nowadays uses MD5,
which has also been broken.  The resulting collection of hashes (let's
call it a "digest", since the rsync papers don't give it a name) is
transmitted to the other participant, where the rolling checksum is
computed over *every length-N substring* of the other version of the
file; any matches found in the digest are checked with the strong
checksum.  This allows the relatively efficient and precise
computation of the byte-ranges of either file that are present at any
offset in the other, as long as the shared data is more than a block
in length.

[rolling-checksum]: https://en.wikipedia.org/wiki/Rolling_hash

It is interesting to note, as [Andrew Tridgell does in his
dissertation][0], that in some cases the rsync algorithm finds smaller
deltas than the LCS algorithm used by diff(1), because rsync can
detect and take advantage of transpositions, while LCS cannot.

The rsync algorithm is used not only in rsync but also in zsync,
rdiff, and some other software.  zsync in particular allows a
sender-server participant in the protocol to be nothing more than a
dumb HTTP server capable of byte-range access; this is achieved by
precomputing the digest and placing it in a "zsync file" on a web
server that points to the real file.  The zsync client, upon fetching
the digest file, can run the rolling checksum over its local version,
occasionally running the strong checksum, and compute the set of
byte-ranges that it needs to fetch from the origin server to
reconstruct the origin server's version of the file.

If you want to rsync a mebibyte of data using a block size of 4
kibibyte ([Tridgell's dissertation][0] discusses block-size tradeoffs
in chapter 3, finding optimal block sizes in the range of 256 bytes to
8 kibibytes for a few datasets), the digest to be transmitted will be
5 kibibytes, 0.5% of the total.

[0]: https://www.samba.org/~tridge/phd_thesis.pdf

Note, however, that this 0.5% doesn't decrease as the file size
increases, unless you also increase the block size.  If you were to
digest 10 tebibytes using 4-KiB blocks and 20-byte digest entries,
your digest would be 50 gibibytes.

As a simple intermediate step between the IHAVE/SENDME system and the
log-appending system, you could imagine using some variant of the
rsync protocol on a document containing the concatenation of all
messages in some well-defined order.  In effect, this assigns a
message-ID to each entire block of messages, rather than each
individual message.

A key difference from the usual use of rsync is that the receiver
don't want to delete messages that the sender doesn't have from their
own database; instead they want the union of all interesting messages.

For this to be efficient, you want the ordering chosen for the
messages to make the likely updates somewhat local, in the sense that
they leave large chunks of the file untouched.  For example, you could
order the messages in the file temporally, so that new messages are
usually added near the end, or by a combination between temporal order
and publisher ID, or a combination of temporal order and topic.

This approach also permits participants, in theory, to blacklist
certain known blocks to save space --- rather than storing a tebibyte
of uninteresting data (last year's Wikipedia edits, say), they can
just store its hashes and its sorting key range.  However, if new data
appears that belongs to that sorting key range, it would change the
hashes, making the simple blacklist approach fragile.

A potentially more interesting approach is to store the ranges of
sorting keys, or at least their longest common prefixes, in the digest
along with the hashes, permitting participants to choose which
subrange of the keyspace they bother to replicate.

### Recursive rsync delta transfer ###

Suppose that instead of using a single block size, we use several
different block sizes on the same file.  For example, we compute
digests for block sizes of 1 KiB, 1 MiB, 1 GiB, and 1 TiB.  If our
total dataset is 16 TiB, its 1-TiB-level digest might be 320 bytes
(assuming, for now, no sorting keys --- just treating the file as
opaque); a peer who fetches that digest can efficiently discover
whether it matches their local replica, or matches it except for a few
bytes inserted at the beginning.

But suppose they find that the last TiB-sized block in the 1-TiB-level
digest doesn't match any of the 17.59 trillion overlapping
tebibyte-sized blocks in their own replica.  Rather than sending a
network request or a purchase order to have that tebibyte of data
shipped to them, they can fetch the corresponding block of the
1-GiB-level index.  The entire 1-GiB-level index has 16384 entries,
but it's only interested in the last 1024 of them, totaling 20 KiB, to
discover whether any of the gibibytes comprising that tebibyte are
among the 17.59 trillion overlapping gibibytes in their existing
dataset.

Perhaps all but one of those gibibytes is a known gibibyte; in this
case it can recurse down to the mebibyte level, and then down to the
kibibyte level.

In this way, if anywhere from 1 to 1024 bytes have been inserted or
deleted in any single place in this 16-TiB dataset, our peer can
discover them by transfering 320 + 20480 + 20480 + 20480 + 1024 =
62784 bytes.  This is what rsync would report as a "speedup factor" of
about 280 million, although it's still worse than the theoretical
limit by a factor of between 61 and 62784.  Note that this is amenable
to zsync's digest-precomputation approach.

The overhead in the worst case is 20 parts in 1023, or 1.96%, the same
as nonrecursive rsync.  But there are important cases that should
admit these higher efficiencies.

Storing the file in such a way that this can be done quickly,
including a summary of the 70 trillion rolling hashes involved to
avoid needing eight passes over the 16-tebibyte dataset, and the
desire to keep a local "virtual copy" of the sending peer's dataset
(to avoid re-transferring blocks the next time around whose only sin
was that they lacked a message, rather than having new ones) seems
like it might be a challenging problem both in terms of algorithms and
in terms of systems design.  However, I think it's in some sense
straightforward; it doesn't require any novel inventions.

### Recursive rsync delta transfer applied to message bases and similar CRDTs ###

Suppose we have a nearly-16-TiB data store and we append one message
to it, a message of under 1024 bytes.  This can be synchronized with
the 62784 bytes mentioned above.  Once we bump past the 16-TiB line
things get even a bit better still: 340 + 20 + 20 + 20 + 1024 bytes,
since all the recursion levels except the top one only contain a
single hash.

This is considerably better than the 50 gibibytes required for
non-recursive rsync or the 28 gigabytes I suggested the IHAVE/SENDME
approach would need for a similar-sized base of messages (although
there I was postulating an average message size of 10 kilobytes).  But
it remains efficient if we have, say, a mebibyte of new messages to
sync.  If they're scattered in 1024 random places through the
16-tebibyte base, due to a poor choice of sorting keys, we need on the
order of 63 mebibytes of bandwidth to sync them, a 63x multiplier, but
several hundred times better than the other protocols.  If, instead,
they are gathered together more or less in one place, we need to
transfer 320 + 20480 + 20480 + 20480 + 1048576 = 1110336 bytes, an
overhead of about 6%.
