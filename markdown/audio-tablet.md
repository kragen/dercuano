Today I was talking with David Christensen about a project of his, and
I had some ideas about tracking styluses on drawing tablets using
ultrasound.  In his project, which is not a drawing tablet, they're
tracking a point of contact on a surface using an array of
piezoelectric contact microphones on the back of the surface, using
the relative intensity of the conducted sound at different microphones
to estimate the location.

It occurred to me that by cross-correlating the signals at the
different microphones, you can do a much better job of localizing the
sound, and this could be useful for an inexpensive large-area drawing
tablet.  (This is related to file `string-instrument-servo`.)

A stylus scratching on a rough surface such as paper or MDF produces
broad-spectrum noise, and broad-spectrum noise is wonderful at having
very low autocorrelation at any shift other than zero; it's very
nearly orthogonal to itself at other shifts.

Echoes from the edges of the tablet can set up Chladni-plate-like
standing waves, which could complicate the situation substantially
(like some stupid Hollywood action movie that ends in a hall of
mirrors) so using a highly attenuating material like leather might be
a good idea, or perhaps cutting the edges of the material in a
sunburst-like zigzag pattern so that the high frequencies we want are
strongly attenuated and their coherence destroyed as they reflect from
the edge.  (This is related to the Q of acoustic resonators such as
music-box tines cut from the material, although I don't know if we can
talk about an acoustic Q of the material itself; but clearly for this
purpose MDF is dramatically superior to plastics, which are
dramatically superior to metals, which are mostly somewhat superior to
ceramics.)

With only two microphones you would have an ambiguity about which side
of the line through them the stylus is on (whose importance could be
minimized by putting them along the same edge of the tablet); three
microphones would avoid this problem, and more than three microphones
would help to reduce errors and latency further.  Latency of under 10
milliseconds is critical for musical use and strongly desirable for
drawing; anything over 1 millisecond is detectable and undesirable.

The localization precision and interaction latency are both limited by
the speed of sound in the material, but unfortunately in opposite
directions: a higher speed of sound means less interaction latency but
lower precision.  Using higher frequencies alleviates this problem.
Suppose you have three microphones in an equilateral triangle one
meter on a side; the center is 661 mm from the corners, and that's as
far as you can get from the corners inside the triangle or indeed
anywhere near it.  With a speed of sound of 2000 m/s, a reasonable
estimate for many solids, that works out to an intrinsic acoustic
latency of 331 microseconds, not counting processing time.  If there
are significant 10-kHz components of the noise being tracked, they
will narrow the autocorrelation peak to around 100 microseconds ---
but at 2km/s, that's 200 mm of position uncertainty!  That's no good
for drawing, which needs submillimeter precision.  A lower speed of
sound would reduce the positional uncertainty proportionally.

However, correlation and intensity aren't the only sources of
information we have.  Solids actually carry two different kinds of
sound, longitudinal and transverse, and transverse waves are slower
and have polarization.  If the microphones are able to detect the
direction of vibration, for example by coupling them to points on the
board through taut UHMWPE or glass-fiber threads near tangent to the
board, they will first detect the longitudinal waves moving the board
towards and away from the point of contact, then later the transverse
waves moving it in some direction normal to the vector towards the
pencil.

This still depends on getting substantial phase separation of the two
waves --- I haven't measured yet but I think they'll tend to be
strongly correlated, though perhaps longitudinal impulses going in one
direction will be strongly associated with transverse impulses
propagating at right angles to it.

Raising the frequency would help a lot, but you need to raise it by a
factor of 500 or so, to about 5 MHz.  It may be the case that pencils
scraping on paper or MDF intrinsically produce 5-MHz noise, but I
doubt it.  5-MHz ultrasound doesn't travel very far in air, but it has
no difficulty with most solids and liquids.  You could attach a small
sound transmitter to the pencil that transmits a 10Mbps LFSR signal,
which would be transmitted to the board whenever the pencil was
touching it.  (Or touching paper taped to it.)  You could transmit
this signal intermittently --- a 40-bit burst, taking 4 microseconds,
every 100 microseconds or more, would be adequate.

Alternatively you could couple ultrasonic vibrations into the board
from a piezoelectric, magnetostrictive, or electromagnetic actuator
mounted on the back of it and see how they scatter; this might be
adequate but would probably work better for large, hard contact points
than for a pencil point.  Or, as described for the one-dimensional
case in file `string-instrument-servo`, you could attach the detector
to the stylus (or the person's finger) and pick up vibrations injected
into the surface.

Periodicity in the sound injected would be problematic, since the
autocorrelation of periodic waveforms has many peaks, creating
ambiguity about the stylus position.  It's easy enough to avoid with
an LFSR in the electronic case, but for acoustically produced sounds
there is the risk of resonances.

Vibration transducers attached to the board could also, at
sub-kilohertz frequencies, provide haptic feedback like the
piezoelectric click pioneered by Nokia for some of their cellphones
years ago; and if the tablet is horizontal and isn't very well damped
at the edges, they could also make Chladni figures to move small
objects around on it, also a technique demonstrated some years ago by
a research group using a single actuator to vibrate a metal plate.
