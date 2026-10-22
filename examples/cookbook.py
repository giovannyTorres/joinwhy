"""Three operational join problems, with deterministic synthetic fixtures."""

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


def lost_customer_ids():
    customers = pd.DataFrame({"id": [1, 2, 3]})
    orders = pd.DataFrame({"id": [1, 4]})
    report = audit(customers, orders, on="id", how="inner")
    assert report.expected_rows == 1
    assert len(report.unmatched_keys(side="left")) == 2
    assert len(report.unmatched_keys(side="right")) == 1
    return report.unmatched_keys()


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


if __name__ == "__main__":
    for recipe in (invoice_multiplication, lost_customer_ids, tenant_keys_and_budget):
        print(recipe.__name__, recipe(), sep="\n")
