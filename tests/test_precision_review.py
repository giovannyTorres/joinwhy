"""Independent pandas differential regressions for key precision and dtypes."""

from __future__ import annotations

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from joinwhy import JoinAuditError, audit, safe_merge


def _precision_frames():
    large = 2**53
    return [
        (
            pd.DataFrame({"key": pd.Series([large, large + 1, None], dtype=object)}),
            pd.DataFrame({"key": pd.Series([large + 1, None], dtype=object)}),
            ["key"],
        ),
        (
            pd.DataFrame({"key": pd.Series([large + 1, large + 2, large + 1, None], dtype=object)}),
            pd.DataFrame({"key": pd.Series([large + 2, large + 2, None, None], dtype=object)}),
            ["key"],
        ),
        (
            pd.DataFrame({"key": pd.Series([large + 1, large + 2, None, "NA"], dtype=object)}),
            pd.DataFrame({"key": pd.Series([large + 1, None, "NA", "NA"], dtype=object)}),
            ["key"],
        ),
        (
            pd.DataFrame(
                {
                    "key": pd.Series([large, large + 1, None, large + 1], dtype=object),
                    "part": ["a", "a", "a", None],
                }
            ),
            pd.DataFrame(
                {
                    "key": pd.Series([large + 1, None, large + 1], dtype=object),
                    "part": ["a", "a", None],
                }
            ),
            ["key", "part"],
        ),
        (
            pd.DataFrame({"key": pd.Series([large, large + 1, pd.NA], dtype="Int64")}),
            pd.DataFrame({"key": pd.Series([large + 1, pd.NA], dtype="Int64")}),
            ["key"],
        ),
        (
            pd.DataFrame(
                {
                    "key": pd.Categorical(
                        [large, large + 1, None], categories=[large, large + 1, large + 2]
                    )
                }
            ),
            pd.DataFrame(
                {"key": pd.Categorical([large + 1, None], categories=[large, large + 1, large + 2])}
            ),
            ["key"],
        ),
        (
            pd.DataFrame({"key": pd.to_datetime(["2024-01-01", None, "2024-01-02"], utc=True)}),
            pd.DataFrame({"key": pd.to_datetime([None, "2024-01-02", "2024-01-02"], utc=True)}),
            ["key"],
        ),
        (
            pd.DataFrame({"key": pd.Series([], dtype=object)}),
            pd.DataFrame({"key": pd.Series([large + 1, None], dtype=object)}),
            ["key"],
        ),
    ]


@pytest.mark.parametrize("how", ["inner", "left", "right", "outer"])
@pytest.mark.parametrize("left,right,keys", _precision_frames())
def test_prediction_and_safe_merge_match_native_key_semantics(left, right, keys, how):
    expected = left.merge(right, on=keys, how=how)
    original_left = left.copy(deep=True)
    original_right = right.copy(deep=True)
    report = audit(left, right, on=keys, how=how)
    assert report.expected_rows == len(expected)
    assert_frame_equal(safe_merge(left, right, on=keys, how=how), expected)
    assert_frame_equal(left, original_left)
    assert_frame_equal(right, original_right)


@pytest.mark.parametrize("how", ["inner", "left", "right", "outer"])
def test_incompatible_numeric_string_keys_still_rejected(how):
    left = pd.DataFrame({"key": [1, 2]})
    right = pd.DataFrame({"key": pd.Series(["1", "2"], dtype=object)})
    with pytest.raises(ValueError):
        left.merge(right, on="key", how=how)
    with pytest.raises(JoinAuditError):
        audit(left, right, on="key", how=how)


def test_unmatched_key_identity_is_exact_for_adjacent_large_integers():
    large = 2**53
    left = pd.DataFrame({"key": pd.Series([large, large + 1, None], dtype=object)})
    right = pd.DataFrame({"key": pd.Series([large + 1, None], dtype=object)})
    report = audit(left, right, "key", how="left")
    unmatched = report.unmatched_keys("left")
    assert len(unmatched) == 1
    assert int(unmatched["key"].iloc[0][0]) == large
    assert unmatched["left_count"].iloc[0] == 1
    assert unmatched["right_count"].iloc[0] == 0
