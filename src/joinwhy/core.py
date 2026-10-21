"""Frequency-based join diagnostics. Input frames are never modified."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, cast

import pandas as pd

JoinHow = Literal["inner", "left", "right", "outer"]
Relationship = Literal["one_to_one", "one_to_many", "many_to_one", "many_to_many"]


class JoinAuditError(ValueError):
    """The requested audit or merge cannot be performed safely."""


class JoinConstraintError(JoinAuditError):
    """A preflight relationship or output-size constraint was violated."""


class FrequencyBackend(Protocol):
    """Small adapter boundary: frequency preparation and backend null semantics.

    Only PandasBackend is supported by the public API in 0.1.x. Future adapters
    must supply their own alignment semantics, rather than inherit Pandas null
    equality accidentally.
    """

    nulls_equal: bool

    def frequencies(self, frame: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
        """Return internal key columns and a frequency column."""
        ...

    def align(self, left: pd.DataFrame, right: pd.DataFrame) -> pd.DataFrame:
        """Align unique key counts without materializing the full join."""
        ...


class PandasBackend:
    """Pandas key grouping with explicit equality of null keys."""

    nulls_equal = True

    def frequencies(self, frame: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
        selected = frame.loc[:, keys].copy()
        selected.columns = [f"k{i}" for i in range(len(keys))]
        # Group IDs retain exact equality even when pandas infers lossy numeric
        # labels for a groupby index (e.g. object ints above 2**53 beside null).
        # Keep representative rows from the original columns instead of rebuilding
        # keys from those labels. This also preserves extension and categorical
        # dtypes, and assigns counts positionally despite duplicate input indexes.
        codes = selected.groupby(
            list(selected.columns), dropna=False, observed=True, sort=False
        ).ngroup()
        first = ~codes.duplicated()
        counts = codes.value_counts(sort=False)
        result = selected.loc[first].reset_index(drop=True)
        # Reindex all representative group IDs at once. A scalar .loc per key
        # dominates large audits; the positional array also avoids input-index
        # alignment when the original frame has duplicate or shuffled labels.
        result["count"] = counts.reindex(codes.loc[first]).to_numpy(dtype="int64")
        return result

    def align(self, left: pd.DataFrame, right: pd.DataFrame) -> pd.DataFrame:
        names = [name for name in left.columns if name != "count"]
        return (
            left.rename(columns={"count": "left_count"})
            .merge(
                right.rename(columns={"count": "right_count"}),
                on=names,
                how="outer",
                validate="one_to_one",
            )
            .fillna({"left_count": 0, "right_count": 0})
        )


def _keys(on: str | Sequence[str]) -> list[str]:
    keys = [on] if isinstance(on, str) else list(on)
    if not keys or not all(isinstance(key, str) for key in keys):
        raise JoinAuditError("on must contain one or more string column names")
    if len(set(keys)) != len(keys):
        raise JoinAuditError("on contains duplicate column names")
    return keys


def _validate(frame: pd.DataFrame, keys: list[str], side: str) -> None:
    if not isinstance(frame, pd.DataFrame):
        raise TypeError(f"{side} must be a pandas DataFrame")
    if not frame.columns.is_unique:
        raise JoinAuditError(f"{side} has duplicate column labels")
    missing = [key for key in keys if key not in frame.columns]
    if missing:
        raise JoinAuditError(f"{side} is missing key columns: {missing}")


def _has_whitespace(value: Any) -> bool:
    return isinstance(value, str) and value != value.strip()


@dataclass(frozen=True)
class AuditReport:
    """A snapshot of join diagnostics; inspection methods return fresh frames."""

    keys: tuple[str, ...]
    how: JoinHow
    left_rows: int
    right_rows: int
    expected_rows: int
    relationship: Relationship
    left_duplicate_keys: int
    right_duplicate_keys: int
    left_null_rows: int
    right_null_rows: int
    left_whitespace_rows: int
    right_whitespace_rows: int
    warnings: tuple[str, ...]
    _table: pd.DataFrame = field(repr=False, compare=False)

    @property
    def expansion(self) -> float:
        """Output rows / left input rows; zero/zero is 0, positive/zero is inf."""
        return (
            self.expected_rows / self.left_rows
            if self.left_rows
            else (math.inf if self.expected_rows else 0.0)
        )

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-compatible summary (unbounded expansion becomes null)."""
        return {
            "backend": "pandas",
            "nulls_equal": True,
            "keys": list(self.keys),
            "how": self.how,
            "left_rows": self.left_rows,
            "right_rows": self.right_rows,
            "expected_rows": self.expected_rows,
            "relationship": self.relationship,
            "expansion": self.expansion if math.isfinite(self.expansion) else None,
            "left_duplicate_keys": self.left_duplicate_keys,
            "right_duplicate_keys": self.right_duplicate_keys,
            "left_null_rows": self.left_null_rows,
            "right_null_rows": self.right_null_rows,
            "left_whitespace_rows": self.left_whitespace_rows,
            "right_whitespace_rows": self.right_whitespace_rows,
            "left_unmatched_keys": int((self._table["right_count"] == 0).sum()),
            "right_unmatched_keys": int((self._table["left_count"] == 0).sum()),
            "warnings": list(self.warnings),
        }

    def problematic_keys(self) -> pd.DataFrame:
        """Return duplicate, unmatched, null or whitespace keys with counts.

        The ``key`` column contains tuples in ``report.keys`` order. No key values
        are normalized or corrected. Counts are original input row frequencies.
        """
        table = self._table
        mask = (
            (table["left_count"] > 1)
            | (table["right_count"] > 1)
            | (table["left_count"] == 0)
            | (table["right_count"] == 0)
            | table["null_key"]
            | table["whitespace"]
        )
        return table.loc[mask].copy(deep=True).reset_index(drop=True)

    def unmatched_keys(self, side: Literal["left", "right", "both"] = "both") -> pd.DataFrame:
        """Return keys absent on the opposite side (both sides by default)."""
        if side not in {"left", "right", "both"}:
            raise JoinAuditError("side must be 'left', 'right', or 'both'")
        left = self._table["right_count"] == 0
        right = self._table["left_count"] == 0
        mask = left if side == "left" else right if side == "right" else left | right
        return self._table.loc[mask].copy(deep=True).reset_index(drop=True)

    def explain(self) -> str:
        """Return a readable summary; counts always derive from the input data."""
        lines = [
            "JOIN ANALYSIS",
            f"Left records: {self.left_rows:,}",
            f"Right records: {self.right_rows:,}",
            f"Relationship: {self.relationship.upper()}",
            f"Expected output ({self.how}): {self.expected_rows:,}",
            f"Output / left rows: {self.expansion:.3g}",
            "Null keys match under pandas semantics.",
        ]
        lines.extend(f"Warning: {warning}" for warning in self.warnings)
        if self.warnings:
            lines.append("Review problematic_keys() and unmatched_keys() before merging.")
        return "\n".join(lines)


def audit(
    left: pd.DataFrame,
    right: pd.DataFrame,
    on: str | Sequence[str],
    how: JoinHow = "left",
) -> AuditReport:
    """Predict join size and diagnose keys without materializing joined payloads.

    Supports equality joins on same-named columns. Frequencies contain all
    observed keys, including nulls. Relationship describes uniqueness in the
    complete inputs, consistent with pandas' ``validate`` constraints.
    """
    if how not in {"inner", "left", "right", "outer"}:
        raise JoinAuditError("how must be inner, left, right, or outer")
    keys = _keys(on)
    _validate(left, keys, "left")
    _validate(right, keys, "right")
    backend: FrequencyBackend = PandasBackend()
    try:
        aligned = backend.align(backend.frequencies(left, keys), backend.frequencies(right, keys))
    except (ValueError, TypeError) as exc:
        raise JoinAuditError(f"Cannot align join keys using pandas semantics: {exc}") from exc

    # Python integers avoid overflow when the predicted output exceeds int64.
    pairs = [
        (int(left_count), int(right_count))
        for left_count, right_count in aligned[["left_count", "right_count"]].itertuples(
            index=False, name=None
        )
    ]
    expected = sum(
        left_count * right_count
        if left_count and right_count
        else left_count
        if how in {"left", "outer"}
        else 0
        for left_count, right_count in pairs
    )
    if how in {"right", "outer"}:
        expected += sum(right_count for left_count, right_count in pairs if not left_count)
    ld = sum(left_count > 1 for left_count, _ in pairs)
    rd = sum(right_count > 1 for _, right_count in pairs)
    relation = cast(Relationship, f"{'many' if ld else 'one'}_to_{'many' if rd else 'one'}")
    aligned_keys = aligned[[f"k{i}" for i in range(len(keys))]]
    tuples = list(aligned_keys.itertuples(index=False, name=None))
    table = pd.DataFrame(
        {
            "key": tuples,
            "left_count": [left_count for left_count, _ in pairs],
            "right_count": [right_count for _, right_count in pairs],
            "null_key": aligned_keys.isna().any(axis=1).to_numpy(),
            "whitespace": [any(_has_whitespace(v) for v in key) for key in tuples],
        }
    )
    # Explicit bool dtype also preserves masks for empty frames.
    table = table.astype({"null_key": bool, "whitespace": bool})
    # Every observed key already has its original row frequency. Weight these
    # diagnostic masks instead of rescanning both complete input key frames.
    ln = int(table.loc[table["null_key"], "left_count"].sum())
    rn = int(table.loc[table["null_key"], "right_count"].sum())
    lw = int(table.loc[table["whitespace"], "left_count"].sum())
    rw = int(table.loc[table["whitespace"], "right_count"].sum())
    warnings: list[str] = []
    for side, duplicates, nulls, whitespace, unmatched in (
        ("left", ld, ln, lw, sum(right_count == 0 for _, right_count in pairs)),
        ("right", rd, rn, rw, sum(left_count == 0 for left_count, _ in pairs)),
    ):
        if duplicates:
            warnings.append(f"{duplicates} duplicate keys on the {side}")
        if unmatched:
            warnings.append(f"{unmatched} unmatched keys on the {side}")
        if nulls:
            warnings.append(f"{nulls} rows with null key components on the {side}")
        if whitespace:
            warnings.append(f"{whitespace} rows with leading/trailing key whitespace on the {side}")
    if ld and rd:
        warnings.append("many-to-many input key relationship; review row expansion")
    return AuditReport(
        tuple(keys),
        how,
        len(left),
        len(right),
        expected,
        relation,
        ld,
        rd,
        ln,
        rn,
        lw,
        rw,
        tuple(warnings),
        table,
    )


def safe_merge(
    left: pd.DataFrame,
    right: pd.DataFrame,
    on: str | Sequence[str],
    how: JoinHow = "left",
    *,
    relationship: Relationship | None = None,
    max_expansion: float | None = None,
    **merge_kwargs: Any,
) -> pd.DataFrame:
    """Enforce uniqueness and output/left expansion before performing the merge.

    ``suffixes``, ``sort`` and ``indicator`` are forwarded to pandas. Keys, join
    kind and validate cannot be overridden through kwargs. No data is cleaned.
    """
    allowed = {"one_to_one", "one_to_many", "many_to_one", "many_to_many"}
    if relationship is not None and relationship not in allowed:
        raise JoinAuditError(f"relationship must be one of {sorted(allowed)}")
    unexpected = set(merge_kwargs) - {"suffixes", "sort", "indicator"}
    if unexpected:
        raise JoinAuditError(f"Unsupported merge options: {sorted(unexpected)}")
    if max_expansion is not None and (not math.isfinite(max_expansion) or max_expansion < 0):
        raise JoinAuditError("max_expansion must be a finite non-negative number")
    report = audit(left, right, on, how)
    if relationship in {"one_to_one", "one_to_many"} and report.left_duplicate_keys:
        raise JoinConstraintError(f"{relationship} requires unique left keys")
    if relationship in {"one_to_one", "many_to_one"} and report.right_duplicate_keys:
        raise JoinConstraintError(f"{relationship} requires unique right keys")
    if max_expansion is not None and report.expansion > max_expansion:
        raise JoinConstraintError(
            f"Predicted {report.expected_rows} rows; expansion {report.expansion:g} exceeds {max_expansion:g}"
        )
    try:
        return left.merge(
            right, on=list(report.keys), how=how, validate=relationship, **merge_kwargs
        )
    except (ValueError, TypeError) as exc:
        # Grouped representatives and complete input columns can lead pandas to
        # infer different key compatibility, especially for all-null object keys.
        # Keep the public error contract even if rejection occurs after preflight.
        raise JoinAuditError(f"Cannot merge using pandas semantics: {exc}") from exc
