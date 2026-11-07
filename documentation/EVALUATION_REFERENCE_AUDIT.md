# Finite sample AP and calendar period review budgets

## What was corrected

The existing paper correctly used constant-score AP = P/N. That value is not exactly the expected AP of a uniformly random, tie-free finite-sample ordering. The original results stay unchanged; the revision distinguishes these two references explicitly. This is not a claim that earlier computed model APs were wrong.

For N records and P>0 positives, let I_k indicate a positive at rank k. For tie-free scores, AP is (1/P) times the sum over k of I_k times the number of positives in ranks 1 through k, divided by k. Under a uniform random ordering, Pr(I_k=1)=P/N. Conditional on I_k=1, the expected number of positives in the preceding k-1 slots is (k-1)(P-1)/(N-1). Linearity of expectation therefore gives:

E(AP) = (1/N) sum over k=1,...,N of [1 + (k-1)(P-1)/(N-1)]/k

Equivalently, with H_N = 1 + 1/2 + ... + 1/N:

E(AP) = H_N/N + [(P-1)/(N-1)] (1 - H_N/N), for N>1.

For N=P=1 the expectation is one. All-positive cohorts also give one. With both classes present, the random-order expectation exceeds P/N by (N-P)(H_N-1)/[N(N-1)]. This derivation is supplied by this study; scikit-learn reference R17 establishes the metric convention, not this finite-sample result.

The implementation exhaustively enumerates all 1,013 distinct positive-position patterns across all 45 N/P pairs with 1<=P<=N<=9. Hand-calculated rank AP agrees with installed scikit-learn 1.7.2 for every pattern, and enumerated means agree with the formula to at most 3.34e-16. A separate offline checker evaluates the full-cohort reference using exact rational rank-by-rank expectations. These are numerical checks in the same research workflow, not external replication.

## Results and uncertainty

For N=2,695 and P=93, constant-score AP is 0.03450834879406308 and expected random tie-free AP is 0.03718784066835856. Original ordinary-logistic AP 0.044712767084718344 exceeds the latter by 0.0075249264163598. A 1,000-replicate CIK-cluster bootstrap with seed 20261108 gives a nominal 95% interval of approximately -0.00324 to 0.03480 for that contrast. Weighted-logistic and forest contrasts also include zero. Full precision is in random_AP_reference.csv.

Each paired replicate resamples CIKs, treats observations with their sampled multiplicities as an expanded multiset, evaluates the fixed model with integer sample weights, and recomputes the random-order expectation using that resample's N/P. For this analytic reference, each copied record receives a distinct position; the fixed model retains its actual score ties. This does not require an assertion that firm-dependent legal outcomes are exchangeable in a permutation test. No permutation p-value or independent random-ranking experiment is reported. These conditional intervals do not include model selection, source errors, unidentified episodes or temporal dependence across companies.

The all-tied constant score is included in the machine table for transparency. Its negative AP-minus-random-expectation contrast follows algebraically from the different tie conventions; it is not empirical evidence of an economically harmful classifier. Likewise, a random tie-free reference does not reproduce every model's tie pattern.

## Calendar quarter budgets

The audit fixes the prior cohort, all scores, 1%/5% nominal rates and original expected tie handling. Calendar year/quarter is formed from the source period field rather than fiscal-year labels. There are twelve batches. Every quarter/model/rate is supplied, including very small batches; no quarter is selected for favorable results.

For each batch, capacity is ceiling(rate times batch size). Aggregate hits are summed; precision divides by total capacity and recall by all 93 positives. Random expected hits are summed as capacity times the individual batch's positive fraction. Those expected hits need not equal total capacity times the full-cohort fraction, because rounding and prevalence differ across batches.

At 5%, capacities sum to 140 rather than the pooled ceiling of 135. Logistic retrieves 7 positives, weighted logistic 5 and forest 3, with precision 0.0500, 0.0357 and 0.0214. At 1%, capacity is 31 rather than 27; the two logistic models retrieve 2 each and forest 0. Matched-capacity pooled rankings are supplied to expose the capacity difference: ordinary logistic retrieves 7 at pooled capacity 140 and 1 at pooled capacity 31. None of these contrasts is a causal estimate or independent model validation.

Batch sizes range from 7 to 308. In the seven-record final batch, both nominal rates select one record (14.29%); nominal rates must therefore not be presented as exact realized rates. No complete filing calendar, point-in-time feature panel, historical control pool or fixed real-time threshold has been reconstructed. Even calendar-quarter rankings assume the whole source-period batch is collected before ranking; period end and submission time are different. This is a descriptive allocation audit, not an operational filing-time simulation.

## Reproduce

First obtain the original pinned financial sources and run analyze.py, which generates generated_test_scores.csv locally. Then run:

```sh
python3 code/audit_evaluation_reference.py --source-dir local_sources --bootstrap 1000
python3 code/verify_evaluation_reference.py
```

No new fit or relabeling occurs. The main source hashes and original AP/AUC/pooled retrieval counts are checked before publication of these outputs. Per-record scores remain locally regenerated rather than redistributed. Included aggregate tables and proof support offline numerical review, while metric recomputation still requires the source files and scores.
