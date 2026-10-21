# joinwhy

Explain a Pandas join before it allocates joined payloads. Detect duplicate and
unmatched keys, report null and whitespace issues, forecast exact output rows,
and enforce relationship and expansion constraints.

```python
import pandas as pd
import joinwhy

customers = pd.DataFrame({"id": [1, 2, 3]})
orders = pd.DataFrame({"id": [1, 1, 3], "amount": [10, 20, 15]})
report = joinwhy.audit(customers, orders, on="id", how="left")
assert report.expected_rows == 4
print(report.explain())
result = joinwhy.safe_merge(customers, orders, on="id", relationship="one_to_many", max_expansion=2)
```

## Installation

Requires Python 3.11+ and Pandas 2.2+. The initial release is being prepared;
until a PyPI release is verified, install from a checkout:

```bash
python -m pip install .
# After the first PyPI release:
python -m pip install joinwhy
```

The library has no runtime service, telemetry or dependency on the other projects.

## API

| API | Behavior |
|---|---|
| `audit(left, right, on, how="left")` | Build an `AuditReport` for `inner`, `left`, `right` or `outer` |
| `safe_merge(..., relationship=None, max_expansion=None)` | Audit and check constraints before merging |
| `report.explain()` | Human-readable diagnostics |
| `report.to_dict()` | JSON-compatible summary |
| `report.problematic_keys()` | Duplicate, unmatched, null or whitespace key tuples and counts |
| `report.unmatched_keys(side="both")` | Keys absent from the opposite side; `left`, `right`, or `both` |

`on` accepts a string or sequence of strings for composite keys. Relationship
values are `one_to_one`, `one_to_many`, `many_to_one`, `many_to_many`. These are
constraints, so one-to-one inputs also satisfy one-to-many. Uniqueness considers
all input keys, including unmatched keys, consistent with Pandas validation.
`JoinConstraintError` rejects violated constraints. `JoinAuditError` reports
invalid configuration or key types Pandas cannot align. Invalid frame objects
raise `TypeError`.

Inspection frames contain `key` tuples (components follow `report.keys`),
`left_count`, `right_count`, `null_key`, and `whitespace`. Each call returns a
fresh frame. Reports retain a snapshot of counts, not references to input frames.
`left_duplicate_keys` counts distinct keys occurring more than once, not excess rows.

`safe_merge` forwards `suffixes`, `sort` and `indicator` only. It never normalizes
identifiers or fills nulls. Output ordering and columns follow Pandas merge.

## Semantics and use cases

Use joinwhy to catch invoice multiplication, identify customer IDs lost during
enrichment, investigate composite-key joins, and stop an ETL join above a known
memory budget. Forecasts group observed keys and align the compact frequency
tables; they do not allocate the potentially much larger result.

For key counts L and R, matching keys contribute L×R. Unmatched keys contribute
L for left/outer, R for right/outer, and zero for inner. Python integer totals
avoid integer overflow. Pandas null keys match other null keys, including
corresponding null components of composite keys. This differs from typical SQL
and from Polars' default; the report states this policy explicitly.

Expansion is `expected_rows / left_rows`, including for right and outer joins.
For an empty left input it is zero if output is empty, otherwise infinity.
`to_dict()` serializes infinity as `None`; `max_expansion` must be finite and
nonnegative. Constraints are evaluated before the actual payload merge.

## Existing tools and limitations

Pandas already offers `validate`, `indicator`, grouping and merging. joinwhy
assembles their diagnostic intent into a reusable report and adds an output-size
guardrail. It does not replace Pandas. See [RESEARCH.md](RESEARCH.md) for the
comparison with [joinspy](https://github.com/gcol33/joinspy) and
[powerjoin](https://github.com/moodymudskipper/powerjoin), the R inspiration.

Version 0.1.0 supports Pandas equality joins on same-named, uniquely labeled
string columns. No index joins, cross/as-of/fuzzy joins, Polars adapter, automatic
repair, case-normalization guesses or post-join lineage are provided. Hashable
scalar or tuple key values follow Pandas grouping behavior. Mutable/unhashable
key values are rejected. Input frames must not change concurrently during an
audit/merge. A high-cardinality key table still uses memory proportional to the
number of observed keys. Whitespace warnings describe literal formatting only;
they do not assert that two different identifiers should match.

`FrequencyBackend` and `PandasBackend` define a small adapter boundary for future
backends. Alternate backends must implement their own null equality semantics;
the public API currently chooses Pandas only.

## Reproduce validation and benchmarks

```bash
python -m pip install -e ".[dev]"
python -m pytest --cov=joinwhy --cov-report=term-missing
python -m ruff check .
python -m mypy src
python examples/quickstart.py
python benchmarks/benchmark.py --rows 100000 --repeat 5
```

Tests compare predictions with real Pandas joins, including generated composite
keys, empty inputs, nulls, extension dtypes and 100,000-row data. The benchmark
checks its manual Pandas reference first, warms each implementation, records
five independent durations and a separate tracemalloc peak. Memory is traced
Python allocation, not process RSS; results are machine-specific.
[Recorded results](benchmarks/results.json) include environment, all repetitions,
median and range. The library does more diagnostic work than the manual baseline;
no speed advantage is claimed. See [benchmarks/README.md](benchmarks/README.md).

## Contributing and roadmap

See [CONTRIBUTING.md](CONTRIBUTING.md). New dtype behavior needs a differential
regression against a real Pandas merge. For 0.2.0, priorities are explicit
`left_on`/`right_on` support, bounded diagnostic samples for high-cardinality
keys, and a separately verified Polars adapter. MIT licensed original code;
upstream projects receive credit without implying affiliation.
