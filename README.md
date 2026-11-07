# Financial Misstatement Reproducibility Audit: Replication Package

Version 1.0.0, prepared 7 November 2026. The public archive of this version has DOI https://doi.org/10.5281/zenodo.24027492.

This package supports the retrospective audit of financial-misstatement data. It includes original analysis scripts, selected extracts, results, source inventories and verification records. Raw third-party financial tables and upstream source code are not redistributed. Follow the pinned retrieval instructions below and consult `data/ATTRIBUTION.md` for source terms. The included checks are internal to the research workflow; they are not independent expert validation.

## Original numerical analysis

Use Python 3.12 in a fresh environment; the executed version was Python 3.12.14. From this folder:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python code/fetch_sources.py --dest local_sources
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MPLCONFIGDIR=local_sources/mpl .venv/bin/python code/analyze.py --source-dir local_sources --bootstrap 1000
.venv/bin/python code/verify_results.py --source-dir local_sources
```

The three financial downloads total approximately 198 MB, are pinned to the original Hugging Face revision, and are hash-checked. Raw third-party financial tables and per-record generated scores are not redistributed. Missing or changed sources fail rather than silently using a substitute. Metrics may differ at the last decimal across environments; source digests, counts and cohort identities must agree.

## Additional reproducible audits

Read SEC_PILOT_DATA.md, MEASUREMENT_AUDIT.md, EPISODE_AND_TIMING_AUDIT.md, EVALUATION_REFERENCE_AUDIT.md, ANNOTATION_ALIGNMENT_AUDIT.md and CONTROL_CANDIDATE_REVIEW.md in documentation/ for definitions and scope.

Included extracts support these offline commands:

```sh
python3 code/sec_filing_audit.py analyze
python3 code/verify_sec_audit.py
python3 code/extend_measurement_audit.py analyze
python3 code/verify_measurement_audit.py
python3 code/verify_episode_timing.py
python3 code/verify_evaluation_reference.py
python3 code/verify_annotation_alignment.py
python3 code/summarize_control_review.py
```

The SEC verifier has an optional --cache argument for checking the separately retained 108 raw official JSON payloads. Without that cache it reports the narrower extract-level scope, so its verification JSON differs from the broader original report. The underlying numerical results do not change. Offline source-scope checks cannot automate legal or accounting adjudication.

After generating local scores, recompute episode and evaluation-reference tables with:

```sh
python3 code/audit_episode_timing.py --source-dir local_sources --bootstrap 1000
python3 code/audit_evaluation_reference.py --source-dir local_sources --bootstrap 1000
```

Annotation recomputation needs four separately retrieved pinned inputs:

```sh
python3 code/fetch_annotation_sources.py --dest annotation_sources
python3 code/audit_annotation_alignment.py --source-dir local_sources --annotation-dir annotation_sources
python3 code/verify_annotation_alignment.py
```

Full helper replay additionally requires the separately retrieved exact third-party source and retained SEC API cache. This package does not reproduce the complete upstream production pipeline or historical panel. A blocked SEC bulk download was not bypassed.

## Additional coverage audit and figures

The added availability decomposition runs offline from the included component records. Field definitions and additional SEC attribution are in documentation/COVERAGE_REASONS.md:

```sh
python3 code/audit_coverage_reasons.py
```

To independently re-extract those component records from the original 53 companyfacts payloads, use `--cache PATH_TO_RETAINED_SEC_CACHE`. Every payload is checked against documentation/sec_source_manifest.csv. That raw cache is not included. The offline mode verifies the extract-level reproduction and does not independently refetch original filings.

To redraw figures from frozen result tables:

```sh
python3 code/make_publication_figures.py
```

To also regenerate the full-axis precision-recall curve, first run the original analysis to produce local scores, then use:

```sh
python3 code/make_publication_figures.py --source-dir local_sources
```

That optional branch checks all three AP values against the original metrics and includes the zero-recall endpoint. The coverage reasons are ordered diagnostics of a selected pilot, not representative error rates. Full uncertainty from model selection, a reconstructed classical accounting score, and new external evaluation data have not been supplied.

## Attribution and terms

Original analysis code is supplied under CODE_LICENSE.txt. Third-party data and extracts retain their own terms; see data/ATTRIBUTION.md.
