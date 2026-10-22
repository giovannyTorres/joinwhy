# Cookbook: joinwhy

Three common operational problems, with complete Python code and asserted outcomes. The records are **synthetic fixtures modeled on real workflows**, not measurements from a business or real customer data.

Install `python -m pip install "joinwhy==0.1.2"`. From a checkout, run all three with `python examples/cookbook.py`.

<a id="invoice-multiplication"></a>
## Stop invoice totals from being counted twice

**Problem.** An invoice register is enriched with installment payments. I-1 has two payments, so a direct join repeats its net amount.

**Expected result.** The fixture exposes the incorrect total of 400, aggregates payments first, and verifies a one-to-one join with the correct total of 300.

Copy the complete block into a fresh Python file and run it:

```python
import pandas as pd
from joinwhy import JoinConstraintError, audit, safe_merge


def invoice_multiplication():
    invoices = pd.DataFrame({"invoice": ["I-1", "I-2"], "net": [100, 200]})
    payments = pd.DataFrame({"invoice": ["I-1", "I-1", "I-2"], "paid": [40, 60, 200]})
    report = audit(invoices, payments, on="invoice", how="left")
    assert report.expected_rows == 3
    assert report.right_duplicate_keys == 1
    # A direct sum after this join would count I-1's net twice.
    assert invoices.merge(payments, on="invoice")["net"].sum() == 400
    assert invoices["net"].sum() == 300
    totals = payments.groupby("invoice", as_index=False)["paid"].sum()
    corrected = safe_merge(invoices, totals, on="invoice", relationship="one_to_one")
    assert corrected["net"].sum() == 300
    return report.to_dict()


print(invoice_multiplication())
```

**Apply it to your data.** Choose the grain of the result before aggregating. A many-to-many relationship can be intentional; the report makes it visible.

<a id="lost-customer-ids"></a>
## Find IDs lost during enrichment

**Problem.** Customer and order exports do not contain the same ID sets.

**Expected result.** Inspect the two unmatched customer keys and one unmatched order key before accepting an inner join.

Copy the complete block into a fresh Python file and run it:

```python
import pandas as pd
from joinwhy import JoinConstraintError, audit, safe_merge


def lost_customer_ids():
    customers = pd.DataFrame({"id": [1, 2, 3]})
    orders = pd.DataFrame({"id": [1, 4]})
    report = audit(customers, orders, on="id", how="inner")
    assert report.expected_rows == 1
    assert len(report.unmatched_keys(side="left")) == 2
    assert len(report.unmatched_keys(side="right")) == 1
    return report.unmatched_keys()


print(lost_customer_ids())
```

**Apply it to your data.** Use side="left" or side="right" deliberately. Unmatched keys count distinct keys, rather than all affected source rows.

<a id="tenant-keys-and-budget"></a>
## Protect a composite-key ETL join

**Problem.** Two tenants both use customer ID 1. Joining only on the ID crosses tenant boundaries.

**Expected result.** Join on tenant plus ID and reject an expansion above the chosen budget before building the payload.

Copy the complete block into a fresh Python file and run it:

```python
import pandas as pd
from joinwhy import JoinConstraintError, audit, safe_merge


def tenant_keys_and_budget():
    customers = pd.DataFrame({"tenant": ["A", "B"], "id": [1, 1]})
    events = pd.DataFrame({"tenant": ["A", "A", "B"], "id": [1, 1, 1]})
    result = safe_merge(
        customers, events, on=["tenant", "id"], relationship="one_to_many", max_expansion=2
    )
    assert len(result) == 3
    try:
        safe_merge(customers, events, on=["tenant", "id"], max_expansion=1)
    except JoinConstraintError:
        return "Rejected before allocating the payload join: 3 rows / 2 customers > 1"
    raise AssertionError("Expected the expansion guardrail to reject the join")


print(tenant_keys_and_budget())
```

**Apply it to your data.** max_expansion measures output rows / left rows. It is a row-count guardrail; byte usage also depends on payload width.

[API details and error policies](api.md) · [Comparison with primitives](comparison.md) · [Benchmark evidence](../benchmarks/RESULTS.md)
