"""Mirage benchmark harness.

Reproducible scenarios run against a Mirage gateway in `enforce` mode.
Each scenario yields containment rate, false-positive rate, and
decision-latency percentiles. See `BENCHMARKS.md` for methodology.
"""

from __future__ import annotations
