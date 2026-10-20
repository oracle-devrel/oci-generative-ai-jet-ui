// Fixture for the chunker tests. Line numbers are asserted in test_chunker.py.

function add(a, b) {
  return a + b;
}

function* count(n) {
  for (let i = 0; i < n; i++) yield i;
}

export class Counter {
  constructor() {
    this.n = 0;
  }

  bump() {
    this.n += 1;
    return this.n;
  }
}

const square = (x) => {
  return x * x;
};

export default function main() {
  return add(1, 2);
}
