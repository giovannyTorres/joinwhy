# Recorded benchmark

Run from the repository root:

```bash
python benchmarks/benchmark.py --rows 100000 --repeat 5
```

The synthetic frames have 100,000 rows each. Left keys repeat twice; right keys
repeat approximately three times, with some left keys unmatched. The exact left
join forecast is 233,334 rows. The script asserts that the manual Pandas
forecast, duplicate-key counts and unmatched-key counts agree with joinwhy.

One warmup precedes five timed repetitions. A separate untimed execution under
tracemalloc records peak traced Python allocation. It does not measure process
RSS or all native array allocations. Environment and raw repetitions appear
in [results.json](results.json). Initial measurement on Python 3.13.5,
Pandas 3.0.6, Windows 11:

| Workflow | Median seconds | Range seconds | Traced peak bytes |
|---|---:|---:|---:|
| Manual Pandas counts and checks | 0.011917 | 0.011251–0.013430 | 5,036,152 |
| joinwhy audit | 0.203938 | 0.183513–0.234503 | 14,617,840 |

joinwhy is slower on this dataset. It additionally constructs diagnostic key
tables, scans literal whitespace, counts null rows, and produces a report with
structured summaries and readable explanation. Its value is a reusable API and
preflight size guardrail, not improved aggregation speed. A fully materialized
join is not the timing baseline because the output itself is not required for
either diagnostic workflow. No universal performance claim follows from this
single synthetic workload. Run the script on representative data before choosing
an operational budget.
