"""Offline numerical checks; score recomputation still needs pinned source files."""
from pathlib import Path
from fractions import Fraction
import csv, json, math

ROOT=Path(__file__).resolve().parents[1]
def read(name):
    with (ROOT/'results'/name).open() as f:
        return list(csv.DictReader(f))
def close(a,b):
    return math.isclose(float(a),float(b),abs_tol=1e-12)
reference=read('random_AP_reference.csv')
exhaustive=read('random_AP_exhaustive_check.csv')
detail=read('period_batch_detail.csv')
aggregate=read('period_batch_retrieval.csv')
original={r['model']:r for r in read('metrics.csv') if r['setting']=='chronological'}
summary=json.loads((ROOT/'results/evaluation_reference_summary.json').read_text())
# Independent rank-by-rank conditional-expectation expression using rational arithmetic.
n,p=2695,93
exact=sum((Fraction(1,k)*(1+Fraction((k-1)*(p-1),n-1)) for k in range(1,n+1)),Fraction())/n
checks={
 'unchanged_cohort_and_four_models':len(reference)==4 and all(r['records']=='2695' and r['positives']=='93' for r in reference),
 'analytic_reference_independent_rational_expression':all(close(r['expected_random_tie_free_AP'],exact) for r in reference),
 'constant_AP_distinguished_from_random_reference':all(close(r['constant_AP'],Fraction(93,2695)) and float(r['expected_random_tie_free_AP'])>float(r['constant_AP']) for r in reference),
 'all_original_AP_reproduced':all(close(r['AP'],original[r['model']]['AP']) for r in reference),
 'contrast_arithmetic':all(close(float(r['AP'])-float(r['expected_random_tie_free_AP']),r['AP_minus_random_expectation']) for r in reference),
 'three_model_contrast_intervals_include_zero':all(float(r['contrast_lower'])<=0<=float(r['contrast_upper']) for r in reference if r['model']!='prevalence'),
 '1000_valid_CIK_cluster_replicates':all(r['valid_cluster_replicates']=='1000' for r in reference),
 'exhaustive_all_45_N_P_pairs':len(exhaustive)==45 and {(int(r['records']),int(r['positives'])) for r in exhaustive}=={(n,p) for n in range(1,10) for p in range(1,n+1)},
 'exhaustive_1013_label_orderings_and_small_errors':sum(int(r['distinct_label_orderings']) for r in exhaustive)==1013 and all(float(r['absolute_error'])<1e-12 for r in exhaustive),
 'all_12_batches_both_rates_all_models':len(detail)==96 and len({(r['batch'],r['rate'],r['model']) for r in detail})==96,
 'aggregate_three_rules_both_rates_all_models':len(aggregate)==24 and len({(r['setting'],r['rate'],r['model']) for r in aggregate})==24,
 'ceiling_capacity_in_each_batch':all(int(r['capacity'])==math.ceil(float(r['rate'])*int(r['records'])) for r in detail),
 'same_2695_records_and_93_positives_per_rule':all(r['records']=='2695' and r['positives']=='93' for r in aggregate),
 'precision_recall_denominators':all(close(r['precision'],float(r['expected_hits'])/int(r['capacity'])) and close(r['recall'],float(r['expected_hits'])/93) for r in aggregate),
 'summary_reports_score_reproduction_and_no_refit':summary['all_primary_AP_ROC_and_pooled_retrieval_reproduced'] and summary['no_refit_or_relabeling'],
}
for row in aggregate:
    m,rate=row['model'],row['rate']
    if row['setting']=='quarter_batches':
        group=[r for r in detail if r['model']==m and r['rate']==rate]
        assert sum(int(r['records']) for r in group)==2695
        assert sum(int(r['positives']) for r in group)==93
        assert int(row['capacity'])==sum(int(r['capacity']) for r in group)
        assert close(row['expected_hits'],sum(float(r['expected_hits']) for r in group))
        assert close(row['random_expected_hits'],sum(float(r['random_expected_hits']) for r in group))
    if row['setting']=='pooled_original':
        column='hits1' if rate=='0.01' else 'hits5'
        assert close(row['expected_hits'],original[m][column])
    if m=='prevalence':
        assert close(row['expected_hits'],row['random_expected_hits'])
    if row['setting']=='pooled_matched_quarter_capacity':
        match=next(r for r in aggregate if r['model']==m and r['rate']==rate and r['setting']=='quarter_batches')
        assert row['capacity']==match['capacity']
checks['batch_aggregation_original_retrieval_and_matched_capacity']=True
result=dict(checks=checks,all_pass=all(checks.values()),scope='Offline aggregate arithmetic and independent formula check; not independent score/case review or deployment validation')
(ROOT/'results/evaluation_reference_verification.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
if not result['all_pass']:
    raise SystemExit(1)
