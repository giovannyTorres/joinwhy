# Research and scope decision

Reviewed 2026-10-21. Original implementation; no R code or documentation is copied.

| Capability | R implementation | Python alternatives | Gap | Proposed solution |
|---|---|---|---|---|
| Pre-join diagnostics | [joinspy](https://github.com/gcol33/joinspy), including duplicate/mismatch checks and prediction | [pandas merge](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.merge.html), groupby and indicator | Pandas supplies the primitives; an analyst still assembles a report and size forecast | One immutable summary plus inspectable key-frequency tables |
| Relationship enforcement | [powerjoin](https://github.com/moodymudskipper/powerjoin) offers configurable checks | Pandas validate and [Polars validate](https://docs.pola.rs/api/python/stable/reference/dataframe/api/polars.DataFrame.join.html) already enforce uniqueness | Uniqueness validation is already solved; a row-expansion budget is an additional guardrail | Preflight both constraints and predicted output/left ratio before payload join |
| Null keys | R backends have their own equality behavior | Pandas matches nulls; Polars defaults to nulls_equal=False | A generic assumption would predict incorrect cardinality | Explicit PandasBackend null policy; no Polars support claimed |
| Suspicious formatting | joinspy offers richer encoding/repair diagnostics | String methods and explicit normalization | Automated repair risks changing identifiers | Deterministic leading/trailing whitespace counts, no automatic alteration |
| Exact cardinality | joinspy predicts join size | Frequency aggregation and multiplication in Pandas/Polars | Existing operations solve it but need careful handling of unmatched/null/empty keys | Aggregate observed keys, align counts, use Python integer arithmetic |

## Evidence and positioning

This is a convenience and safety API, not a claim that Python cannot diagnose joins.
Pandas already implements joins, indicators and relationship validation. joinwhy
adds a reusable preflight report, exact output estimate and expansion limits.
The test suite compares forecasts to actual Pandas merges, including composite
and nullable keys and 100,000-row inputs. The benchmark compares an equivalent
manual count/uniqueness/mismatch workflow and documents additional library cost.

The [joinspy function index](https://gillescolling.com/joinspy/reference/index.html)
also includes post-join and repair functions; those are outside this initial API.
The design favors explicit rules and no mutation. Only same-named string column
keys and equality joins are in scope; indexes, fuzzy/as-of joins and alternate
backends are deferred.

## Licenses

The upstream DESCRIPTION files declare MIT + license files for
[joinspy](https://github.com/gcol33/joinspy/blob/main/DESCRIPTION) and
[powerjoin](https://github.com/moodymudskipper/powerjoin/blob/master/DESCRIPTION).
[Pandas](https://github.com/pandas-dev/pandas/blob/main/LICENSE) uses BSD-3-Clause;
[Polars](https://github.com/pola-rs/polars/blob/main/LICENSE) uses MIT. References
inform behavior and scope only. joinwhy original code is licensed MIT.

## Naming

On 2026-10-21, `https://pypi.org/pypi/joinwhy/json` returned HTTP 404 and the
public GitHub repository search `joinwhy in:name` returned zero repositories.
PEP 503 normalization leaves `joinwhy` unchanged. These are evidence of no
visible exact collision at review time, not a reservation or proof that PyPI
will accept the name. Recheck immediately before first publication. No broad
trademark clearance is claimed. The name describes explaining joins and does
not imply affiliation with the R packages.
