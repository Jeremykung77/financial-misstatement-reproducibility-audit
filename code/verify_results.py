"""Independent result checks including tied-rank baseline and economic key identity."""
import argparse,csv,hashlib,json
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.metrics import average_precision_score,roc_auc_score
p=argparse.ArgumentParser();p.add_argument('--source-dir',type=Path,required=True);a=p.parse_args();root=Path(__file__).resolve().parents[1];out=root/'results'
s=json.loads((out/'summary.json').read_text()); src=a.source_dir
for row in csv.DictReader((root/'documentation/source_manifest.csv').open()):
    if row['file'].endswith('.zip'): continue
    location=(root/'data'/row['file']) if (root/'data'/row['file']).exists() else (src/row['file'])
    assert hashlib.sha256(location.read_bytes()).hexdigest()==row['sha256']
x=pd.concat([pd.read_csv(src/'hf_train.csv'),pd.read_csv(src/'hf_test.csv')],ignore_index=True)
x['release_sort']=pd.to_datetime(x.aeer_date,errors='coerce')
x=x.sort_values(['release_sort','report_id'],na_position='last').drop_duplicates(['cik','year','quarter'])
m=pd.read_csv(out/'split_manifest.csv');x=x.merge(m,on='report_id',validate='one_to_one')
expected=np.where(x.period.le(20151231),'development',np.where(x.period.le(20171231),'validation',np.where(x.period.le(20181231),'gap',np.where(x.period.le(20211231),'test','unused'))))
assert np.array_equal(x.split.to_numpy(),expected), 'Date-based cohort assignment differs from manifest'
fit=x[x.split.isin(['development','validation'])];test=x[x.split.eq('test')].sort_values('report_id')
assert fit.period.max()<20180101 and test.period.min()>20181231
scores=pd.read_csv(src/'generated_test_scores.csv');t=test.merge(scores,on='report_id',validate='one_to_one')
metrics=pd.read_csv(out/'metrics.csv');main=metrics[metrics.setting.eq('chronological')].set_index('model')
for name in ['logit','logit_balanced','forest','prevalence']:
    assert abs(average_precision_score(t.is_fraud,t[name])-main.loc[name,'AP'])<1e-10
    assert abs(roc_auc_score(t.is_fraud,t[name])-main.loc[name,'ROC_AUC'])<1e-10
# A constant prediction must not obtain top-k skill from target-correlated IDs.
assert abs(main.loc['prevalence','P1']-t.is_fraud.mean())<1e-12
assert abs(main.loc['prevalence','P5']-t.is_fraud.mean())<1e-12
# Independent AP implementation, grouped ties, for main logistic model.
z=t.sort_values('logit',ascending=False); y=z.is_fraud.to_numpy(dtype=int);p=z.logit.to_numpy();tp=np.cumsum(y);ends=np.r_[np.flatnonzero(p[:-1]!=p[1:]),len(p)-1]
recall=tp[ends]/y.sum();precision=tp[ends]/(ends+1);ap=np.sum(np.diff(np.r_[0,recall])*precision)
assert abs(ap-main.loc['logit','AP'])<1e-10
# The audit score identity is a diagnostic, not a held-out fraud detection result.
u=pd.read_csv(root/'data/audit_risk.csv');assert np.array_equal(u.Risk,(u.Audit_Risk>1).astype(int))
assert len(test)==2695 and test.is_fraud.sum()==93 and test.loc[test.is_fraud,'cik'].nunique()==26
# Feature join independently uses economic identity and exact period.
f=pd.read_csv(src/'hf_financials.csv');key=['cik','year','quarter'];assert not f.duplicated(key).any()
j=x.merge(f[key+['period']],on=key,how='left',validate='one_to_one',suffixes=('','_source'),indicator=True)
assert j._merge.eq('both').all() and j.period.eq(j.period_source).all()
# No unvalidated thresholds are carried into the changed availability fitting cohort.
av=pd.read_csv(out/'metrics.csv').query("setting == 'partial_label_availability'")
assert av[['F1','precision_threshold','recall_threshold','threshold']].isna().all().all()
# Skill point estimates must subtract the paired evaluation fraction, not the refit fraction.
for _,row in pd.read_csv(out/'baseline_skill_intervals.csv').iterrows():
    assert abs(row.estimate-(main.loc[row.model,'AP']-test.is_fraud.mean()))<1e-12
    assert row.lo<=row.hi and row.replicates==s['bootstrap_replicates']
# Unknown AAER categories remain missing rather than being turned into confirmed negatives.
aa=pd.read_csv(root/'data/aaer_mark5.csv',sep=';')
assert int(aa.fsf.isna().sum())==74
strata=pd.read_csv(out/'aaer_timing_strata.csv').set_index('stratum')
assert strata.loc['FSF_flag_1','n']==478 and strata.loc['FSF_flag_missing','n']==74
assert strata.loc['FSF_flag_1_both_dates_certain','n']==319
rob=pd.read_csv(out/'posthoc_robustness.csv')
assert set(rob.condition)=={'narrow_category','nonfinancial_SIC_exclusion','zero_pattern_only'}
assert rob.loc[rob.condition.eq('narrow_category'),'positives'].eq(92).all()
report={'status':'PASS','checks':['All original benchmark input CSVs and all three financial sources match SHA256','Economic-key feature join and exact period agreement','Calendar cohort assignment independently reconstructed without trusting split manifest','Main AP and ROC metrics separately recomputed','AP independently integrated over score tie groups','Constant-score review budget uses random tie expectation','UCI target score identity','Holdout positive firm and record counts','Availability stress test has no inherited classification thresholds','Baseline-skill contrasts use paired evaluation fraction','Missing category flags and timing strata preserved','Post hoc narrow-category denominator verified'],'main_test_records':len(test),'main_test_positives':int(test.is_fraud.sum()),'independence_scope':'Separate implementation checks within one research workflow; no external research team replication'}
(out/'verification_report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
