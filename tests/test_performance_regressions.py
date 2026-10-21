"""Frequency ordering and materialization errors after preflight."""

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from joinwhy import JoinAuditError, PandasBackend, audit, safe_merge


def test_frequency_counts_follow_representatives_not_count_or_index_order():
    frame = pd.DataFrame(
        {"key": ["z", "a", "z", "b", "a", "a", None, "b", None]},
        index=[9, 9, 3, 1, 8, 3, 9, 1, 7],
    )
    expected = pd.DataFrame(
        {"k0": ["z", "a", "b", None], "count": pd.Series([2, 3, 2, 2], dtype="int64")}
    )
    assert_frame_equal(PandasBackend().frequencies(frame, ["key"]), expected)


@pytest.mark.parametrize("how", ["inner", "left", "right", "outer"])
def test_diagnostics_count_input_rows_even_for_unmatched_repeated_composite_keys(how):
    left = pd.DataFrame(
        {
            "key": [" a", " a", None, None, "ok", "ok", "b "],
            "part": [None, None, "x", "x", "x", "y", "z"],
        }
    )
    right = pd.DataFrame(
        {
            "key": [" a", None, None, "b ", "b ", "ok"],
            "part": [None, "x", "x", None, None, "x"],
        }
    )
    report = audit(left, right, ["key", "part"], how)
    assert report.left_null_rows == 4
    assert report.right_null_rows == 5
    assert report.left_whitespace_rows == 3
    assert report.right_whitespace_rows == 3


@pytest.mark.parametrize("error_type", [ValueError, TypeError])
def test_safe_merge_wraps_pandas_materialization_errors(monkeypatch, error_type):
    left = pd.DataFrame({"key": pd.Series([float("nan"), float("nan")], dtype=object)})
    right = pd.DataFrame({"key": [1, 2]})
    assert audit(left, right, "key").expected_rows == 2
    original_error = error_type("incompatible input key dtypes")

    def reject_merge(*args, **kwargs):
        raise original_error

    # Patch only the original frame: frequency alignment still uses real pandas.
    monkeypatch.setattr(left, "merge", reject_merge)
    with pytest.raises(JoinAuditError, match="Cannot merge using pandas semantics") as error:
        safe_merge(left, right, "key")
    assert error.value.__cause__ is original_error


def test_safe_merge_wraps_native_payload_column_conflict():
    left = pd.DataFrame({"key": [1], "_merge": ["source"]})
    right = pd.DataFrame({"key": [1]})
    assert audit(left, right, "key").expected_rows == 1
    with pytest.raises(JoinAuditError, match="Cannot merge using pandas semantics") as error:
        safe_merge(left, right, "key", indicator=True)
    assert isinstance(error.value.__cause__, ValueError)
    assert "indicator" in str(error.value.__cause__)


@pytest.mark.parametrize("how", ["inner", "left", "right", "outer"])
@pytest.mark.parametrize("null", [None, float("nan"), pd.NA, pd.NaT])
@pytest.mark.parametrize("reverse", [False, True])
def test_all_null_object_and_integer_keys_follow_native_merge(how, null, reverse):
    left = pd.DataFrame({"key": pd.Series([null, null], dtype=object)})
    right = pd.DataFrame({"key": [1, 2]})
    if reverse:
        left, right = right, left
    try:
        expected = left.merge(right, on="key", how=how)
    except (ValueError, TypeError):
        with pytest.raises(JoinAuditError):
            safe_merge(left, right, "key", how)
    else:
        assert_frame_equal(safe_merge(left, right, "key", how), expected)
