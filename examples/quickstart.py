"""A runnable, deterministic example using only installed runtime dependencies."""

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
