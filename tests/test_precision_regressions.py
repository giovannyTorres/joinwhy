"""Retain original key values rather than inferred groupby index labels."""

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from joinwhy import PandasBackend, audit, safe_merge

LARGE = 2**53


@pytest.mark.parametrize("how", ["inner", "left", "right", "outer"])
@pytest.mark.parametrize("composite", [False, True])
def test_adjacent_object_integers_with_nulls_match_real_merge(how, composite):
    left = pd.DataFrame(
        {"k": pd.Series([LARGE, LARGE + 1, None, LARGE + 1, LARGE + 3], dtype=object)}
    )
    right = pd.DataFrame({"k": pd.Series([LARGE + 1, None, LARGE + 2, LARGE + 1], dtype=object)})
    keys = ["k"]
    if composite:
        left["part"] = pd.Series(["a", "a", None, "a", "b"], dtype="string")
        right["part"] = pd.Series(["a", None, "a", "a"], dtype="string")
        keys.append("part")
    left_before, right_before = left.copy(deep=True), right.copy(deep=True)
    expected = left.merge(right, on=keys, how=how)
    report = audit(left, right, keys, how)
    assert report.expected_rows == len(expected)
    assert report.left_duplicate_keys == report.right_duplicate_keys == 1
    assert report.to_dict()["left_unmatched_keys"] == 2
    assert report.to_dict()["right_unmatched_keys"] == 1
    assert_frame_equal(safe_merge(left, right, keys, how), expected)
    assert_frame_equal(left, left_before)
    assert_frame_equal(right, right_before)
    unmatched = report.unmatched_keys("left")
    exact_values = [key[0] for key in unmatched["key"]]
    assert exact_values == [LARGE, LARGE + 3]
    assert all(isinstance(value, int) for value in exact_values)


def test_frequencies_keep_object_values_and_assign_counts_positionally():
    frame = pd.DataFrame({"k": pd.Series([LARGE, LARGE + 1, None, LARGE + 1], dtype=object)})
    frame.index = [7, 7, 2, 7]
    result = PandasBackend().frequencies(frame, ["k"])
    expected = pd.DataFrame(
        {"k0": pd.Series([LARGE, LARGE + 1, None], dtype=object), "count": [1, 2, 1]}
    )
    assert_frame_equal(result, expected)


@pytest.mark.parametrize(
    "series",
    [
        pd.Series([LARGE, LARGE + 1, pd.NA, LARGE + 1], dtype="Int64"),
        pd.Series(pd.Categorical([LARGE, LARGE + 1, None, LARGE + 1])),
        pd.Series(pd.to_datetime(["2024-01-01", "2024-01-02", None, "2024-01-02"], utc=True)),
        pd.Series([(LARGE, "a"), (LARGE + 1, "a"), None, (LARGE + 1, "a")], dtype=object),
    ],
)
def test_frequencies_preserve_representative_extension_and_tuple_keys(series):
    frame = pd.DataFrame({"k": series})
    result = PandasBackend().frequencies(frame, ["k"])
    expected = frame.iloc[:3].reset_index(drop=True).rename(columns={"k": "k0"})
    expected["count"] = [1, 2, 1]
    assert_frame_equal(result, expected)


def test_all_null_and_empty_object_key_dtypes_are_preserved():
    backend = PandasBackend()
    frame = pd.DataFrame({"k": pd.Series([None, None], dtype=object)})
    result = backend.frequencies(frame, ["k"])
    expected = pd.DataFrame({"k0": pd.Series([None], dtype=object), "count": [2]})
    assert_frame_equal(result, expected)
    empty = backend.frequencies(frame.iloc[:0], ["k"])
    assert empty["k0"].dtype == object
    assert empty["count"].dtype == "int64"
    assert empty.empty
