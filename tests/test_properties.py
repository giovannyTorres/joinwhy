import pandas as pd
from hypothesis import given, settings
from hypothesis import strategies as st

from joinwhy import audit

values = st.lists(st.one_of(st.integers(-4, 4), st.none()), max_size=35)


@given(values, values)
@settings(max_examples=100, deadline=None, derandomize=True)
def test_predictions_against_reference(left_values, right_values):
    left = pd.DataFrame({"k": pd.Series(left_values, dtype="Float64")})
    right = pd.DataFrame({"k": pd.Series(right_values, dtype="Float64")})
    for how in ["inner", "left", "right", "outer"]:
        assert audit(left, right, "k", how).expected_rows == len(left.merge(right, on="k", how=how))


@given(
    st.lists(
        st.tuples(st.integers(-2, 2), st.one_of(st.text(alphabet=" ab", max_size=3), st.none())),
        max_size=25,
    ),
    st.lists(
        st.tuples(st.integers(-2, 2), st.one_of(st.text(alphabet=" ab", max_size=3), st.none())),
        max_size=25,
    ),
)
@settings(max_examples=60, deadline=None, derandomize=True)
def test_composite_string_patterns(left_values, right_values):
    left = pd.DataFrame(left_values, columns=["a", "b"]).astype({"a": "int64", "b": "string"})
    right = pd.DataFrame(right_values, columns=["a", "b"]).astype({"a": "int64", "b": "string"})
    for how in ["inner", "left", "right", "outer"]:
        assert audit(left, right, ["a", "b"], how).expected_rows == len(
            left.merge(right, on=["a", "b"], how=how)
        )
