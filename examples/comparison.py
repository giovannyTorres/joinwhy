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
