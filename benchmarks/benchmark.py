"""Reproduce timings: python benchmarks/benchmark.py --rows 100000 --repeat 5.

Both implementations predict size, uniqueness and unmatched keys, without
materializing joined payloads. The library also checks whitespace/nulls,
returns inspection tables, and explains results. tracemalloc captures traced
Python allocations, not total RSS or all native NumPy allocations.
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import time
import tracemalloc
from collections.abc import Callable
from pathlib import Path

import pandas as pd

from joinwhy import audit


def manual(left: pd.DataFrame, right: pd.DataFrame) -> dict[str, int]:
    """Straightforward pandas-only analyst workflow used as reference."""
    lc = left.groupby("key", dropna=False).size().rename("l")
    rc = right.groupby("key", dropna=False).size().rename("r")
    counts = pd.concat([lc, rc], axis=1).fillna(0)
    return {
        "expected_rows": int((counts["l"] * counts["r"].clip(lower=1)).sum()),
        "left_duplicate_keys": int((lc > 1).sum()),
        "right_duplicate_keys": int((rc > 1).sum()),
        "left_unmatched_keys": int((counts["r"] == 0).sum()),
        "right_unmatched_keys": int((counts["l"] == 0).sum()),
    }


def measure(operation: Callable[[], object], repeat: int) -> dict[str, object]:
    operation()  # Warm up imports, allocators and pandas machinery.
    durations = []
    for _ in range(repeat):
        start = time.perf_counter()
        operation()
        durations.append(time.perf_counter() - start)
    tracemalloc.start()
    operation()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "seconds": durations,
        "median_seconds": statistics.median(durations),
        "min_seconds": min(durations),
        "max_seconds": max(durations),
        "traced_peak_bytes": peak,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=100_000)
    parser.add_argument("--repeat", type=int, default=5)
    parser.add_argument("--output", type=Path, default=Path("benchmarks/results.json"))
    args = parser.parse_args()
    if args.rows < 10 or args.repeat < 2:
        parser.error("rows must be >=10 and repeat >=2")
    left = pd.DataFrame({"key": [i % (args.rows // 2) for i in range(args.rows)]})
    right = pd.DataFrame({"key": [i % (args.rows // 3) for i in range(args.rows)]})
    reference = manual(left, right)
    result = audit(left, right, "key").to_dict()
    assert all(result[key] == value for key, value in reference.items())
    report = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "pandas": pd.__version__,
        "rows_per_frame": args.rows,
        "repeats": args.repeat,
        "expected_rows": result["expected_rows"],
        "manual_pandas": measure(lambda: manual(left, right), args.repeat),
        "joinwhy": measure(lambda: audit(left, right, "key"), args.repeat),
        "notes": "Timing without tracemalloc; memory separately measured. Library also constructs key inspection tables and diagnostics. No performance advantage is claimed.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
