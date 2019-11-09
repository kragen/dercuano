I think it's possible to speed up raymarching with signed distance
fields enormously using affine arithmetic and possibly even interval
arithmetic.

Raymarching with signed distance fields
---------------------------------------

Raymarching with signed distance fields is a currently popular
computer graphics technique (in particular Inigo Quilez has achieved
visually amazing results, and perhaps as a result, the technique is
widely used throughout the demoscene) and is also the basis of
Christopher Olah's ImplicitCAD solid-modeling system.  The "signed
distance field" or "SDF" of an object is a function from points in 3-D
space to the Euclidean distance to the nearest point on the object's
surface, except that it's positive outside the object and negative
inside.  Since it's the distance from a point to the *nearest* point
on the object, it's a *lower bound* on the distance from that point to
*any* point on the object.

Constructing such a function is a very convenient and expressive way
to model a wide variety of geometry.

Raymarching successively approximates the intersection between a ray
and the object by advancing a point along the ray toward the object.
The SDF enables us to use a variant of raymarching called "sphere
tracing" in which the distance to advance is given by by the SDF at
that point.  This is guaranteed not to overshoot the intersection,
since the SDF gives a lower bound to the distance to that intersection
(as to any other point on the object), but if the intersection point
is not the nearest point on the object --- which it almost never is
--- the point will only move closer to the surface, not reach it.  If
the intersection is in a smooth part of the surface, each new point
will be closer to the surface by a factor of 1/sin(*&theta;*), where
*&theta;* is the angle the ray makes with the surface normal.

This is known as "linear convergence" and results in iteration counts
in the dozens to hundreds per ray in typical scenes.

Note that the above algorithm has no trouble with the case where the
SDF is actually an *overestimate* of the true surface distance, but
may fail if the SDF is an underestimate.  Conservative-estimate SDFs
are extremely useful for a variety of purposes.

Interval and affine arithmetic along the ray
--------------------------------------------

It occurred to me that interval and affine arithmetic could perhaps
speed up the process immensely.

The reason we can't just leap down the ray an arbitrarily long
distance and see if we're inside the object is that, if it's not thick
enough, we might leap right through it and out the other side,
eventually hitting some other part of the object or just the sky.  But
if we use interval arithmetic to evaluate the SDF over an interval of
the ray, rather than at a point, we can check to see whether that
interval includes zero --- that is, whether it is possible for the ray
to intersect the surface anywhere inside this interval.  This allows
us to test points on the other side of the surface without the risk of
missing intersections, which should allow us to reliably linearly
interpolate to find the zero of the SDF, effectively using the method
of secants with its *&phi;* degree of convergence rather than the
linear degree of convergence given by sphere tracing.

(Jorge Eliecer Florez Diaz wrote his dissertation, which I still
haven't managed to finish reading, on using interval arithmetic to
handle this case correctly for raytracing of implicit functions.  I'm
sure what's above is in there.)

By using affine arithmetic or reduced affine arithmetic instead of
simple interval arithmetic, we get an affine form which gives the SDF
value over the chosen interval of the ray as a linear function of the
position along the ray plus an error bound.  This allows us to find
all possible zeroes of the SDF reliably and probably much more quickly
than with just interval arithmetic, because the subinterval or
subintervals in which the SDF *might* have a zero will often be very
small compared to the original interval.

Interval and affine arithmetic on screen coordinates
----------------------------------------------------

Using interval values for the distance along the ray, as described
above, can be combined with using interval values for the position and
angle of the ray as well (a so-called "view frustum"), permitting in
many cases the computation of an affine expression for the color of a
part of the screen.  See file `reduced-affine-arithmetic-raytracer`
for more on this.

Gradients and surface normals
-----------------------------

Since surface normals are needed as input to lighting calculations, we
need some way to calculate them from the SDF; they are the gradient of
the SDF at the surface.  This is normally approximated by sampling the
SDF in octahedra or tetrahedra near the intersection point, choosing
the epsilon size comparable to the projected pixel size to attenuate
aliasing of surface bumps with pixel sampling.  But I think affine
arithmetic inherently calculates an approximation of the gradient,
which may be adequately precise for these purposes.  Moreover, unlike
automatic differentiation, the coefficients in the affine form
potentially pertain to an entire interval, not just a point.

Related work that I probably should have read by now
----------------------------------------------------

In addition to Florez Diaz's dissertation,
<https://www.shadertoy.com/view/lssSWH> is relevant, and maybe
"Interval Arithmetic and Recursive Subdivision for Implicit Functions
and Constructive Solid Geometry", Duff 1992.