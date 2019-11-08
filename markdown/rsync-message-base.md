I was discussing eventual content synchronization for disconnected
operation through eventually-consistent data stores for
computer-mediated communication systems with an entity known as The
Doctor, and they suggested the use of the rsync algorithm and its
variants, which I thought was really interesting.

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
requested its transmission, if possible.

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
round trips, such as ping-pong breadth-first trie traversal, that can
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
the latency of propagation of new in

This works out to be precisely the same per-publisher log protocol
used by Kafka.