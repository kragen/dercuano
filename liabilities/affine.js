// Simple affine arithmetic in JS.

let newAffineIndex = (() => {
  let affineIndex = 0;
  return () => affineIndex++;
})();
let affineRange = (a, b) => affine(a + (b-a)/2, {[newAffineIndex()]: (b-a)/2});

let subscriptDigits = {
  '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
  '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
  '-': '₋' };

let subscript = n => (''+n).replace(/\d/g, d => subscriptDigits[d] || d);
let asAffine = n => typeof n === 'number' ? affine(n, {}) : n;

let affine = (k, a) => {
  return {
    k: k,
    a: a,

    toString: () => {
      const terms = [k];
      for (let i in a) {
        terms.push(` + ${a[i]}ε${subscript(i)}`);
      }
      return terms.join('');
    },

    add: other => {
      const o = asAffine(other);
      const na = {};
      for (let i in a) {
        const oai = o.a[i];
        na[i] = oai === undefined ? a[i] : a[i] + oai;
      }
      for (let i in o.a) {
        if (na[i] === undefined) na[i] = o.a[i];
      }

      // As far as I know there is no way to set the rounding mode in
      // JS, so we’ll just ignore rounding error for now.

      return affine(k + o.k, na);
    },

    mul: other => {
      const o = asAffine(other);
      return affine(k * o.k, 'XXX');
    },
  };
};

/*
 * So, how is multiplication supposed to work?  If we have (k1 + a11 e1
   + a12 e2)(k2 + a21 e1 + a22 e2), it multiplies out to k1 k2 + k1
   a21 e1 + k1 a22 e2 + k2 a11 e1 + a11 a21 e1^2 + a11 a22 e1 e2 + k2
   a12 e2 + a12 a21 e1 e2 + a12 a22 e2^2.  Gathering the coefficients
   of like terms, this gives us k1 k2 + (k1 a21 + k2 a11) e1 + (k1 a22
   + k2 a12) e2 + a11 a21 e1^2 + a12 a22 e2^2 + (a11 a22 + a12 a21) e1
   e2.  The first three — the ones that come from one of the constant
   offsets — are pretty straightforward; they introduce no new terms.
   The quadratic terms are interesting because they are in the [0, 1]
   range, so they generate an additional constant offset, (a11 a21 +
   a12 a22)/2, and a new error variable with that as its coefficient.
   The other term, the e1 e2 term, can be in [-1, 1], so its
   coefficient doesn’t get halved and it doesn’t generate a constant
   offset.  We can, however, lump it together with the halved ones
   into a new term e3.  So the final result is

   k1 k2 + ½ a11 a21 + ½ a12 a22
   + (k1 a21 + k2 a11) e1
   + (k1 a22 + k2 a12) e2
   + (½ |a11 a21| + ½ |a12 a22| + |a11 a22| + |a12 a21|) e3.

   If we visualize this as a function of the matrix that is the outer
   product of the two vectors, the constant comes from the diagonal,
   with a ½ multiplier for the squared epsilons; the rest of the first
   row and the first column give us our coefficients for the existing
   epsilons; and the “interior”, all the other rows and columns
   (including the diagonal, which gets halved) give us the terms of
   the coefficient for the newly introduced epsilon.  We can’t assume
   that these terms are correlated with each other — since they come
   variously from e1^2, e2^2, and e1 e2, and in a larger system would
   come from a larger collection of epsilon pairs, the departures from
   linearity they represent might all have the same sign even if the
   terms have different signs — so we have to use their absolute
   values rather than their signed sum to get the new coefficient.

   Gamito and Maddock omit all this special-case stuff for squared
   error symbols, so I should be careful to verify that I’m not making
   a reasoning error.

 */