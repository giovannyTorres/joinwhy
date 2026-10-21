"""Explain and constrain pandas equality joins before materializing them."""

from .core import (
    AuditReport,
    FrequencyBackend,
    JoinAuditError,
    JoinConstraintError,
    JoinHow,
    PandasBackend,
    Relationship,
    audit,
    safe_merge,
)

__version__ = "0.1.1"
__all__ = [
    "AuditReport",
    "FrequencyBackend",
    "JoinAuditError",
    "JoinConstraintError",
    "JoinHow",
    "PandasBackend",
    "Relationship",
    "audit",
    "safe_merge",
]
