# Local validation record — 0.1.0

Verified on 2026-10-21 using Python **3.13.5**, Pandas **3.0.6**, and Windows 11.
These are local execution results. GitHub CI runs and PyPI publication have separate status;
this record does not assert success on another operating system or Python version.

| Check | Observed result |
|---|---|
| Editable installation with development dependencies | Passed |
| Pytest | **95 passed** |
| Statement coverage | **100%**, 136 of 136 measured statements; 5 excluded lines |
| Ruff lint | Passed |
| Ruff formatting | Passed |
| Mypy, `src/` | Passed |
| Wheel and sdist build | Passed |
| Twine distribution metadata checks | Passed for both artifacts |
| Clean wheel installation and shipped example | Passed in a fresh isolated virtual environment |
| Clean sdist installation and shipped example | Passed in a second fresh isolated virtual environment |
| Benchmark reference assertions and measurements | Passed |

Coverage is statement coverage; no branch-coverage percentage was measured. The suite
includes generated comparisons against actual Pandas joins, composite and null keys,
empty frames, relationship and expansion constraints, and a 100,000-row case.

The installation checks use local `dist/joinwhy-0.1.0-py3-none-any.whl` and
`dist/joinwhy-0.1.0.tar.gz`. Each artifact is installed independently with its declared
runtime dependencies. Examples run with Python's `-I` flag, and the imported module path
is verified by the log to be in the fresh environment's `site-packages`.
These checks do **not** constitute an installation from the public PyPI index.

## Recorded benchmark

The [raw measurement file](benchmarks/results.json) records five timed repetitions after
one warmup for each workflow on two synthetic frames of 100,000 rows each. Both workflows
forecast **233,334** output rows and agree on duplicate and unmatched-key counts.
The manual reference uses Pandas grouping and key-count alignment without materializing
the joined payload. The library additionally constructs inspection tables and diagnostics.

| Workflow | Median seconds | Minimum–maximum seconds | Peak traced bytes |
|---|---:|---:|---:|
| Manual Pandas counts and checks | 0.011917 | 0.011251–0.013430 | 5,036,152 |
| `joinwhy.audit` | 0.203938 | 0.183513–0.234503 | 14,617,840 |

Memory comes from a separate execution under `tracemalloc`; it excludes untraced native
allocations and is not process RSS. Timings exclude `tracemalloc`. The library is slower
on this workload; no performance advantage or general speed guarantee is claimed.
See the [benchmark methodology](benchmarks/README.md) and executable
[benchmark](benchmarks/benchmark.py).

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
python benchmarks/benchmark.py --rows 100000 --repeat 5
```

CI is configured to exercise Python 3.11–3.14 and the Pandas 2.2.3 compatibility floor.
**PyPI: NOT PUBLISHED** until the first upload and public-index installation are verified;
see [RELEASE.md](RELEASE.md) for the required publisher configuration and confirmation.
