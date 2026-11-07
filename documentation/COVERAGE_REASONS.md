# Selected-accession component availability

Added 7 November 2026 after the benchmark and initial measurement audit. This is an exploratory coverage diagnostic. It does not alter the frozen financial predictors, outcomes, fitted scores or original ratio comparisons.

## Provenance and attribution

The additional file data/sec_component_availability.csv contains 960 derived records: eight accounting components for each of the 120 existing pilot observations. The original sources are the 53 SEC companyfacts JSON payloads already listed, with exact URLs and SHA256 digests, in sec_source_manifest.csv. The extraction run checked every payload against that manifest. The code does not silently download a newer API response. SEC information and filing definitions remain attributable to the U.S. Securities and Exchange Commission and the underlying issuers. These derived API coverage counts are additional to the original extracts described in data/ATTRIBUTION.md; they are not a new licensed third-party financial panel.

The eight components are net income, assets, current assets, current liabilities, inventory, revenue, gross profit and operating income. Exact eligible US-GAAP tags are in code/audit_coverage_reasons.py. Assets and the other balance-sheet components require an instant context. Flow components require 60–120 inclusive days. A fact must use USD and match both the selected accession and exact report end. The same strict reconstruction rules govern the original extension comparisons.

## Component fields

| Field | Definition |
| --- | --- |
| report_id | Original pilot observation identifier; join to sec_pilot_filing_extract.csv for CIK, accession and report date |
| component | One of the eight specified components |
| matched | Whether an original filing with the exact supplied report date was found |
| exact_accession_end_USD_facts | Number of API fact records for the admitted tags, USD unit, selected accession and end, before eligibility filtering |
| eligible_facts | Count passing the instant/duration rule, including repeated identical entries |
| distinct_eligible_context_values | Number of distinct start/value pairs after eligibility filtering |
| single_start | Flow start when there is exactly one eligible pair; blank for instant components or unavailable/ambiguous components |
| single_value | USD value when exactly one eligible pair exists; otherwise blank |

Unmatched reports have zero component counts. Distinct context/value pairs, not the raw number of duplicate entries, determine ambiguity. API absence does not establish absence from the original filing: custom tags and unsupported contexts can be excluded from companyfacts.

## Decomposition and reproduction

The five original extension ratios request 600 comparisons. code/audit_coverage_reasons.py reproduces all 370 computable values to relative/absolute tolerance 1e-12 and reproduces all 230 unavailable statuses. It records every detected component obstacle in sec_unavailable_reason_detail.csv. An exclusive category uses this fixed priority: unmatched report date; absent selected-accession USD fact; no eligible context/duration; ambiguous eligible component; incompatible flow starts; zero denominator. Thus counts are not a causal decomposition when several component problems coexist.

The exclusive unavailable counts are 65, 136, 8 and 21 for the first four obstacles. The last two checks have zero remaining failures. results/sec_unavailable_reason_summary.csv preserves each feature's seven-category partition including computable. results/coverage_reason_verification.json reports the executed identities.

Offline mode uses the included component records. The --cache mode independently re-extracts them from the retained hash-checked companyfacts payloads, then performs the same comparisons. The raw payload cache is not in this distribution. Neither mode supplies a probability sample or a complete reconstruction of the upstream production pipeline. No overall source-error rate is estimated.
