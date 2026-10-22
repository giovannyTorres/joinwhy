# Comparison: joinwhy and the underlying primitives

A join can duplicate monetary amounts or silently discard customer IDs. joinwhy forecasts the exact row count and reports problematic keys before you allocate the joined payload.

## What is compared

| Dimension | Scope |
|---|---|
| Existing tools | Pandas grouping, `merge(validate=...)` and `indicator=True` provide the underlying tools. |
| Shared result checked | Predicted left-join row count. The benchmark also compares duplicate and unmatched-key counts. |
| Additional package behavior | Inspectable key tables, null/whitespace flags, relationship checks and the pre-allocation expansion limit. |
| Cost / when a manual recipe fits | Extra diagnostics consume time and key-table memory. A direct merge or short pandas recipe is sufficient when you already trust the keys and size. |

[powerjoin](https://github.com/moodymudskipper/powerjoin) is a workflow inspiration for checked joins. This is a focused pandas equality-join API. The comparison below measures a Python workflow; it makes no claim of feature parity or numerical parity with an R package.

## Full executable example

Save this as `comparison.py` after installing the release, or run `python examples/comparison.py` from this repository. The assertions verify the stated shared result.

```python
"""Same predicted left-join size; joinwhy also retains key diagnostics."""

import pandas as pd

import joinwhy


def baseline(left, right):
    left_counts = left.groupby("customer_id", dropna=False).size().rename("left")
    right_counts = right.groupby("customer_id", dropna=False).size().rename("right")
    counts = pd.concat([left_counts, right_counts], axis=1).fillna(0)
    return int((counts["left"] * counts["right"].clip(lower=1)).sum())


def library(left, right):
    return joinwhy.audit(left, right, on="customer_id", how="left").expected_rows


if __name__ == "__main__":
    customers = pd.DataFrame({"customer_id": [1, 2, 3]})
    orders = pd.DataFrame({"customer_id": [1, 1, 3]})
    assert baseline(customers, orders) == library(customers, orders) == 4
    print("Both forecast 4 rows; joinwhy also exposes unmatched and duplicate keys.")
```

## How to choose

Use the package when you need its named diagnostics, explicit policies or provenance repeatedly. Keep the underlying pandas/Python recipe when that smaller shared result meets the job. Review each recipe's data assumptions before applying it to another dtype or layout.

Extra diagnostics consume time and key-table memory. A direct merge or short pandas recipe is sufficient when you already trust the keys and size.

## Evidence and boundaries

Five common counts are compared exactly. The comparison example independently checks the left-join size; the cookbook checks real merges and a rejected guardrail.

The repeated-key synthetic workload does not cover arbitrary object keys, mixed dtypes or large payload columns. High-cardinality keys increase report storage. Timing differences do not establish statistical accuracy or developer productivity. The benchmark checks exact fixture outputs and separately reports code-size counts as a limited usability proxy.

[Actual measured results](../benchmarks/RESULTS.md) · [Reproduce the benchmark](../benchmarks/README.md) · [Recipes](cookbook.md) · [API contracts](api.md)

## Sources and alternatives

- [pandas API documentation](https://pandas.pydata.org/docs/reference/index.html) documents the underlying grouping, masking and reshaping primitives.
- [pandas merge: validate, indicator and null-key behavior](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.merge.html)
- [powerjoin upstream](https://github.com/moodymudskipper/powerjoin)

Upstream references credit problem ideas and existing tools. This repository contains its own implementation and claims no upstream affiliation.
