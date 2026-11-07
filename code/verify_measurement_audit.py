"""Independent arithmetic/denominator checks within the same research workflow."""
from pathlib import Path
from datetime import date
from collections import Counter
import csv,json,math
ROOT=Path(__file__).resolve().parents[1]
def read(name):
    with (ROOT/name).open() as f:return list(csv.DictReader(f))
facts=read('data/sec_extended_fact_extract.csv');comparisons=read('results/sec_extended_ratio_comparison.csv')
filings={r['report_id']:r for r in read('data/sec_pilot_filing_extract.csv')}
summaries=read('results/sec_extended_summary.csv');quarter=read('results/quarter_zero_patterns.csv')
checks={
    'five_features_120_each':len(comparisons)==600 and set(Counter(r['feature'] for r in comparisons).values())=={120},
    'no_duplicate_feature_observations':len({(r['report_id'],r['feature']) for r in comparisons})==600,
    'exact_original_accession_end_and_USD':all(r['accession']==filings[r['report_id']]['accessionNumber'] and r['end']==filings[r['report_id']]['reportDate'] and r['unit']=='USD' for r in facts),
    'quarterly_duration_not_annual':all(not r['start'] or 60<=(date.fromisoformat(r['end'])-date.fromisoformat(r['start'])).days+1<=120 for r in facts),
    'comparison_partition':Counter(r['status'] for r in comparisons)=={'match':322,'different':48,'unavailable':230},
    'no_zero_fill_for_unavailable':all(r['original_accession_ratio']=='' for r in comparisons if r['status']=='unavailable'),
    'match_flags_numeric':all((r['status']=='match')==math.isclose(float(r['original_accession_ratio']),float(r['processed_source']),rel_tol=1e-6,abs_tol=1e-8) for r in comparisons if r['status']!='unavailable'),
    '19_net_margin_zero_nonzero_cases':sum(int(r['source_zero_with_nonzero_reconstruction']) for r in comparisons if r['feature']=='ratio_NetProfitMargin')==19,
    'zero_flags_mean_zero_to_nonzero':all(float(r['processed_source'])==0 and float(r['original_accession_ratio'])!=0 for r in comparisons if r['source_zero_with_nonzero_reconstruction']=='1'),
    'quarter_counts_full_release':sum(int(r['observations']) for r in quarter if r['population']=='full_release' and r['feature']=='ratio_NetProfitMargin')==269097,
    'quarter_counts_modeled_cohort':sum(int(r['observations']) for r in quarter if r['population']=='modeled_cohort' and r['feature']=='ratio_NetProfitMargin')==14657,
    'only_24_modeled_q4':next(int(r['observations']) for r in quarter if r['population']=='modeled_cohort' and r['fiscal_quarter']=='q4' and r['feature']=='ratio_NetProfitMargin')==24,
}
selector=json.loads((ROOT/'results/upstream_selector_replay.json').read_text())
checks['selector_returns_observed_prior_period']=selector['selected_date']=='20191231' and selector['selected_value']==7389407 and selector['target_period']=='20200930'
result={'checks':checks,'all_pass':all(checks.values()),'scope':'Same AI-assisted workflow, not external replication or population data-error validation'}
(ROOT/'results/measurement_verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if not result['all_pass']:raise SystemExit(1)
