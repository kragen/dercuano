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
