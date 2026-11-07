# Data provenance and interpretation

Access date is 6 November 2026 in Australia/Brisbane. File hashes, exact URLs, byte counts and declared licenses are in source_manifest.csv. Financial source revision is b4c976c8662bc7f24568d71f30a41eeccb677f85. Preserve this revision when reproducing.

## Financial benchmark actually analyzed

Source: WaguyMZ/Financial_statements_fraud_dataset, original creator's Hugging Face repository. The card declares GPL without specifying a version. This is a public research release, not an independent legal clearance of every upstream component. Raw Hugging Face tables are not redistributed. Retrieval code uses their original host. No paid database, private account, access bypass or unauthorized mirror was used.

The downloaded train/test tables are 11364 x 34 and 3507 x 34. Their concatenation has 14871 rows and 14657 unique economic observations. All 214 surplus rows are repeated positive company quarters. There are no conflicting labels within CIK/fiscal-year/quarter keys. Keep the earliest linked AAER date among repeated keys; no assertion that it is the first public disclosure. The full financial table is 269097 x 96. Join by CIK/year/quarter, unique in that table, and require exact period equality. The split report_id is NOT the full financial row index. A trial index join was rejected by identity assertions before any model fit.

The source split is not strict chronological order by period: training maximum is 20180630 and test minimum is 20170930, with ten shared period values. There are no shared report IDs or shared economic keys across the two files, so a common reporting date is not itself an identical-observation leak. They share 1740 CIKs, which is allowed for a recurring-company target but does not test new-company generalization. The card's simple 2009-2019 / 2020-2021 description is not the observed snapshot. The associated preprint describes another sample size. This study reanalyzes the pinned release and does not reproduce the authors' exact original experiment.

The primary target is is_fraud, an eventual enforcement-associated indicator. Three original positive rows lack FinancialMistatement in their generalized category; the target is therefore not exclusively narrow financial statement fraud. Enforcement can concern reporting errors or controls, and does not universally establish intentional criminal fraud. Unlinked records are unlabeled controls, not verified honest firms. Controls were already sampled by the source authors. Neither test prevalence nor predictive precision is a population estimate.

## Field roles

- cik: entity grouping, joining and bootstrap only. Excluded from predictors.
- year and quarter: source fiscal key. They need not equal calendar period. Excluded from predictors.
- period: report period ending YYYYMMDD, used to split. This is not filing or acceptance date.
- report_id: source split row identity; retained for reproducibility and never a feature or tie breaker.
- is_fraud: eventual outcome only.
- aeer_date, aaer_no, role, url, labels, glabels, num_glabels, summary, complaints: enforcement metadata. Excluded. AAER presence is used only as an explicitly invalid leakage diagnostic.
- serial_count, total_serial_count, cik_reports_count: outcome sequence or full-horizon counts. Excluded.
- mda identifiers, sic, sicagg and all n_* coverage counts: excluded.
- Twelve ratio_* columns in results/feature_audit.csv: modeled predictors. They represent profitability, liquidity, leverage and asset efficiency in the released processed data. Signed log transformation z=sign(x)log(1+abs(x)), training median imputation and scaling. No future difference or supplied Beneish score features are used.

Zero is distinct from missing in the released CSV. No modeled feature has an explicit missing value in the final cohort. Several zero rates are high, including debt/assets around 75%; upstream imputation may be responsible. There is insufficient accession-level evidence here to certify original filing values, units, fiscal recalculation, or the point-in-time imputation procedure. This is a material limitation even after the train-only transformations in our code.

## Corrected analysis cohorts

Development: reports ending through 2015, 7799 records / 342 positives. Validation: 2016-2017, 3069 / 133. Refit combines these, 10868 / 475. Gap: 2018, 1094 / 60 excluded. Final test: 2019-2021, 2695 / 93, including 26 positive firms. A fixed-model unseen-company subset contains 945 / 21. Positive-only availability sensitivity excludes 355 refit positives whose linked release date was missing or later than 2018-01-01; 10513 / 120 remain. Validation and cohort selection still use eventual labels, so this is only a partial stress test.

## Revision 2 diagnostics

All additions were specified after inspecting the original evaluation. No independent untouched evaluation cohort is claimed. The main cohort and main ranking metrics are unchanged. baseline_skill_intervals.csv subtracts constant-score AP within the same 1000 firm resamples; all three 95% intervals include zero. posthoc_robustness.csv reports fixed-parameter narrow-category exclusion, SIC 6000-6999 exclusion and zero-pattern-only models. Classification thresholds are not transferred into these revised conditions or the partial availability refit. positive_firm_influence.csv removes evaluation records only, without refitting. sector_feature_audit.csv describes source ratios and does not infer that zeros are necessarily errors.

The narrow condition excludes two refit positives and one evaluation positive lacking the generalized FinancialMistatement label. It leaves 2694 evaluation rows and 92 positives; there is no recoding of those excluded cases into controls. The SIC exclusion condition leaves 2049 evaluation rows and 88 positives. Zero-pattern diagnostics use indicator(released ratio == 0), preserve all 2695/93 evaluation records and do not establish an economic or processing mechanism.

## AAER register actually analyzed

Source: Amin and Aßenmacher (2025), 10k-fraud-detection v1.0.0, DOI 10.5281/zenodo.17121948, aaer_mark5.csv. Zenodo declares CC BY 4.0. Provider MD5 was independently matched. Read using semicolon delimiter. 570 label records, 534 CIKs and 553 AAER identifiers. This is a selected positive register, not 570 unique frauds or a population panel. Repeated firms/AAERs can represent distinct episodes, categories or respondents.

Fields: dateTime is linked AAER release timestamp; fraud_start and fraud_end are coded month-year; certainty_start/end identify author-coded timing certainty; fsf, amis and corruption are category flags, not predictor measurements. Remove zero-width characters from dateTime and parse the first ten characters. Interpret month starts at first day and ends at calendar month end. Lag=(release_date-coded_end_date)/365.25 years. This is linked-release lag, not discovery lag. The overall median weights each selected register row equally; it is not an independent-event-weighted or population estimate. Two records have negative lag and remain visible. Twenty-six id entries are missing; CIK/AAER and physical row order are retained instead of inventing identifiers.

The full 5.6 GB 10-K text corpus was not downloaded, fitted, or evaluated. Only the small label register was analyzed. Do not infer text-model or LLM performance from this study.

The fsf category is one in 478 rows, explicitly zero in 18, and missing in 74. The companion author preprocessing fills category blanks with zero. This audit preserves and reports raw blanks separately as an encoding diagnostic, without claiming the source processing convention is a mistake. Median linked-release lag is 3.1814 years among fsf=1 and 3.1732 among the 319 fsf=1 records with both dates marked certain. The amis and corruption columns have 453 and 399 missing entries. No missing category is silently counted as a verified negative.

## UCI audit data actually analyzed

Source: Hooda (2018), UCI Audit Data, DOI 10.24432/C5930Q; CC BY 4.0. Original archive contains audit_risk.csv and trial.csv. Only audit_risk.csv is analyzed; trial.csv is supplied untouched and is not an independent test set. The web page lists 777 instances; the downloaded audit CSV has 776 rows, 305 positive Risk labels and 13 exact duplicate rows. Money_Value has one missing observation. No per-row longitudinal date or stable firm ID is supplied. Audit_Risk>1 equals Risk in all rows. Audit_Risk equals Inherent_Risk x CONTROL_RISK x Detection_Risk up to floating point precision. These are full-snapshot algebra checks, not held-out classifier results.

## Revision 3 original filing audit

The separate SEC pilot now reconstructs four explicitly defined ratios for selected observations. It does not certify original filing provenance for all twelve modeled columns or the complete cohort. See SEC_PILOT_DATA.md, SEC_PILOT_PLAN.md and SEC_PILOT_SELECTION.csv for source timing, exact-date failures, coverage denominators, definition reconciliation, the residual prior-period fingerprint and raw-cache reproducibility limits. Additional source inspection and manuscript revision continued into 7 November 2026 Australia/Brisbane; actual API retrieval times are recorded in UTC.

## Revision 4 measurement scope

Five further explicit ratios are compared against original-accession facts under strict duration/context rules. Source zero values are retained for the benchmark and not silently treated as economic break-even. MEASUREMENT_AUDIT.md distinguishes source code inspection, actual isolated AST replay, API reconstruction, raw-snapshot limitations and unadjudicated discrepancies. predictor_formula_dictionary.csv covers all twelve modeled column names and their verification limits. The original full financial table and the modeled cohort have very different q4 representation; zero rates must be quoted with their denominator.

## Revision 5 source episode and public information boundaries

Deduplication is on the economic observation key, not on a verified real-world scheme. Among source positive keys, 141 have multiple original release associations. The new episode audit preserves these associations as a sensitivity rather than declaring them accidental identical duplicates. Twenty-six representative evaluation URLs have manually checked ID/date headers; the FirstEnergy inconsistency is recorded separately and not used to silently alter raw source tables or original model inputs. Targeted public dates identify reports filed after a documented concern, not a complete first-discovery panel. Detailed scope and reproduction are in EPISODE_AND_TIMING_AUDIT.md.

Revision 6 adds aggregate AP-reference and calendar-period budget outputs only. No new source records or per-report scores are redistributed. The analytical random reference is a derived quantity, not an observed performance trial. Full recomputation requires the pinned original financial sources and locally regenerated scores.

Revision 7 uses two separately pinned annotation artifacts and two exact companion source files; see annotation_source_manifest.csv. The package includes derived public-identifier crosswalks and aggregate counts, not raw third-party narratives, archive contents or full source code. Candidate controls and absent annotations are not silent label corrections.


Revision 8 adds a complete official-source scope review of the fourteen frozen annotation/control candidates. control_candidate_review.csv preserves every original candidate field and label; control_source_verification.csv lists fifteen official documents and locators. These source-reading classifications are not independently validated outcomes. See CONTROL_CANDIDATE_REVIEW.md. No source data, financial features, fitted models, labels, or existing result files are changed.

## Focused release coverage diagnostic

The focused manuscript release adds data/sec_component_availability.csv, with 960 component records derived from the original 53 hash-checked SEC companyfacts payloads. COVERAGE_REASONS.md defines its fields, source attribution, context rules, exclusive-priority classification and offline versus raw-cache verification scope. This descriptive addition accounts for all 230 unavailable requests in the existing five-ratio extension without replacing any benchmark input or original result. The four publication figures use retained metrics, intervals and locally generated frozen scores; no new evaluation cohort or fitting is added.
