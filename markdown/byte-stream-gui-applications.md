How should we run graphical programs on machines remote from the GUI,
that is, remote from the machine the user is using?  This includes
scenarios such as the following:

1. DisplayLink-like USB-connected or Ethernet-connected monitors
   (whether for multiple monitors per user or multiple users of a
   larger machine, like X terminals);
2. Remote server administration;
3. Screen sharing for, for example, remote pair programming, remote
   demos, or visual aids for teleconference presentations;
4. Remote access to expensive shared computational resources, such as
   supercomputers (the original rationale for the ARPANet project);
5. Including GUIs in tiny embedded computers that don't have monitors
   of their own, but do have ports where you could connect monitors,
   touchscreens, keyboards, and mice;
6. Access to remote datasets, such as your email, although this
   very-thin-client approach is more demanding of the server.

Byte streams and pipes
----------------------

In some sense the lowest common denominator is bidirectional byte
streams with maybe some kind of escaping; this works over sockets,
RS-232 serial links (which can run at megabits per second nowadays ---
RS-422 and RS-485 can reach tens of megabits), and over `ssh` with
proper authentication.  So, on Unix, a very reasonable way to spawn a
graphical interactive app on a remote machine is to spawn an `ssh`
process connected to input, output, and error pipes, and then
select(2) or similar on those pipes to send events to the app and
receive commands from it.  Thus ssh can take care of authentication,
spawning processes on the remote host, checking them for errors
(although if there's an error you'll probably only get a textual
message back on stderr), and detecting when they die.

This also lets you run graphical apps on USB serial devices or other
embedded devices that just have a serial port.  It doesn't inherently
give you a way to run multiple graphical apps over a single serial
connection, so one serial device would be one app, and if that device
contains the display and keyboard and whatnot, it can only *display*
one app.  But that one app could be a full-fledged multiplexed display
server in its own right, spawning off ssh children and whatnot.

This all assumes the usual app interaction model, as I called it in
file `dehydrating-processes`, which suggests that for more flexible
kinds of interaction that aren't tied to particular hosts, a different
interaction model would probably work better.

ssh
---

I just did a quick experiment with OpenSSH:

    $ time ssh  -vC user@server dd if=/dev/zero bs=100M count=1 | dd bs=1k | wc -c
    ...
    debug1: Sending command: dd if=/dev/zero bs=100M count=1
    1+0 records in
    1+0 records out
    104857600 bytes (105 MB, 100 MiB) copied, 11.3868 s, 9.2 MB/s
    debug1: client_input_channel_req: channel 0 rtype exit-status reply 0
    debug1: client_input_channel_req: channel 0 rtype eow@openssh.com reply 0
    debug1: channel 0: free: client-session, nchannels 1
    debug1: fd 1 clearing O_NONBLOCK
    Transferred: sent 65224, received 341432 bytes, in 12.5 seconds
    Bytes per second: sent 5205.9, received 27251.5
    debug1: Exit status 0
    debug1: compress outgoing: raw data 28009, compressed 14245, factor 0.51
    debug1: compress incoming: raw data 104917069, compressed 229911, factor 0.00
    104857600
    102400+0 records in
    102400+0 records out
    104857600 bytes (105 MB) copied, 14.4017 s, 7.3 MB/s

    real    0m14.411s
    user    0m1.964s
    sys     0m4.108s

That is, ssh was happy enough to transmit me 100 megabytes of zero
bytes from the server in 14 seconds.

By comparison, running the command `true` produced this result:

    Transferred: sent 3352, received 2400 bytes, in 1.2 seconds
    Bytes per second: sent 2701.5, received 1934.3
    debug1: Exit status 0
    debug1: compress outgoing: raw data 154, compressed 135, factor 0.88
    debug1: compress incoming: raw data 566, compressed 538, factor 0.95
    0+0 records in
    0+0 records out
    0 bytes (0 B) copied, 3.09319 s, 0.0 kB/s
    0

    real    0m3.107s
    user    0m0.148s
    sys     0m0.004s

So the 100 megabytes only cost 11.3 seconds.  And, of that, 4 seconds
were spent in the kernel on my end, shuffling the bytes between the
processes, and 2 seconds were spent decompressing them.

Indeed, repeating the experiment using an ssh master connection
configured with `-o 'ControlMaster yes' -o 'ControlPath somepath'` and
an ssh slave connection configured with just the ControlPath, I got
11.2 seconds.  `true` took 400 ms or so.

This is not super great for video; this netbook's display is 1024x600
24bpp 60fps, which is 110.592 megabytes per second uncompressed, about
four times what the kernel is managing to copy through a pipe.  This
is why the draft Wercam protocol design in BubbleOS uses shared memory
(on Unix, with `mmap`, passed over sockets as open file descriptors).
But it's probably adequate, and if the data is encoded with some kind
of video codec, it might be totally fine.

Resynchronization and topology
------------------------------

X-Windows apps die if the display server dies or they lose their
connection to it.  This is very limiting.  Terminal apps connected
over a serial port, or GUI apps connected to a monitor or KVM switch,
don't have this problem; you can reconnect to them later, even
plugging in a different monitor, and keep using them.  GNU Screen and
tmux offer the ability to do this with terminal apps running on a
virtual terminal connected to via ssh, as well.

Making that kind of thing work well imposes some extra requirements on
the protocol design.  There are a few different cases where we might
need to resynchronize after some kind of protocol desynchronization.

First, you might want to recover from bugs in the application, the
display server, or the connection between them that caused
communication to break down --- an unescaped framing byte, say, or
noise on a serial line.

Second, in an embedded context, the application being displayed might
have crashed and restarted.

Third, the display and input devices might have been disconnected for
a while, and then reconnected, without having been able to see
anything in between.  Maybe it's a different display, or maybe it's
crashed and restarted or lost power in the interim.

Fourth, you might want to have multiple displays and input devices
connected to the same running application at the same time.  If all,
or all but one, but one of the input devices are disabled, this is
straightforward ("live streaming"); otherwise you need some way to
keep the input devices from screwing up the framing when they try to
talk at the same time, and somehow negotiate the window size.

Fifth, you might want to record and replay a video stream
("screencasting").

These can all be handled to one extent or another by adaptors of some
kind spliced into the protocol, rather than by the protocol design.
That may or may not be the best way to solve the problem.  For
example, live streaming benefits from adaptors to adapt to the
available bit rate.

Codecs
------

The standard VNC RFB protocol uses only lossless "video codecs", and
they are not very efficient.  XPra uses modern lossy video codecs in
order to get dramatically better efficiency at the cost of a little
latency.  Specifically, its non-deprecated codecs are rgb (compressed
with zlib, lzo, or lz4), png, VP8/VP9 ("vpx"), and H.264.

Video codecs have an interesting feature: they are often also video
container formats that are designed for broadcasting over the
airwaves.  Broadcast formats have to be unidirectional and permit
synchronization in the middle of the stream, so that turn your digital
TV on or change channels, you start seeing the video on the channel
you're receiving.  You can start reading the stream at any point, and
pretty soon you'll manage to synchronize with the framing, and then an
I frame (internally coded, a lossily compressed image without any
reference to other frames), and then you're displaying video.

Any video stream format that allows this pretty much automatically
gives you items #1 through #5 above, except when it comes to handling
of input events, including things like window size changes.

Traditional "video stream formats" filling this role include NTSC,
PAL, SECAM, VGA signals, and ASCII text for teletypes and video
terminals.  These are optimized for displays with very little memory.
NTSC needs to remember where you are relative to the the horizontal
and vertical sync and the colorburst, and PAL has some additional
slight twist.  VGA is the same but without the colorburst.  Teletypes
only need to remember where they are on the line and the currently
printing byte, if any; video terminals have 2K or 4K of RAM for the
screen contents, or maybe a bit more.

I think it's okay for the protocol to require displays made of modern
electronics to have more memory than that, 8 to 32 bytes per pixel,
say.

Bidirectionally predicted frames (B frames) are potentially more of a
problem.  Their mere existence imposes potentially unacceptable codec
latency, but if your remote app is a video player, you're going to
have substantial bandwidth inflation if the video streaming protocol
doesn't support B frames.

Supporting multiple codecs and demanding that the stream be readable
without any kind of codec negotiation allows applications to be very
simple but potentially requires a lot of complexity on the display
side.  As a very crude estimate, a single modern codec is on the order
of a meg of code:

    $ ls -lL /usr/lib/i386-linux-gnu/libx264.so.142
    -rw-r--r-- 1 root root 976296 Mar 23  2014 /usr/lib/i386-linux-gnu/libx264.so.142

But maybe it's possible to get the requisite compression of 4 to 8
with a much simpler codec, something like MPEG-1, but maybe more
modern.

Input events
------------

The main requirement for input event handling is that they need to get
delivered even if one or both of the app and the display crash and
restart, or if the user reconnects using a different terminal.  There
are a lot of ways to do this; the simplest one is to send all possible
input events all the time rather than attempting to economize in any
way.  At least without cameras, the total input event data can't be
more than a tiny fraction of the video data torrent rushing the
opposite way; this probably makes it insignificant, although there do
exist unusual scenarios with very asymmetric bandwidths, such as some
satellite communications.  Other possibilities include resynchronizing
the input state (shift keys, etc.) whenever a reconnection is detected
or suspected.

You also need to send the window size if the app is sending video of
the wrong window size, and maybe when it's sending no video, too.

GUI apps on embedded microcontrollers
-------------------------------------

You probably don't want to have to include an H.264 encoder in your
Arduino; you probably want to support some kind of simpler protocol
than H.264, maybe something uncompressed; for example, a sequence of
nothing but "P frames" that consist of local area updates, some of
which are actual updates and others of which are redundant
retransmissions of unchanged scan lines.  At some point you might want
to add reduced-color-depth pixels to the protocol, but [even Arduino
serial ports can run at 2
Mbps](https://arduino.stackexchange.com/questions/296/how-high-of-a-baud-rate-can-i-go-without-errors)
(83 kilopixels per second at 24 bits per pixel) and if you're
transmitting via `ssh -C` you'll get paletting implicitly from
Lempel-Ziv compression, so lower color depths are never going to be a
big win.

And you don't need text in the protocol.  In
[dofonts-1k](http://canonical.org/~kragen/sw/netbook-misc/dofonts-1k.html)
I included a full printable-ASCII 6x8 font in 64x36 bits, 288 bytes
uncompressed, or 482 bytes PNG-compressed and base64ed.  It's
reproduced below.  The file, 1KiB in all, also includes a sort of
terminal emulator that uses the font to render ASCII text on a
`<canvas>` which is 20 lines of JS code, including lines of code that
just say `}`.  You have room for that in your Arduino's Flash.

<img src="data:image/png;base64,
iVBORw0KGgoAAAANSUhEUgAAAEAAAAAkAQMAAAADwq7RAAAAAXNSR0IArs4c6QAAAAZQTFRFAAAA
////pdmf3QAAAQxJREFUGNMtjlFqg0AYhIcQikhJryBFgoiHWGQR2QfJIaQPfegZRCQEkZxBZCny
I9sr+LBIkZBDBPFBQs7QNXTgh2Hg+2ewpZh7Ehtsf26S89XYmvHHbgu8ebVJLJPcDlyyGACDhwzg
ifpK4VTomjYnnoSY3LuOkLmQ4XvbIGFI7kF84U6Bpyxzqb7Oyi9dELUn6Z8J6rcbp+C8oKS2lFQS
PvX1qMTyT63Sw0I0VwzUCiK3qDFqobhZhrIRD1m4QNElQs4BzPyndmCZ4xReD+yHNOptoWG3tHRB
QsZ0kfQF4WX4CJW/yJV4Rf8kmfkRHzB8m9KJ16CLIBFEwJgLFa2lx2ovmsmYfMU2Fv4AgeVrl8Qw
sFoAAAAASUVORK5CYII=
" />

83 kilopixels per second means that a full-screen redraw at 1024x600
would take 7.4 seconds, and if you're using the Arduino Serial
library, more like 30 seconds.  Even if you had only one bit per
pixel, it would still take over a second.  There are applications that
update the screen regularly for which this kind of latency is
acceptable, but having the screen partially redrawn all the time is
not.  Double-buffering is the usual solution, and it's within the
8-32-byte-per-pixel budget described above.  But how should we do it?

The basic atom of the Arduino protocol described above is something
like draw(x, y, w, h, pixeldata), where typically wxh is on the order
of 64 to 256 (about a millisecond at the data rates discussed above).
The simplest approach to double-buffering is to add a flip() operation
that makes all the previous changes visible.  An alternative would be
to include some kind of timestamp in the draw() operation that
specifies when to make it visible, perhaps a one-byte number of
intervening draw() messages to delay the draw operation.

The (x, y, w, h, delay) header might be 7 or 8 bytes, so prepended to
a 192-byte 64-pixel data block, it amounts to about 4% overhead, which
seems acceptable.

A more stateful protocol might handle double-buffering by including
offscreen pixmaps and commands to copy regions between them, but that
poses risks to resynchronization after disconnects.

BubbleOS thoughts
-----------------

This also suggests a different way to write and run BubbleOS Yeso
programs, particularly on Linux: put the code for interfacing with,
for example, X-Windows or the framebuffer, into a process which runs
the app as a subprocess.  The app itself reads input events on stdin
and writes a video stream on stdout; when the app exits, the parent
process detects this and also exits.  Then a window-managing shell
running multiple apps as subprocesses would just be one more app you
could run in this way.

I have some vague memories of worrying that if raw framebuffer
programs crash I might have to reboot to regain control of the
machine, although I don't remember if this has to do with changing
keyboard modes or video modes or stty or what.  Running them as
subprocesses this way would permit the (hopefully more reliable)
parent process to clean up properly.

This would also make it straightforward to do things like run multiple
programs successively in a window, run an image output filter over the
output of a program (e.g., Dark Mode, magnify, overlay ripples around
mouse clicks, or some kind of pause/rewind thing), or write graphical
programs in whatever random language that can spit out bytes.

Unfortunately, though, performance.  As explained above, Linux charges
too many computrons for moving pixels between processes in pipes.  The
Intranin design for IPC by transferring ownership of memory segments
between processes would enable these things to be done efficiently.

For environments with a low screen update rate, such as e-ink
displays, the efficiency concerns disappear.
