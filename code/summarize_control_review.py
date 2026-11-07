"""Check the frozen candidate universe and summarize manual source-scope readings.

Python standard library only. This does not automatically verify legal truth,
reconstruct financial amounts, change labels, or estimate model performance.
"""
from collections import Counter
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = {
    'explicit_quarter_support': 'Explicit quarterly scope or stated quarterly restatement interval',
    'annual_or_scheme_period_only': 'Annual or scheme-period support without individual-quarter confirmation',
    'controls_or_transaction_scope': 'Control or transaction issue without numerical report-misstatement finding',
    'outside_cited_scheme_period': 'Candidate period outside the cited underlying scheme',
}


def read(path):
    with path.open(newline='') as f:
        return list(csv.DictReader(f))


def write(path, rows, fields):
    with path.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main():
    candidates = read(ROOT/'results/annotation_control_candidates.csv')
    review = read(ROOT/'documentation/control_candidate_review.csv')
    sources = read(ROOT/'documentation/control_source_verification.csv')
    checks = {}

    def check(name, condition):
        checks[name] = bool(condition)
        if not condition:
            raise ValueError(name)

    original = {r['report_id']: r for r in candidates}
    checked = {r['report_id']: r for r in review}
    check('candidate_and_review_ids_unique', len(original) == len(candidates) == len(checked) == len(review))
    check('entire_previously_frozen_universe_reviewed', set(original) == set(checked) and len(review) == 14)
    check('all_original_candidate_fields_preserved', all(all(checked[k][f] == v for f, v in r.items()) for k, r in original.items()))
    check('all_original_labels_zero_and_preserved', all(r['benchmark_positive'] == '0' and r['original_label_preserved'] == '1' for r in review))
    check('only_declared_categories', all(r['review_category'] in CATEGORIES for r in review))
    check('each_reading_has_locator_status_scope_and_boundary', all(all(r[x].strip() for x in ['linked_source_locator', 'legal_document_status', 'verified_scope', 'inference_boundary', 'review_date', 'review_workflow']) for r in review))
    check('related_source_and_locator_are_paired', all(bool(r['related_primary_url']) == bool(r['related_source_locator']) for r in review))
    source_urls = {r['primary_url'] for r in sources}
    check('15_unique_source_urls', len(sources) == len(source_urls) == 15)
    check('all_sources_official', all(u.startswith('https://www.sec.gov/') for u in source_urls))
    check('every_cited_primary_source_registered', all(r['annotation_url'] in source_urls and (not r['related_primary_url'] or r['related_primary_url'] in source_urls) for r in review))
    counts = Counter(r['review_category'] for r in review)
    stages = Counter(r['stage'] for r in review)
    check('candidate_stage_denominators_preserved', stages == {'development': 7, 'validation': 5, 'gap': 1, 'evaluation': 1})
    check('all_candidates_in_one_category', sum(counts.values()) == len(review))
    check('evaluation_candidate_remains_compass', [r['report_id'] for r in review if r['stage'] == 'evaluation'] == ['123494'])
    check('no_independent_human_review_claim', all('not independent human expert' in r['review_workflow'] for r in review))

    totals = [{'category': c, 'description': d, 'candidate_records': counts[c]} for c, d in CATEGORIES.items()]
    cross = [{'stage': s, 'category': c, 'candidate_records': sum(r['stage'] == s and r['review_category'] == c for r in review)} for s in ['development', 'validation', 'gap', 'evaluation'] for c in CATEGORIES]
    write(ROOT/'results/control_review_summary.csv', totals, ['category', 'description', 'candidate_records'])
    write(ROOT/'results/control_review_by_stage.csv', cross, ['stage', 'category', 'candidate_records'])
    (ROOT/'results/control_review_verification.json').write_text(json.dumps({
        'all_pass': all(checks.values()), 'checks': checks,
        'candidate_records': len(review), 'source_documents': len(sources),
        'category_counts': dict(counts), 'stage_counts': dict(stages),
        'no_model_fit_relabel_or_metric_change': True,
        'scope': 'Mechanical consistency of a source-reading register. Classifications are manual interpretations within the same research workflow, not independently validated labels or legal adjudication.'
    }, indent=2)+'\n')
    print(json.dumps({'all_pass': all(checks.values()), 'checks': len(checks), 'category_counts': dict(counts)}, indent=2))


if __name__ == '__main__':
    main()
