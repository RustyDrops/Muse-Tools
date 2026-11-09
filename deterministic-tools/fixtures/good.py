"""Sample module for toolbox fixtures (hand-written, tiny)."""

import os


class Greeter:
    """Greets people politely.

    Longer second line that outline must not include.
    """

    def __init__(self, name="world"):
        self.name = name

    def hello(self, loud=False):
        """Say hello.

        Details omitted.
        """
        return "hi " + self.name


def add(a, b=2):
    """Add two numbers."""
    return a + b


# a trailing comment that strip must drop
