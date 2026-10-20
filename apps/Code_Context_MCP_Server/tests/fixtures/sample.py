"""Fixture for the chunker tests. Line numbers are asserted in test_chunker.py."""

import functools


def add(a, b):
    return a + b


def greet(name):
    def shout(text):
        return text.upper()

    return shout(f"hello {name}")


class Counter:
    def __init__(self):
        self.n = 0

    @property
    def value(self):
        return self.n

    def bump(self):
        self.n += 1
        return self.n

    class Step:
        def size(self):
            return 1


@functools.cache
def square(x):
    return x * x
