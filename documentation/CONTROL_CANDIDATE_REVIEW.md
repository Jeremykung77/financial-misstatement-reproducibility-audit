# Official source review of annotated controls

## Scope and timing

This exploratory follow-up reviews the complete fourteen-record candidate list produced in revision 7, including the thirteen candidates not individually checked at that stage. The candidate universe was fixed before this follow-up; initial document inspection preceded the revision 8 plan. The categories were developed during source inspection and are not preregistered. No additional control search or new predictive evaluation is presented.

The review compares a candidate's recorded period with the scope of its exact linked SEC document and, where necessary, a related original release or complaint. Fifteen distinct official documents were inspected. The source register records the documents and locators; the candidate register preserves every field of the original list, the legal/procedural context, the evidence interpretation and its boundary. This is source inspection within the same research workflow, not independent human expert adjudication. Current final dispositions of every underlying proceeding have not been researched.

## Findings

| Evidence category | Records |
| --- | --- |
| Explicit quarterly scope or stated quarterly restatement interval | 5 |
| Annual or scheme-period support without individual-quarter confirmation | 4 |
| Control or transaction issue without numerical report-misstatement finding | 2 |
| Candidate period outside the cited underlying scheme | 3 |

The stage totals remain seven development, five validation, one excluded gap and one evaluation. The sole evaluation candidate remains Compass report 123494. The four categories are mutually exclusive summaries of support for the particular recorded quarter. Explicit support can occur in a complaint or in a document reciting allegations; it does not automatically imply a final finding of intent. A period outside a cited scheme is not proof of a clean report. Broad annual coverage and a professional order's publication date do not establish a separate quarterly misstatement.

Cross-document association is material: MiMedx 2015Q2 has annual-only scope in the directly linked auditor document, but explicit quarterly scope in the related Senken order already inspected for another candidate. Including that related document raises explicit support from an initial four to five and reduces the annual/broad-period group to four. This refinement occurred during the exploratory review, before release; a direct-link-only interpretation would discard known case evidence.

The record-level register supplies the source-specific reasoning rather than treating an annotation as sufficient evidence. Fiscal conventions, the accounting entity, original amounts, amendments and first public disclosure remain separate reconstruction questions. The review does not estimate a population mislabeling rate or determine which label errors caused weak model performance. All original features, economic observations, labels, scores and existing result files remain unchanged. No corrected-label AP, new model fit or new holdout is claimed.

## Files and reproduction

- documentation/control_candidate_review.csv: fourteen records, original identifiers plus source-scope readings and procedural status.
- documentation/control_source_verification.csv: fifteen official URLs, dates and inspected locators.
- results/control_review_summary.csv: four category counts.
- results/control_review_by_stage.csv: complete stage/category cross-tabulation, retaining zero cells.
- results/control_review_verification.json: fourteen mechanical consistency assertions and explicit scope limits.

From the package directory, run `python3 code/summarize_control_review.py`. Only the Python standard library and included CSVs are required. The script checks that the frozen universe, all original fields, stage denominators, source coverage and original labels are preserved, then regenerates the summary files. It cannot independently decide whether a legal or accounting interpretation is correct. Full source reading remains necessary; URLs identify official public documents rather than an inferred replacement outcome dataset.
