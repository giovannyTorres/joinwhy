# Changelog

## 0.1.1 — 2026-10-21

- Preserve exact original join-key values and dtypes when counting observed groups.
  Object integer keys above `2**53` beside nulls could previously be rounded by
  Pandas' inferred groupby index labels, causing an incorrect audit or an alignment error.
- Count public Pandas group IDs and retain representative original key rows instead.
  Add differential regressions for adjacent large integers, nulls, composite keys,
  duplicate input indexes, categorical/nullable/datetime and tuple keys.
- Keep the published 0.1.0 release unchanged; the precision correction is a new version.

## 0.1.0 — 2026-10-21

- Initial independently installable release of joinwhy.
- Typed public API, original implementations, executable examples, tests, and reproducible benchmarks.

Publication state is recorded in RELEASE.md; this version number alone does not imply a PyPI upload.
