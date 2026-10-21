"""Reference checks against real pandas merges, rather than formula copies."""

import json
import math
from unittest.mock import patch

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from joinwhy import JoinAuditError, JoinConstraintError, PandasBackend, audit, safe_merge


@pytest.mark.parametrize("how", ["inner", "left", "right", "outer"])
@pytest.mark.parametrize(
    "values",
    [
        ([1, 1, 2, None], [1, 3, 3, None, None]),
        ([], [1, 1]),
        ([1, 2], []),
        ([], []),
        ([1, 2], [2, 3]),
        ([None, None], [None, None, None]),
    ],
)
def test_cardinality_matches_pandas(how, values):
    left = pd.DataFrame({"k": pd.Series(values[0], dtype="Float64"), "x": range(len(values[0]))})
    right = pd.DataFrame({"k": pd.Series(values[1], dtype="Float64"), "y": range(len(values[1]))})
    before = left.copy(deep=True)
    report = audit(left, right, "k", how)
    assert report.expected_rows == len(left.merge(right, on="k", how=how))
    assert_frame_equal(left, before)
    assert report.to_dict()["nulls_equal"] is True


@pytest.mark.parametrize("how", ["inner", "left", "right", "outer"])
def test_composite_nulls_and_reserved_names(how):
    left = pd.DataFrame({"left_count": [1, 1, 2, None], "count": ["a", "a", None, "b"]})
    right = pd.DataFrame({"left_count": [1, 2, None], "count": ["a", None, "c"]})
    report = audit(left, right, ["left_count", "count"], how)
    assert report.expected_rows == len(left.merge(right, on=["left_count", "count"], how=how))
    assert report.keys == ("left_count", "count")
    assert report.left_null_rows == 2


def test_categorical_nullable_datetime_keys():
    for left, right in [
        (
            pd.DataFrame({"k": pd.Categorical(["a", "a", None], categories=["a", "b"])}),
            pd.DataFrame({"k": pd.Categorical(["a", None], categories=["a", "b"])}),
        ),
        (
            pd.DataFrame({"k": pd.to_datetime(["2024-01-01", None])}),
            pd.DataFrame({"k": pd.to_datetime([None, "2024-01-01", None])}),
        ),
        (
            pd.DataFrame({"k": pd.Series(["a", None], dtype="string")}),
            pd.DataFrame({"k": pd.Series([None, "b"], dtype="string")}),
        ),
    ]:
        for how in ["inner", "left", "right", "outer"]:
            assert audit(left, right, "k", how).expected_rows == len(
                left.merge(right, on="k", how=how)
            )


def test_report_details_and_snapshot():
    left = pd.DataFrame({"k": ["a", "a", " b", None, "lonely"]})
    right = pd.DataFrame({"k": ["a", "a", "b", None, "other"]})
    report = audit(left, right, "k")
    assert report.relationship == "many_to_many"
    assert report.left_duplicate_keys == report.right_duplicate_keys == 1
    assert report.left_whitespace_rows == 1
    assert report.right_whitespace_rows == 0
    assert report.expected_rows == 7
    assert len(report.unmatched_keys("left")) == 2
    assert len(report.unmatched_keys("right")) == 2
    assert len(report.unmatched_keys()) == 4
    assert len(report.problematic_keys()) == 6
    assert "Expected output (left): 7" in report.explain()
    assert "Review problematic_keys()" in report.explain()
    assert len(report.warnings) == 8
    changed = report.problematic_keys()
    changed.loc[:, "left_count"] = 999
    assert report.problematic_keys()["left_count"].max() == 2
    left["k"] = "changed"
    assert report.expected_rows == 7
    json.dumps(report.to_dict(), allow_nan=False)
    with pytest.raises(JoinAuditError, match="side"):
        report.unmatched_keys("invalid")


def test_clean_keys_have_no_warnings():
    frame = pd.DataFrame({"k": ["a", "b"]})
    report = audit(frame, frame, "k")
    assert not report.warnings
    assert report.problematic_keys().empty
    assert report.relationship == "one_to_one"
    assert "Warning" not in report.explain()


def test_expansion_empty_and_full_outer():
    empty = pd.DataFrame({"k": pd.Series([], dtype=int)})
    one = pd.DataFrame({"k": [1]})
    assert audit(empty, empty, "k").expansion == 0
    report = audit(empty, one, "k", "outer")
    assert math.isinf(report.expansion)
    assert report.to_dict()["expansion"] is None
    json.dumps(report.to_dict(), allow_nan=False)
    with pytest.raises(JoinConstraintError, match="exceeds"):
        safe_merge(empty, one, "k", "outer", max_expansion=10)


@pytest.mark.parametrize(
    "relation,left_values,right_values,expected",
    [
        ("one_to_one", [1], [1], "one_to_one"),
        ("one_to_many", [1], [1, 1], "one_to_many"),
        ("many_to_one", [1, 1], [1], "many_to_one"),
        ("many_to_many", [1, 1], [1, 1], "many_to_many"),
        ("many_to_many", [1], [1], "one_to_one"),
    ],
)
def test_safe_relationship_constraints(relation, left_values, right_values, expected):
    left = pd.DataFrame({"k": left_values, "value": range(len(left_values))})
    right = pd.DataFrame({"k": right_values, "value": range(len(right_values))})
    result = safe_merge(
        left, right, "k", relationship=relation, suffixes=("_a", "_b"), indicator=True
    )
    assert audit(left, right, "k").relationship == expected
    assert_frame_equal(
        result, left.merge(right, on="k", how="left", suffixes=("_a", "_b"), indicator=True)
    )


def test_safe_merge_rejects_before_full_merge():
    left = pd.DataFrame({"k": [1, 1]})
    right = pd.DataFrame({"k": [1, 1]})
    # Internal merges only see unique frequency tables. The original frame's
    # merge must never be called when a preflight constraint fails.
    with patch.object(left, "merge", side_effect=AssertionError("payload materialized")):
        with pytest.raises(JoinConstraintError, match="unique left"):
            safe_merge(left, right, "k", relationship="one_to_many")
        with pytest.raises(JoinConstraintError, match="unique right"):
            safe_merge(left, right, "k", relationship="many_to_one")
        with pytest.raises(JoinConstraintError, match="expansion"):
            safe_merge(left, right, "k", max_expansion=1.5)
    assert len(safe_merge(left, right, "k", max_expansion=2)) == 4


@pytest.mark.parametrize(
    "kwargs",
    [
        {"relationship": "typo"},
        {"max_expansion": -1},
        {"max_expansion": float("inf")},
        {"max_expansion": float("nan")},
        {"left_index": True},
        {"validate": "1:1"},
    ],
)
def test_invalid_safe_options(kwargs):
    frame = pd.DataFrame({"k": [1]})
    with pytest.raises(JoinAuditError):
        safe_merge(frame, frame, "k", **kwargs)


@pytest.mark.parametrize("on", [[], ["k", "k"], [1], "missing"])
def test_bad_keys(on):
    frame = pd.DataFrame({"k": [1]})
    with pytest.raises(JoinAuditError):
        audit(frame, frame, on)


def test_bad_inputs_and_incompatible_types():
    frame = pd.DataFrame({"k": [1]})
    with pytest.raises(TypeError, match="pandas DataFrame"):
        audit([1], frame, "k")
    with pytest.raises(JoinAuditError, match="duplicate column"):
        audit(pd.DataFrame([[1, 2]], columns=["k", "k"]), frame, "k")
    with pytest.raises(JoinAuditError, match="how"):
        audit(frame, frame, "k", "cross")
    with pytest.raises(JoinAuditError, match="Cannot align"):
        audit(frame, pd.DataFrame({"k": ["one"]}), "k")
    with pytest.raises(JoinAuditError, match="Cannot align"):
        audit(pd.DataFrame({"k": [[1]]}), pd.DataFrame({"k": [[1]]}), "k")


def test_at_least_100k_rows():
    left = pd.DataFrame({"k": [i % 50_000 for i in range(100_000)]})
    right = pd.DataFrame({"k": range(100_000)})
    report = audit(left, right, "k", "outer")
    assert report.expected_rows == len(left.merge(right, on="k", how="outer")) == 150_000
    assert report.relationship == "many_to_one"


def test_backend_contract():
    backend = PandasBackend()
    assert backend.nulls_equal
    result = backend.frequencies(pd.DataFrame({"k": [1, 1, None]}), ["k"])
    assert result["count"].tolist() == [2, 1]
