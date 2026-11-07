"""Offline checks of episode/timing outputs. Full score recomputation needs original sources."""
from pathlib import Path
from collections import Counter
from datetime import date
import csv,json,math
ROOT=Path(__file__).resolve().parents[1]
def read(name):
    with (ROOT/name).open() as f:return list(csv.DictReader(f))
overlap=read('results/evaluation_episode_overlap.csv');metrics=read('results/episode_proxy_subset_metrics.csv')
ci=read('results/episode_proxy_subset_intervals.csv');headers=read('documentation/evaluation_release_header_verification.csv')
timing=read('results/public_event_filing_timing.csv');stages=read('results/stage_label_availability.csv')
checks={
 'all_93_positive_records_preserved':len(overlap)==93 and len({r['report_id'] for r in overlap})==93,
 'source_proxy_overlap_26_and_29':sum(int(r['representative_proxy_seen_in_refit']) for r in overlap)==26 and sum(int(r['any_proxy_seen_in_refit']) for r in overlap)==29,
 'all_associations_conservative_superset':all(int(r['any_proxy_seen_in_refit'])>=int(r['representative_proxy_seen_in_refit']) for r in overlap),
 'two_subsets_four_fixed_models':len(metrics)==8 and len({(r['setting'],r['model']) for r in metrics})==8,
 'all_2602_controls_retained':all(int(r['records'])-int(r['positives'])==2602 for r in metrics),
 'changed_denominators_explicit':all((int(r['records']),int(r['positives']),int(r['excluded_positive_rows']))==((2669,67,26) if r['setting']=='exclude_representative_shared_proxy' else (2666,64,29)) for r in metrics),
 'constant_AP_matches_subset_fraction':all(math.isclose(float(r['AP']),int(r['positives'])/int(r['records']),rel_tol=1e-12) for r in metrics if r['model']=='prevalence'),
 'AP_and_retrieval_ranges':all(0<=float(r['AP'])<=1 and 0<=float(r['precision_5pct'])<=1 and 0<=float(r['recall_5pct'])<=1 for r in metrics),
 '1000_valid_cluster_replicates':len(ci)==8 and all(int(r['valid_bootstrap_replicates'])==1000 for r in ci),
 'all_subset_skill_intervals_include_zero':all(float(r['skill_lower'])<=0<=float(r['skill_upper']) for r in ci if r['model']!='prevalence'),
 '26_official_headers_one_mismatch':len(headers)==26 and sum(r['header_match']=='0' for r in headers)==1,
 'FirstEnergy_mismatch_adjudicated':any(r['cik']=='1031296' and r['source_AAER']=='AAER-4517' and r['source_date']=='2024-09-09' and r['verified_linked_document_AAER']=='AAER-4519' and r['verified_linked_document_date']=='2024-09-12' for r in headers),
 'validation_linked_release_unavailable_at_cutoff':any(r['stage']=='validation' and r['positive_records']=='133' and r['linked_date_by_cutoff']=='0' for r in stages),
 'refit_availability_matches_prior_analysis':any(r['stage']=='refit' and r['positive_records']=='475' and r['linked_date_by_cutoff']=='120' for r in stages),
 'strictly_later_filing_rule':all(date.fromisoformat(r['original_filing_date'])>date.fromisoformat(r['event_date']) for r in timing if r['relation']=='after_documented_event'),
 'five_distinct_reports_after_documented_concern':len({r['report_id'] for r in timing if r['relation']=='after_documented_event'})==5,
}
result={'checks':checks,'all_pass':all(checks.values()),'scope':'Internal consistency and denominator checks; not independent expert verification of first discovery or every event-quarter mapping'}
(ROOT/'results/episode_timing_verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if not result['all_pass']:raise SystemExit(1)
