# Episode proxy and public-information timing

This revision is post hoc. It preserves the original benchmark, all original main/supplemental fitted-model metrics, raw source files, and source-label values. No model is refitted or retuned. Original per-record scores are separately checked to reproduce all four original AP and ROC values before subsets are evaluated.

## Source episode overlap

An episode proxy is (CIK, associated AAER number). This does not identify a unique real-world scheme: one release may cover several schemes, and several releases may concern one scheme. The 93 evaluation positives have 26 representative proxies. Twenty-six records share their representative proxy with a refit positive. Using every associated release retained in the pre-deduplication source, 29 evaluation records share at least one proxy with refit positives. Across the source there are 141 positive economic keys linked to multiple release proxies. Repeated positive quarters therefore do not necessarily represent accidental identical-label duplicates.

These counts are distinct from the earlier recurring-company and unseen-company conditions. Removing repeated company-quarter keys does not eliminate repeated enforcement episodes across time. Conversely, a shared source proxy is not by itself proof that a model uses future information. The information set, event interpretation and intended estimand must be specified.

## Fixed-score subsets

The first subset removes the 26 evaluation positives with representative proxies in refit and retains every one of the 2,602 controls: 2,669 records, 67 positives, 18 positive firms, constant-score AP 0.025103. The conservative all-original-association subset removes 29 positives: 2,666 records, 64 positives, 17 positive firms, constant AP 0.024006. No removed positive is relabeled as zero.

On the first subset, AP is 0.029475 for ordinary logistic, 0.026975 for weighted logistic and 0.022760 for the forest. On the second it is 0.025910, 0.024264 and 0.022099. These scores are unchanged from the full evaluation. The ranking metrics now address a different sampled population and positive fraction; their differences from full-cohort AP are not causal effects or fair estimates of a model improvement from purging.

One thousand firm-cluster bootstrap replicates use seed 20261107 and fixed scores. AP-minus-constant contrasts use the same resample's positive fraction. All six model-by-subset nominal 95% intervals include zero. For ordinary logistic they are -0.004207 to 0.032751 under the representative rule and -0.005342 to 0.020740 under all associations. Intervals do not account for prior cohort inspection, model selection, source-label error, unknown schemes or the complete data-production process.

## Label availability at different stages

Among 342 development positives, 42 associated releases are dated by January 1, 2016. Among the 133 validation positives, none of their retained associated releases is dated by January 1, 2018. In the combined 475 refit positives, 120 associated releases are dated by January 1, 2018, reproducing the prior 355-later-or-missing count.

This is an associated-release information rule, not a claim that all underlying concerns were then unknown. Earlier disclosures can exist. Under this rule, the original validation AP cannot be described as a historically available labeled-positive validation exercise at the refit cutoff. A partial availability filter on refitting cannot repair the future-informed validation or historical control selection.

## All 26 linked release headers

evaluation_release_header_verification.csv records a manual comparison of all 26 representative evaluation URLs against the official PDF first page or HTML release header. Scope is publication date and associated release number only, not every alleged quarter, respondent identity or category.

One linked-document mismatch was found. For FirstEnergy, the retained source metadata say AAER-4517, September 9, 2024, while the linked official order 33-11302 says AAER-4519, September 12, 2024. Ten original positive source rows have that mismatched pair. Nine of those economic observations also have a separate AAER-4519 row; selecting the earliest source date keeps the mismatched representative. All ten remain positive observations and both dates are far later than the refit cutoff. The corrected header is recorded separately without silently changing model inputs, identifiers or scores. This is a metadata correction, not a determination about every episode-quarter label.

## Targeted earlier public events

verified_public_events.csv records three manually checked public events from official sources. They are not certified first-discovery dates. Lordstown and FirstEnergy were selected for targeted case review after results had been seen. Their histories are not representative of all cases.

The Lordstown order, AAER-4490, documents a March 12, 2021 short-seller report questioning preorder statements and a June 14, 2021 public special-committee statement that certain statements were inaccurate. The allegation is not itself a finding of wrongdoing. Three selected Lordstown reports were originally filed after March 12, while two were filed after June 14. In particular, the March 31, 2021 report was filed June 8, after the allegations but before the committee statement. A different information definition changes whether it is considered already public.

FirstEnergy's official order documents a July 23, 2020 public issuer response to the Householder investigation. Its original Form 8-K and attached press release were also inspected; the release explicitly addresses that investigation. Two selected FirstEnergy reports were filed after this event: the June 30, 2020 report on August 17, 2020, and the March 31, 2021 report on April 22, 2021. The first report period predates the response but its filing follows it, demonstrating why period end is not decision-time availability.

Across the two firms, five distinct selected positive reports were filed after one of the documented public concerns/responses. Four were filed after the more conservative issuer statement/response dates. Earlier reports remain classified only as before the selected event, never as verified before all public information. No such conclusion is inferred for other firms whose histories remain unresolved. No case was selectively removed to generate a supposedly clean pre-discovery predictive result.

## Entity continuity

Four positive observations under the later Lordstown CIK have periods and original filings before October 2020, when the official order says Lordstown became public through the DiamondPeak combination. The inspected June 2019 Form 10-Q identifies DiamondPeak as a blank-check company with no operating revenue. These are public-issuer predecessor financials, not operating-company Lordstown statements for those periods. Legal CIK continuity does not establish unchanged business identity. This flags a mapping/interpretation issue, rather than automatically adjudicating the four labels as false or the predecessor as misconduct-free.

## Reproduce

The original analyze.py run writes generated_test_scores.csv locally. Download the pinned source files and run that pipeline first. Then:

```sh
python3 code/audit_episode_timing.py --source-dir local_sources --bootstrap 1000
python3 code/verify_episode_timing.py
```

The episode audit needs numpy, pandas and scikit-learn from requirements.txt. Per-observation scores are not redistributed; rerun the original pipeline to obtain them. The packaged event associations, public dates, filing dates, header comparisons, metrics and intervals can be inspected offline. verify_episode_timing.py checks internal consistency offline, but that is not a substitute for full score recomputation or external expert case review.
