# Reproduce the review-revision pilot

This directory contains a fresh, bounded experiment for the manuscript. It
uses existing TPC-H DuckDB files read-only; it imports no historical results
from the adjacent research checkout. The SQL is a scalar SPJ query derived
from the TPC-H schema, rather than an official TPC-H performance run.

Install Python dependencies matching `results/review_revision/environment.json`:

```sh
python3 -m pip install duckdb==1.4.3 pulp==3.3.0 highspy==1.12.0 matplotlib
python3 experiments/review_revision.py --self-check
python3 experiments/check_theory.py
python3 experiments/review_revision.py \
  --data-dir /path/to/tpch/databases \
  --output build/reproduced-pilot
python3 experiments/summarize_review.py \
  --results build/reproduced-pilot --figure build/reproduced-pilot/runtime.pdf
```

Inputs are `tpch_sf_0_01.duckdb` and `tpch_sf_0_03.duckdb`, containing
standard TPC-H tables. Their recorded SHA-256 digests identify the exact
input files used. New databases can be generated with DuckDB's `tpch`
extension (`INSTALL tpch; LOAD tpch; CALL dbgen(sf=0.01);` and SF 0.03).
Regenerated database containers may have different file digests; compare
the ordered derivations and counts, not physical-file hashes, in that case.

The frozen `results/review_revision/` directory contains all 180 runs,
including witnesses, statuses, solver bounds, exact validation outcomes,
input sizes, environment versions, and script hash. No run timed out.
Each algorithm/scale/operator/threshold cell has three timing repetitions
of the same instance. Algorithm order is shuffled with seed 1729. ILP uses
one HiGHS thread, zero requested MIP gaps, and a five-second solver limit.
All candidate witnesses are checked using exact integer/rational arithmetic
and a fresh residual query over the original database.

COUNT and SUM compare the full survival-variable ILP, incremental coverage,
certified lazy SQL, and the exact derivatives of a two-level multilinear
circuit. AVG compares the same full ILP with signed-threshold greedy.
The lazy SQL oracle runs on its own materialized derivation table; its
materialization is included in method time. The circuit variant evaluates
closed-form derivatives of `sum_c y_c sum_(b:c_b=c) w_b y_(p_b)`, with no
claim about a general-purpose DAG compiler or compression ratio.

Method times include method-specific initialization and optimization, and
exclude shared source extraction and independent validation. Extraction
is recorded separately. The figure shows medians and min/max ranges of
three repetitions, not confidence intervals. The summarizer audits the
frozen data and regenerates `sizes.tex`, `summary.json`, and the manuscript
figure. Its default input is the frozen directory; the explicit arguments above
regenerate a reproduction separately.

`check_theory.py` exhaustively checks singleton-support AVG optimization and
the sign-separated AVG optimum reduction on small instances. The pilot's
self-check also compares the full ILP against exhaustive enumeration and
requires all three exact-greedy variants to select identical traces.

This pilot covers one self-join-free join shape, two small scale factors,
and rank-two supports. It does not measure peak memory, survivor enumeration,
self-join execution, or large-scale database performance.
