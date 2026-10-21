"""Independent differential checks against actual pandas merge behavior."""

from __future__ import annotations

import json

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from joinwhy import JoinAuditError, JoinConstraintError, audit, safe_merge


def _frames() -> list[tuple[pd.DataFrame, pd.DataFrame, list[str]]]:
    return [
        (
            pd.DataFrame({"key": pd.Series([1, 1, pd.NA, 3], dtype="Int64")}),
            pd.DataFrame({"key": pd.Series([1, pd.NA, pd.NA, 4], dtype="Int64")}),
            ["key"],
        ),
        (
            pd.DataFrame(
                {"key": pd.Categorical(["a", None, "b"], categories=["a", "b", "unused"])}
            ),
            pd.DataFrame(
                {"key": pd.Categorical(["a", None, None], categories=["a", "b", "unused"])}
            ),
            ["key"],
        ),
        (
            pd.DataFrame({"key": pd.to_datetime(["2024-01-01", None, "2024-01-01"], utc=True)}),
            pd.DataFrame({"key": pd.to_datetime([None, None, "2024-01-02"], utc=True)}),
            ["key"],
        ),
        (
            pd.DataFrame({"key": [1, 2, 2]}),
            pd.DataFrame({"key": [1.0, 2.0, 2.0, 3.0]}),
            ["key"],
        ),
        (
            pd.DataFrame({"key": pd.Series([None, float("nan"), pd.NA, "a"], dtype=object)}),
            pd.DataFrame({"key": pd.Series([None, "b"], dtype=object)}),
            ["key"],
        ),
        (
            pd.DataFrame({"k0": [None, None, "a", "a"], "count": [1, 2, None, None]}),
            pd.DataFrame({"k0": [None, "a", "a"], "count": [2, None, None]}),
            ["k0", "count"],
        ),
        (
            pd.DataFrame({"key": pd.Series([], dtype="Int64")}),
            pd.DataFrame({"key": pd.Series([pd.NA, pd.NA, 2], dtype="Int64")}),
            ["key"],
        ),
        (
            pd.DataFrame({"key": pd.Series([], dtype="string")}),
            pd.DataFrame({"key": pd.Series([], dtype="string")}),
            ["key"],
        ),
    ]


@pytest.mark.parametrize("how", ["inner", "left", "right", "outer"])
@pytest.mark.parametrize("left,right,keys", _frames())
def test_differential_key_dtype_cases(left, right, keys, how):
    original_left, original_right = left.copy(deep=True), right.copy(deep=True)
    report = audit(left, right, on=keys, how=how)
    assert report.expected_rows == len(left.merge(right, on=keys, how=how))
    assert_frame_equal(left, original_left)
    assert_frame_equal(right, original_right)
    json.dumps(report.to_dict(), allow_nan=False)


@pytest.mark.parametrize("how", ["inner", "left", "right", "outer"])
def test_tuple_valued_scalar_keys(how):
    left = pd.DataFrame({"key": [("a", 1), ("a", 1), ("b", 2)]})
    right = pd.DataFrame({"key": [("a", 1), ("c", 3)]})
    assert audit(left, right, "key", how).expected_rows == len(left.merge(right, on="key", how=how))


def test_safe_merge_stops_before_payload_merge(monkeypatch):
    left = pd.DataFrame({"key": [1, 1], "left_value": [10, 20]})
    right = pd.DataFrame({"key": [1, 1, 1], "right_value": [30, 40, 50]})

    def forbidden(*args, **kwargs):
        pytest.fail("Payload merge must not be called after a failed constraint")

    monkeypatch.setattr(left, "merge", forbidden)
    with pytest.raises(JoinConstraintError):
        safe_merge(left, right, "key", relationship="one_to_many")
    with pytest.raises(JoinConstraintError):
        safe_merge(left, right, "key", max_expansion=2.0)


@pytest.mark.parametrize(
    "options", [{"left_index": True}, {"right_on": "other"}, {"validate": "many_to_many"}]
)
def test_safe_merge_rejects_semantics_changing_kwargs(options):
    with pytest.raises(JoinAuditError, match="Unsupported merge options"):
        safe_merge(pd.DataFrame({"key": [1]}), pd.DataFrame({"key": [1]}), "key", **options)


def test_whitespace_warning_has_no_substring_false_positive():
    left = pd.DataFrame({"key": ["New York", "a\tb", "a b"]})
    report = audit(left, left.copy(), "key")
    assert report.left_whitespace_rows == 0
    assert report.right_whitespace_rows == 0
    assert not report.warnings


def test_inspection_frame_is_independent_snapshot():
    left = pd.DataFrame({"key": [1, 1, 2]})
    report = audit(left, pd.DataFrame({"key": [1, 3]}), "key")
    expected = report.problematic_keys()
    inspection = report.problematic_keys()
    inspection.loc[:, "left_count"] = 999
    assert_frame_equal(report.problematic_keys(), expected)
    left.loc[:, "key"] = 777
    assert_frame_equal(report.problematic_keys(), expected)
