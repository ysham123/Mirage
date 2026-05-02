"""Framework integration adapters for Mirage.

The package holds thin adapters that route agent traffic through a
Mirage gateway. Each adapter imports its target framework lazily so the
core `mirage` install stays free of optional dependencies.
"""

from __future__ import annotations
