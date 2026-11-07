# SEC filing audit data and interpretation

This is a post hoc descriptive audit, not new predictive validation. The frozen selection and original rules are in SEC_PILOT_SELECTION.csv and SEC_PILOT_PLAN.md. All 93 evaluation positives, 26 deterministically sampled nonlinked controls and one separately targeted Amyris observation give 120 observations in 53 firms. These groups are not a representative sample of all SEC issuers. No claim that nonlinked controls are honest is made.

Official public SEC companyfacts and submissions APIs supplied 108 JSON payloads, all retrieved successfully, with URLs, retrieval timestamps, byte counts and SHA256 in sec_source_manifest.csv. System curl verified TLS using the operating system trust store. An initial Python trust-store failure was an environment issue, not evidence of SEC data absence; no failed payload entered the analysis. Requests were sequential with a pause and below the SEC ten-request-per-second ceiling. No access restriction was bypassed. No account or proprietary database was used.

The package includes narrowly selected numerical fact and filing-metadata extracts, not full filing texts or complete API payloads. They support offline recomputation of the pilot comparisons. The full original JSON cache remains in the working analysis environment; hashes allow a researcher with a matching cache to verify exact identity. A future live fetch may legitimately change because SEC APIs are updated aggregations. Matching current endpoint URLs alone does not establish historical snapshot identity. Re-extracting from a future snapshot must be treated as a new data version, not an exact replay of the November 2026 extraction.

## Files

- data/sec_pilot_filing_extract.csv: one row per selected observation. The earliest retrieved non-amended 10-Q/10-K must match the period end exactly. Includes accession, filing date, report date, API acceptanceDateTime copied verbatim, form, primary-document URL and four processed-source comparison values. Company name is current submission metadata and is descriptive only. It is not asserted to be the historical issuer name.
- data/sec_pilot_fact_extract.csv: USD facts for six specified standard US-GAAP tags and selected period ends, preserving original and later accessions. NetIncomeLoss is limited to 60-120 inclusive days, never annual net income reclassified as a quarter. Five balance-sheet tags require instant contexts. Repeated API representations are retained. Absence from this API subset does not imply absence from the full filing, which may contain custom tags or different contexts.
- data/sec_pilot_cash_diagnostic_extract.csv: selected standard investment and combined cash/investment tags from the original accession. This was added as a follow-up after cash-only differences appeared; it was not in the initial six-tag audit.
- results/sec_pilot_ratio_comparison.csv: all 480 requested comparisons with match, different or unavailable status. Missing/ambiguous inputs and zero denominators are excluded from numerical comparisons, never filled with zero. Tolerance is relative 1e-6 and absolute 1e-8.
- results/sec_pilot_fact_coverage.csv: availability of each of the six original tags.
- results/sec_pilot_version_changes.csv: an original fact and the earliest later differing value within the retrieved API facts for the identical tag/unit/start/end context. This does not identify the earliest public correction, or establish that every difference is a restatement or fraud.
- results/sec_pilot_cash_reconciliation.csv: exploratory numerical compatibility of narrow cash plus one reported investment tag, or a combined cash/investment tag. Nineteen of twenty differences have a compatible candidate. Compatibility is not independent proof of the source author's actual formula; overlapping investment tags are not added together.
- results/sec_pilot_unmatched_candidates.csv: after the strict rule produced 13 unmatched observations, a follow-up search within seven days found one nearby accession each. They remain unmatched in the main exact-date audit; candidate offsets range from minus four to plus one days. No candidate's facts were silently substituted into the 480 comparisons.
- results/sec_pilot_checks.json and sec_pilot_summary.csv: overall and group-specific counts. Ratios have different denominators; never interpret 353/480 as the accuracy of available facts.

## Availability boundary

The chosen report is the earliest exact-period statutory report in the downloaded history, not necessarily the first earnings release, 8-K, press release or public correction. The date-level rule makes its values eligible from the next calendar day. No intraday decision is simulated. API acceptance timestamps are preserved but their legacy timezone handling has not been independently reconciled to complete submission headers. Filing lag among the 107 exact matches ranges from 20 to 97 days, median 41 days. This is descriptive of the selected group, not an issuer-population estimate.

The 13 exact-date failures are not proof of missing filings. The nearby candidates are consistent with source month-end normalization, including week-based fiscal calendars, but the source transformation was not independently re-executed. A larger panel must use accession-specific actual report dates and validate any normalized-to-actual mapping explicitly.

## Residual cash discrepancy

The remaining unmatched cash comparison is Sensus Healthcare, CIK 1494891, September 30, 2020. A targeted manual inspection of the original Form 10-Q balance sheet, accession 0001213900-20-036128, found current cash USD 16,127,085, current debt-security investments shown as a dash (zero), and total assets USD 27,721,217. The comparative December 31, 2019 investment balance is USD 7,389,407. These four observations and the official primary-document URL are recorded in data/sec_pilot_manual_filing_check.csv, explicitly marked as manual extraction.

The processed source cash/assets ratio 0.8483210531485684 equals (16,127,085 + 7,389,407)/27,721,217; the current cash/assets ratio is 0.5817596319815252. This is an exact numerical fingerprint consistent with carrying a prior-period investment value into the current ratio. The source transformation code was not re-executed, so the implementation mechanism is not established. This is a specific unresolved preprocessing discrepancy, not proof of future-information leakage, a population error-rate estimate or an explanation of model performance. The benchmark values and original model metrics are preserved; no selective replacement is made.

## Targeted Amyris example

For April 1-June 30, 2018, NetIncomeLoss is USD 1,533,000 in accession 0001171843-18-006064, filed August 14, 2018, and USD -14,382,000 in accession 0001171843-19-006389, filed October 7, 2019. The original and later primary documents were inspected; the latter identifies its 2018 comparative figures as restated. These figures are net income/loss attributable to Amyris, not amounts attributable to common stockholders. The later value is one verified later restated comparator, not necessarily the earliest public correction.

The released ReturnOnAssets value 0.0129201361966085 equals 1,533,000/118,652,000 within numeric precision. That particular benchmark value is compatible with the original positive earnings figure, so the example does not demonstrate look-ahead contamination of that feature. It demonstrates why period-only joins can lose the distinction between original and revised numbers.

## Reproduce

From the package root, offline with standard Python 3:

```sh
python3 code/sec_filing_audit.py analyze
python3 code/verify_sec_audit.py
```

To retrieve a new live API snapshot and extract it against the pinned financial source:

```sh
python3 code/sec_filing_audit.py fetch --cache local_sec
python3 code/sec_filing_audit.py extract --cache local_sec --financials local_sources/hf_financials.csv
python3 code/verify_sec_audit.py --cache local_sec
```

System curl is required for downloading. Keep the delivered package intact and perform live updates in a separate copy. The recorded run downloaded about 153 MB across 108 requests; future sizes may differ. The extraction does not refit models, rebuild all twelve predictors, reconstruct the historical control universe, ascertain first disclosure dates for all labels or estimate a prospective fraud model.


To independently reconstruct the frozen selection from the pinned split files without changing the selection CSV:

```sh
python3 code/sec_filing_audit.py verify-selection --source-dir local_sources
```
