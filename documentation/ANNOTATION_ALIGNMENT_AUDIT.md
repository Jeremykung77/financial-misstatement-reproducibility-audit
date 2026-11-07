# Annotation compatibility and outcome definition

## Resources and scope

This is an exploratory audit of additional artifacts at the original pinned Hugging Face revision b4c976c8662bc7f24568d71f30a41eeccb677f85. df_aaer_with_misstatements_since_2009.csv has 1,451 rows, all unique by CIK/fiscal quarter, and 256 retained AAER/CIK pairs. AAER_DETAILS.zip has 3,210 JSON members. Four exact downloaded inputs, including two companion scripts at Git commit 8c292f2af557f4153f4f605668756c9ce5a4c870, are fingerprinted in annotation_source_manifest.csv. Both script bytes match the Git tree blobs. Raw third-party annotations, generated descriptions and full scripts are not redistributed. No new generative-model request was made.

The narrower annotation resource is not a validated replacement for the benchmark. Different outcome scopes, retained release associations, extraction omissions, fiscal interpretation and artifact versions can cause disagreement. This audit preserves every original model result and label. It does not estimate a population label-error rate or fit a corrected outcome.

## Join and denominators

The benchmark is deduplicated by CIK, financial fiscal year and financial quarter using the original earliest-source-date rule, preserving all 14,657 economic observations. The annotation comparison string is formed from those financial year/quarter fields. The annotation-derived fiscal_quarter column in the split cannot supply this key for controls because it is blank there. Using it would collapse distinct negative company quarters; the code asserts the original cohort counts before comparison.

Eight stage/outcome rows in annotation_match_by_stage.csv report all 628 positives and 14,029 controls. The evaluation still has 2,695 observations, including 93 positives and 2,602 controls. Thirty-four of those positives have a same-company/fiscal-quarter annotation. Twenty-six also match the retained representative AAER; 31 match at least one original AAER before deduplication. Fifty-nine have no company-quarter annotation. The 34/26/31 counts describe compatibility, not 34 verified true positives or 59 proven false labels.

Fourteen benchmark controls have same-company/quarter annotations: seven development, five validation, one gap and one evaluation. annotation_control_candidates.csv lists these public identifiers and links without relabeling them. They are candidates for substantive review, not fourteen independently confirmed intentional-fraud cases. The one evaluation candidate is report 123494, Compass Minerals, CIK 1227654, period September 30, 2019, mapped to AAER-4340 in the narrower resource.

## Source processing and association loss

The inspected companion SYSTEM_PROMPT targets numerical earnings/account misstatements and excludes purely disclosure-related cases. It instructs the model to expand an implicated full year into all four quarters and repeat year-level information. This creates inferred quarterly coverage rather than four independently cited quarterly findings. Inspection establishes a prompt rule; it does not prove how each released annotation was produced, which model generated it or whether a particular expansion is wrong.

The preprocessing script skips empty misstatement lists. Its duplicate condition uses CIK and fiscal quarter without AAER, retaining an existing row when another release concerns the same company/quarter. Consequently, strict representative-AAER matching alone is not sufficient to establish missing event evidence. The inspected code and current table are consistent with consolidation, but a complete replay and exact production lineage are not certified. The implementation's pandas update behavior and every combined category have not been validated here.

Only 13 of the 26 representative evaluation releases have files in the supplied details archive. The largest numeric AAER in the archive is 4477; suffix variants are counted as separate files. The narrower CSV includes some later releases absent from that archive. Missing recent archive members therefore must not be treated as empty source evidence. The entire 3,210-member archive has not been manually adjudicated or reproduced through an extraction model.

## Three bounded case checks

**Compass Minerals.** The original benchmark marks report 123494 as a control. The official AAER-4340 order, printed page 11, paragraphs 44-45, describes a non-GAAP interim inventory methodology and states that quarterly segment results from 2019Q1 through 2021Q1 were restated. The report period falls within that interval. This is source evidence that an apparently unlinked control can overlap an enforcement-associated accounting-misstatement period. It does not adjudicate intentional fraud, prove the narrower narrative's specific direction or amount of error, or supply every original restated balance. Labels remain unchanged. The other thirteen control candidates are not certified by this one review.

**Surgalign.** The two evaluation positives (reports 581/583, 2019Q2/Q3) use AAER-4318 as their representative source. The narrower file places both under AAER-4319, which is among the benchmark's original alternative associations. The AAER-4318 order, printed page 7, paragraph 21, explicitly describes a restatement of the first three quarters of 2019. The companion official AAER-4319 release identifies the same broader case and 2014-2019 restatement. These positives are not missing from the entire narrower table. This case corrects the initial same-release-only reading and shows why association-sensitive matching is necessary.

**Lordstown.** None of its seven benchmark positives matches the narrower table's 2020Q3/Q4 entries. The official order, printed page 10, paragraphs 37-41, separately discusses the then-private operating company's 2019 accounts and the later audit/proxy filings. Therefore the 2019 date alone does not establish that 2019 is outside every accounting issue. Conversely, private operating-company accounts do not establish that earlier standalone DiamondPeak balances are misstated. The four predecessor observations remain an entity-mapping concern requiring account and filing evidence. They are not automatically flipped to negative.

The manually inspected sources and locators appear in annotation_case_verification.csv. These are targeted case checks within the same research workflow, not independent expert adjudication of all companies or quarters.

## Reproduce

```sh
python3 code/fetch_sources.py --dest local_sources
python3 code/fetch_annotation_sources.py --dest annotation_sources
python3 code/audit_annotation_alignment.py --source-dir local_sources --annotation-dir annotation_sources
python3 code/verify_annotation_alignment.py
```

The first fetcher retrieves the original three financial inputs; the new fetcher adds about 6.37 MB of annotation inputs and companion scripts. The annotation audit needs pandas, but no model scores or refitting. Hash mismatches stop execution. The offline verifier checks supplied crosswalks and denominators; it cannot independently verify legal findings, fiscal mappings or all LLM-derived categories.


## Revision 8 follow up

The preceding three-case discussion records revision 7. All fourteen control candidates have since received source-scope review, documented in CONTROL_CANDIDATE_REVIEW.md and control_candidate_review.csv. This supersedes the earlier statement that thirteen candidates were not individually reviewed; it does not change the compatibility counts, original labels or scores.
