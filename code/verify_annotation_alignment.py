"""Offline crosswalk checks; manual legal/financial judgment is not automated here."""
from pathlib import Path
from collections import Counter
import csv,json

ROOT=Path(__file__).resolve().parents[1]
def read(name,folder='results'):
    with (ROOT/folder/name).open() as f:return list(csv.DictReader(f))
s=json.loads((ROOT/'results/annotation_alignment_summary.json').read_text())
stages=read('annotation_match_by_stage.csv');positive=read('evaluation_positive_annotation_crosswalk.csv')
controls=read('annotation_control_candidates.csv');cases=read('annotation_case_comparison.csv');archive=read('annotation_archive_coverage.csv')
manual=read('annotation_case_verification.csv','documentation');manifest=read('annotation_source_manifest.csv','documentation')
old={r['report_id']:r for r in read('evaluation_episode_overlap.csv')}
checks={
 'all_original_cohort_records_accounted_for':sum(int(r['records']) for r in stages)==14657 and sum(int(r['records']) for r in stages if r['benchmark_positive']=='1')==628,
 'all_93_evaluation_positives_unique':len(positive)==93 and len({r['report_id'] for r in positive})==93,
 'crosswalk_preserves_original_positive_IDs_and_source_AAERs':set(old)=={r['report_id'] for r in positive} and all(r['representative_AAER']==old[r['report_id']]['source_AAER'] for r in positive),
 'matched_fiscal_keys_are_derived_from_financial_fields':all(len(r['financial_fiscal_quarter'])==6 and r['financial_fiscal_quarter'][4]=='q' and r['financial_fiscal_quarter'][-1] in '1234' for r in positive+controls),
 'evaluation_match_counts_34_26_31':sum(int(r['company_quarter_annotation']) for r in positive)==34 and sum(int(r['exact_representative_AAER_match']) for r in positive)==26 and sum(int(r['any_original_AAER_match']) for r in positive)==31,
 'release_match_rules_are_nested':all(int(r['exact_representative_AAER_match'])<=int(r['any_original_AAER_match'])<=int(r['company_quarter_annotation']) for r in positive),
 'stage_match_partitions':all(int(r['no_annotation'])+int(r['company_quarter_annotation'])==int(r['records']) and int(r['exact_representative_AAER_match'])+int(r['other_AAER_only'])==int(r['company_quarter_annotation']) for r in stages),
 'fourteen_candidate_controls_with_one_in_evaluation':len(controls)==14 and Counter(r['stage'] for r in controls)=={'development':7,'validation':5,'gap':1,'evaluation':1} and all(r['benchmark_positive']=='0' for r in controls),
 'Compass_candidate_is_original_2019Q3_control':any(r['report_id']=='123494' and r['cik']=='1227654' and r['financial_fiscal_quarter']=='2019q3' and r['period']=='20190930' and r['annotation_AAER']=='AAER-4340' for r in controls),
 'twenty_six_cases_and_archive_coverage_records':len(cases)==26 and len(archive)==26 and sum(int(r['evaluation_positives']) for r in cases)==93,
 'thirteen_representative_releases_in_archive':sum(int(r['present_in_details_archive']) for r in archive)==13 and s['archive_json_records']==3210,
 'Lordstown_narrow_quarters_do_not_match_seven_benchmark_rows':any(r['cik']=='1759546' and r['evaluation_positives']=='7' and r['company_quarter_matches']=='0' and r['same_release_annotation_quarters']=='2020q3;2020q4' for r in cases),
 'Surgalign_two_rows_preserved_under_alternative_release':any(r['cik']=='1760173' and r['evaluation_positives']=='2' and r['company_quarter_matches']=='2' and r['representative_release_matches']=='0' for r in cases) and all(r['annotation_AAER']=='AAER-4319' and r['any_original_AAER_match']=='1' for r in positive if r['cik']=='1760173'),
 'three_explicit_manual_case_sources':len(manual)==3 and {r['cik'] for r in manual}=={'1759546','1760173','1227654'} and all(r['primary_url'].startswith('https://www.sec.gov/') and r['boundary'] for r in manual),
 'four_pinned_nonredistributed_source_inputs':len(manifest)==4 and all(r['redistributed']=='No' and len(r['sha256'])==64 for r in manifest),
 'no_refit_or_relabeling_declared':s['no_fit_relabel_or_metric_change'],
}
result=dict(checks=checks,all_pass=all(checks.values()),scope='Offline internal identities and denominators; no automated case adjudication or population label-error estimate')
(ROOT/'results/annotation_alignment_verification.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
if not result['all_pass']:raise SystemExit(1)
