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
in [results.json](results.json). Measurement for **joinwhy 0.1.2** on Python 3.12.14,
Pandas 3.0.6, Linux:

| Workflow | Median seconds | Range seconds | Traced peak bytes |
|---|---:|---:|---:|
| Manual Pandas counts and checks | 0.005992 | 0.005628–0.006632 | 5,035,814 |
| joinwhy audit | 0.063702 | 0.062094–0.065173 | 14,178,879 |

joinwhy is slower on this dataset. It additionally constructs diagnostic key
tables, scans literal whitespace, counts null rows, and produces a report with
structured summaries and readable explanation. Its value is a reusable API and
preflight size guardrail. No universal performance claim follows from this
single synthetic workload. Run the script on representative data before choosing
an operational budget.

## 0.1.2 optimization comparison

The same Linux/Python 3.12.14/Pandas 3.0.6 environment was used before and after
source edits. Two integer-key frames contain 1,000,000 rows each, with keys
modulo 500,000 on the left and 333,333 on the right. The left join has exactly
2,333,334 rows. Each operation warmed up once, followed by three timed
`perf_counter` repetitions without tracemalloc. Raw measurements and workload
metadata appear in [optimization.json](optimization.json).

| Operation | 0.1.1 median seconds | 0.1.2 median seconds |
|---|---:|---:|
| Full audit | 4.496708 | 0.577598 |
| Left frequency preparation | 1.926606 | 0.040443 |
| Materialized Pandas left merge | 0.066057 | 0.059964 |

Version 0.1.2 replaces one scalar lookup per observed key with a vectorized
lookup, retaining original key rows and exact values. It weights observed-key
null/whitespace masks by the original row frequencies instead of rescanning both
complete inputs. This workload shows about 7.8 times faster auditing and 47.6
times faster frequency preparation. The direct merge performs different work;
its result is much larger than a frequency table. The shared machine had other
workloads, so timings and ratios are illustrative rather than CI guarantees.
