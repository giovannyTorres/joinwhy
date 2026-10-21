# Local validation record — joinwhy 0.1.1

Recorded from completed local checks on 2026-10-21 (UTC).
These results are separate from GitHub CI and from public PyPI installation.

| Check | Observed result |
|---|---|
| Editable installation with development dependencies | Passed |
| Pytest and coverage threshold | Passed |
| Ruff lint | Passed |
| Ruff formatting | Passed |
| Mypy, src/ | Passed |
| Wheel and sdist build | Passed |
| Twine distribution metadata checks | Passed |
| Independent clean wheel and sdist installations and shipped examples | Passed |
| Benchmark execution | Passed |

**Tests:** 146 passed.
**Statement coverage:** 100.00% (141 of 141 measured statements; 5 excluded lines). This is not a branch-coverage claim.

Wheel and sdist were installed separately in fresh virtual environments with declared runtime dependencies.
The shipped examples ran with Python's `-I` flag, isolating imports from the repository checkout.
These installations used local distribution files, not a public-index upload.

## Recorded benchmark

Environment: python: `3.13.5`; pandas: `3.0.6`; platform: `Windows-11-10.0.26200-SP0`.

rows_per_frame: **100,000**; repeats: **5**; expected_rows: **233,334**.

Two synthetic frames contain 100,000 rows each, with left keys repeated twice and right keys repeated approximately three times. Before timing, the manual Pandas forecast and duplicate/unmatched key counts are asserted equal to joinwhy; the expected left join has 233,334 rows. Each workflow warms up once, followed by five perf_counter measurements. A separate untimed tracemalloc execution records traced peak allocation. The library additionally retains diagnostic key tables, checks whitespace/null rows and prepares a structured report; version 0.1.1 preserves exact source key values while counting public Pandas group IDs.

| Workflow | Median seconds | Minimum–maximum seconds | Peak traced bytes |
|---|---:|---:|---:|
| `manual_pandas` | 0.012102 | 0.011152–0.012633 | 5,035,320 |
| `joinwhy` | 0.563649 | 0.542325–0.577331 | 14,622,415 |

Timing without tracemalloc; memory separately measured. Library also constructs key inspection tables and diagnostics. No performance advantage is claimed.

The [raw measurement file](benchmarks/results.json) is the source of these numbers.
See [benchmark code](benchmarks/benchmark.py) and its documented methodology for workload details.
`tracemalloc` figures, when present, are traced allocations rather than process RSS.
No universal performance advantage follows from a single workload.

## Reproduce

```bash
python -m pip install -e ".[dev]"
python -m pytest --cov=joinwhy --cov-report=term-missing --cov-fail-under=95
python -m ruff check .
python -m ruff format --check .
python -m mypy src
python -m build
python -m twine check dist/*
python scripts/check_artifacts.py joinwhy
python benchmarks/benchmark.py
```

See [RELEASE.md](RELEASE.md) for publication status and the Trusted Publisher configuration.
