# joinwhy

**See a join explosion before it reaches your invoice totals or memory budget.**

A join can duplicate monetary amounts or silently discard customer IDs. joinwhy forecasts the exact row count and reports problematic keys before you allocate the joined payload.

## Try it in two minutes

Requires Python 3.11+ with pandas 2.2+. Install the [published release](https://pypi.org/project/joinwhy/0.1.2/):

```sh
python -m pip install "joinwhy==0.1.2"
```

Copy this complete example into a Python session or save it as `demo.py` and run `python demo.py`:

```python
import pandas as pd

import joinwhy

customers = pd.DataFrame({"customer_id": [1, 2, 3], "name": ["Ana", "Bo", "Cy"]})
transactions = pd.DataFrame({"customer_id": [1, 1, 3], "amount": [10, 20, 15]})
report = joinwhy.audit(customers, transactions, on="customer_id", how="left")
print(report.explain())
assert report.expected_rows == 4
result = joinwhy.safe_merge(
    customers, transactions, on="customer_id", relationship="one_to_many", max_expansion=2
)
assert len(result) == report.expected_rows
print(result)
```

The example forecasts **4 rows** from 3 customers, then checks a one-to-many relationship before merging.

## What you gain

One reusable report combines expected size, duplicate and unmatched keys, null/whitespace diagnostics and an expansion guardrail. The forecast groups keys instead of creating the full payload join.

| Existing approach | What this package adds | Tradeoff |
|---|---|---|
| Pandas grouping, `merge(validate=...)` and `indicator=True` provide the underlying tools. | Inspectable key tables, null/whitespace flags, relationship checks and the pre-allocation expansion limit. | Extra diagnostics consume time and key-table memory. A direct merge or short pandas recipe is sufficient when you already trust the keys and size. |

[Run the side-by-side comparison](docs/comparison.md): both implementations are included and their shared outputs are asserted equal. [powerjoin](https://github.com/moodymudskipper/powerjoin) is a workflow inspiration for checked joins. This is a focused pandas equality-join API.

## Solve a real workflow problem

These small, synthetic operational fixtures make the workflows reproducible without external services or private records. Each recipe includes expected results and a failure or interpretation boundary.

| Recipe | Verified outcome |
|---|---|
| [Stop invoice totals from being counted twice](docs/cookbook.md#invoice-multiplication) | The fixture exposes the incorrect total of 400, aggregates payments first, and verifies a one-to-one join with the correct total of 300. |
| [Find IDs lost during enrichment](docs/cookbook.md#lost-customer-ids) | Inspect the two unmatched customer keys and one unmatched order key before accepting an inner join. |
| [Protect a composite-key ETL join](docs/cookbook.md#tenant-keys-and-budget) | Join on tenant plus ID and reject an expansion above the chosen budget before building the payload. |

From a checkout, after installing the package:

```sh
python examples/comparison.py
python examples/cookbook.py
```

## Measured performance, accuracy and usability

Recorded on Windows-11-10.0.26200-SP0, CPython 3.13.5, with five rotating timed rounds. At the largest measured input size (50,000; see workload definition):

| Compared operation | Baseline median ms | Package median ms | Package / baseline |
|---|---:|---:|---:|
| Package / manual recipe | 4.875 | 41.086 | 8.43x |

Ratio = package median / baseline median; above 1 means higher latency. The package performs the extra diagnostic or provenance work described above. These single-host synthetic results have no universal speed guarantee. Allocation measurements and the smaller scales are in the full table.

[Measured table](benchmarks/RESULTS.md) · [Raw repeated samples](benchmarks/latest.json) · [Reproduction instructions](benchmarks/README.md)

Accuracy means agreement on the stated fixture outputs: Five common counts are compared exactly. The comparison example independently checks the left-join size; the cookbook checks real merges and a rejected guardrail. Code-size counts are an inspectable usability proxy; no developer-time study was performed.

## Scope and limits

- Same-named, uniquely labeled string key columns and equality joins only; no index/as-of/fuzzy/cross joins.
- Pandas null keys match null keys, which differs from common SQL semantics.
- Key tables scale with observed key cardinality; this is an in-memory tool.
- Identifier normalization is explicit. The package cannot restore precision lost before input construction.

## Documentation

- [Start here](docs/index.md): choose a workflow and find the relevant guide.
- [Comparison and alternatives](docs/comparison.md): full code, shared behavior and added outputs.
- [Cookbook](docs/cookbook.md): three complete problem-solving recipes.
- [API and behavioral contracts](docs/api.md): exact semantics and errors.
- [Benchmark methodology](benchmarks/README.md): inputs, correctness checks, environment and limits.
- [Research and upstream credit](RESEARCH.md): R inspiration, existing Python tools and scope decisions.

## Develop and validate

```sh
python -m pip install -e ".[dev]"
python scripts/check_docs.py
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy src
```

MIT licensed. Contributions should include a reproducing example and the expected behavior. See [CONTRIBUTING.md](CONTRIBUTING.md).
