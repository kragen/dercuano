Transmitting low-power TV signals around your house via RF modulation with an SDR 
=================================================================================

Suppose you want a multi-monitor setup.  As [Elda King points
out](https://mastodon.social/@eldaking/103236501885892061) your
monitors are more convenient to use if they're wireless, and perhaps
more trustworthy (and certainly lower latency) if they have no RAM.
Fortunately, there's a device that already exists with these
attributes: the analog TV.  They are currently being discarded in
enormous numbers.

What would it take to use many analog TVs as prosthetic wireless
monitors for your computer system?  Merely an RF modulator, ideally on
unused TV channels, and an antenna that's just strong enough to reach
across the room.  If it uses near-field transmission it might be able
to be even more local and more efficient than the inverse-square law
would suggest.  RF modulators for VHF channels 3 and 4 were common
home-computer accessories around 1980, but using cables rather than
antennas to connect to the TV.

You don't get a whole lot of resolution with the analog TV standards:
NTSC is 525 lines, while PAL and SECAM are 625 lines, with 4:3 aspect
ratios --- 700x525 or 833x625 in theory if you use square pels, but
some of that is lost to overscan, the HBI and VBI.  The 625-line
resolution has a 49-line VBI, so you only get 576 lines on the screen,
or 768x576 if you use square pels; NTSC has only 486 visible lines out
of its 525, or 648x486 with square pels.  And because this is
*interlaced*, one-pixel-thick letters can be hard to read as they
flicker at 25 or 30 Hz.  Analog HDTV never hit the mass market
anywhere but Japan, so if you want higher resolution, you need to
transmit DVB.

Still, if you're transmitting many frequencies at once, you can run
many TVs at once.

NTSC is amplitude-modulated, which is why snow is such a problem, and
the whole signal is 6 MHz wide.  The VHF channels are in the 30 to 300
MHz "VHF" band, while the UHF channels are in the 300 MHz to 3 GHz
"UHF" band.  In [North
America](https://en.wikipedia.org/wiki/Band_I#North_America), channels
2 to 6 occupy 54 to 88 MHz, 6 MHz each, while [channels 7 to 13 occupy
174 to 216 MHz](https://en.wikipedia.org/wiki/Band_III#North_America),
again 6 MHz each, while
[UHF](https://en.wikipedia.org/wiki/Ultra_High_Frequency) channels 52
to 69 occupied 698 MHz to 806 MHz until 2009, channels 14 to 20
occupied 470 to 512 MHz, channels 21 to 36 occupied 512 to 608 MHz,
channel 37 was reserved for mostly radio astronomy, and channels 38 to
51 occupy 614 to 698 MHz until 2020; unlicensed devices are officially
permitted in the 652-663 MHz range, including part of channels 44 and
46, and all of channel 45.  Until 1983, 806 MHz to 890 MHz was UHF
channels 70 to 83, so older TVs might be able to receive those, too.

Aside from channel 45, probably any transmission on these frequencies
is illegal in the US unless you do it inside a Faraday cage.

The bandplan here in Argentina is presumably different, but harder to
get information on.

A quarter-wave monopole antenna at 806 MHz would be 93 mm, so
efficient antennas are compact and easy to build, and the "far field"
might be the other side of the room.  UHF frequencies transmit almost
entirely by line of sight and are even substantially attenuated by
building walls.  The VHF frequencies, below 300 MHz, have much better
wall penetration and can take advantage of ground bounce; at the lower
extreme of 54 MHz, a quarter-wave monopole is 1.39 m long, which is
inconveniently large, but by the same token, near-field communication
can extend out several meters --- the [Fraunhofer
distance](https://en.wikipedia.org/wiki/Fraunhofer_distance) 2D²/λ for
a 2-m antenna would be 1.44 m, and a 4-meter loop antenna might be
practical, as discussed in file `bitbang-am-radio`, which would give
you a near-field range of almost 6 meters.

You only get about a third of a megapixel per TV channel, so you need
at least three channels, 18 MHz of bandwidth, to get a megapixel, and
thus at least 36 Msps, better 50 Msps.  The USRP N200 and N210, like
the USRP2 before them, have dual DACs running at 400 Msps.  So they
should easily be able to handle that DAC demand if you can compute the
waveform; indeed, at the DAC level at least, they should be able to
transmit on 66 contiguous NTSC TV channels at once, covering the
entire UHF TV band!

Of course it would be foolish to attempt to transmit a signal in this
way that you wanted to maintain confidential, since your neighbors can
probably tune in to it.

[Vladislav Fomitchev KM4VTH demonstrated this more or less working in
2018](https://youtu.be/z8DMFo4atnM) using GNU Radio, a HackRF One
(US$600 in Argentina), and a signal flow graph he constructed, and
[marble has demonstrated doing something similar with GNU Radio, a
HackRF One and
PAL](https://hackaday.io/project/14904-analog-tv-broadcast-of-the-new-age).
[Argilo has published a flow graph for transmitting ATSC on 438 MHz
with GNU Radio and a BladeRF](https://github.com/argilo/sdr-examples);
the BladeRF has 61.44 MHz sampling and 2x2 MIMO and costs US$420 from
SparkFun but isn't available in Argentina.
