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

CCN message IDs

FidoNet message-IDs: (network, zone, region, board, sub, message)