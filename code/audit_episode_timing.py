"""Post hoc episode-proxy and documented-public-event audit, without fitting.

python code/audit_episode_timing.py --source-dir local_sources
First run analyze.py, which leaves generated_test_scores.csv in source-dir.
"""
from pathlib import Path
from collections import defaultdict
import argparse,csv,hashlib,json,re
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score,roc_auc_score
ROOT=Path(__file__).resolve().parents[1]
MODELS=['logit','logit_balanced','forest','prevalence']
def aaer(value):
    m=re.fullmatch(r'AAER-(\d+)',str(value).strip(),re.I)
    if not m:raise ValueError('Missing or unrecognized source AAER: '+str(value))
    return 'AAER-'+str(int(m.group(1)))
def main(src,bootstrap):
    for item in csv.DictReader((ROOT/'documentation/source_manifest.csv').open()):
        if item['file'] in ['hf_train.csv','hf_test.csv']:
            assert hashlib.sha256((src/item['file']).read_bytes()).hexdigest()==item['sha256']
    raw=pd.concat([pd.read_csv(src/n) for n in ['hf_train.csv','hf_test.csv']],ignore_index=True)
    key=['cik','year','quarter'];raw['release_sort']=pd.to_datetime(raw.aeer_date,errors='coerce')
    d=raw.sort_values(['release_sort','report_id'],na_position='last').drop_duplicates(key).copy()
    d['date']=pd.to_datetime(d.period.astype(str),format='%Y%m%d')
    fit=d[d.date.le('2017-12-31')];test=d[d.date.between('2019-01-01','2021-12-31')].sort_values('report_id').copy()
    assert len(fit)==10868 and len(test)==2695 and test.is_fraud.sum()==93
    def episode(r):return (int(r.cik),aaer(r.aaer_no))
    selected_fit_events={episode(r) for r in fit[fit.is_fraud].itertuples()}
    all_associations=defaultdict(set)
    for r in raw[raw.is_fraud].itertuples():all_associations[(int(r.cik),int(r.year),r.quarter)].add(episode(r))
    all_fit_events=set().union(*(all_associations[(int(r.cik),int(r.year),r.quarter)] for r in fit[fit.is_fraud].itertuples()))
    audit=[]
    for r in test[test.is_fraud].itertuples():
        links=all_associations[(int(r.cik),int(r.year),r.quarter)]
        audit.append({'report_id':r.report_id,'cik':r.cik,'period':r.period,'source_AAER':aaer(r.aaer_no),
            'source_release_date':r.aeer_date,'source_url':r.url,
            'representative_proxy_seen_in_refit':int(episode(r) in selected_fit_events),
            'any_proxy_seen_in_refit':int(bool(links & all_fit_events)),
            'all_original_associated_AAERs':';'.join(sorted(x[1] for x in links))})
    a=pd.DataFrame(audit);a.to_csv(ROOT/'results/evaluation_episode_overlap.csv',index=False)
    scores=pd.read_csv(src/'generated_test_scores.csv')
    assert set(scores.report_id)==set(test.report_id) and not scores.report_id.duplicated().any()
    test=test.merge(scores[['report_id']+MODELS],on='report_id',validate='one_to_one').sort_values('report_id')
    reference=pd.read_csv(ROOT/'results/metrics.csv').query("setting=='chronological'").set_index('model')
    for model in MODELS:
        assert abs(average_precision_score(test.is_fraud,test[model])-reference.loc[model,'AP'])<1e-12
        assert abs(roc_auc_score(test.is_fraud,test[model])-reference.loc[model,'ROC_AUC'])<1e-12
    def metrics(x,model):
        y=x.is_fraud.astype(int).to_numpy();p=x[model].to_numpy();k=int(np.ceil(len(x)*.05));cut=np.sort(p)[-k]
        above=p>cut;tied=p==cut;hits=float(y[above].sum()+(k-above.sum())*y[tied].mean())
        return {'records':len(x),'positives':int(y.sum()),'firms':int(x.cik.nunique()),'positive_firms':int(x.loc[x.is_fraud,'cik'].nunique()),
            'positive_fraction':float(y.mean()),'AP':float(average_precision_score(y,p)),
            'ROC_AUC':float(roc_auc_score(y,p)),'review_budget_5pct':k,'hits_5pct':hits,'precision_5pct':hits/k,'recall_5pct':hits/y.sum()}
    rows=[];intervals=[]
    for setting,col in [('exclude_representative_shared_proxy','representative_proxy_seen_in_refit'),('exclude_any_original_shared_proxy','any_proxy_seen_in_refit')]:
        excluded=set(a.loc[a[col].eq(1),'report_id']);x=test[~test.report_id.isin(excluded)].copy()
        assert len(x.loc[~x.is_fraud])==2602
        groups,ci=np.unique(x.cik.to_numpy(),return_inverse=True);rng=np.random.default_rng(20261107)
        samples={m:[] for m in MODELS};skill={m:[] for m in MODELS if m!='prevalence'};valid=0
        y=x.is_fraud.astype(int).to_numpy();pred={m:x[m].to_numpy() for m in MODELS}
        for _ in range(bootstrap):
            w=np.bincount(rng.integers(0,len(groups),len(groups)),minlength=len(groups))[ci]
            if (w*y).sum()==0 or (w*(1-y)).sum()==0:continue
            base=float(np.average(y,weights=w));valid+=1
            for m in MODELS:
                ap=float(average_precision_score(y,pred[m],sample_weight=w));samples[m].append(ap)
                if m!='prevalence':skill[m].append(ap-base)
        for m in MODELS:
            met=metrics(x,m);rows.append({'setting':setting,'model':m,'excluded_positive_rows':len(excluded),**met})
            lower,upper=np.quantile(samples[m],[.025,.975]);record={'setting':setting,'model':m,'valid_bootstrap_replicates':valid,'AP_lower':lower,'AP_upper':upper}
            if m!='prevalence':
                lower,upper=np.quantile(skill[m],[.025,.975]);record.update(AP_minus_constant=met['AP']-met['positive_fraction'],skill_lower=lower,skill_upper=upper)
            intervals.append(record)
    pd.DataFrame(rows).to_csv(ROOT/'results/episode_proxy_subset_metrics.csv',index=False)
    pd.DataFrame(intervals).to_csv(ROOT/'results/episode_proxy_subset_intervals.csv',index=False)
    stages=[]
    for name,mask,cut in [('development',d.date.le('2015-12-31'),'2016-01-01'),('validation',d.date.between('2016-01-01','2017-12-31'),'2018-01-01'),('refit',d.date.le('2017-12-31'),'2018-01-01')]:
        p=d[mask & d.is_fraud];known=int(p.release_sort.le(cut).sum())
        stages.append({'stage':name,'cutoff':cut,'positive_records':len(p),'linked_date_by_cutoff':known,'later_or_missing_linked_date':len(p)-known})
    pd.DataFrame(stages).to_csv(ROOT/'results/stage_label_availability.csv',index=False)
    filings=pd.read_csv(ROOT/'data/sec_pilot_filing_extract.csv',dtype={'cik':str,'report_id':str,'period':str})
    public=pd.read_csv(ROOT/'data/verified_public_events.csv',dtype=str);timing=[]
    for e in public.itertuples():
        group=filings[(filings.cik==e.cik)&filings.selection_group.eq('all_positive_evaluation')]
        for r in group.itertuples():
            filed=pd.to_datetime(r.filingDate,errors='coerce');event=pd.Timestamp(e.event_date)
            relation='filing_unresolved' if pd.isna(filed) else 'after_documented_event' if filed>event else 'same_day_unresolved' if filed==event else 'before_selected_event_only'
            timing.append({'event_id':e.event_id,'cik':e.cik,'event_date':e.event_date,'report_id':r.report_id,'source_period':r.period,
                'original_filing_date':r.filingDate,'relation':relation,'source_url':e.source_url,
                'boundary':'Before selected event is not certified before all public information; allegations not a finding of violation'})
    pd.DataFrame(timing).to_csv(ROOT/'results/public_event_filing_timing.csv',index=False)
    headers=pd.read_csv(ROOT/'documentation/evaluation_release_header_verification.csv',dtype=str)
    # The header correction is audited separately; no raw source or original model input changes.
    fe=raw[(raw.cik==1031296)&raw.is_fraud];mismatch=fe[fe.aaer_no.eq('AAER-4517')&fe.url.eq('https://www.sec.gov/files/litigation/admin/2024/33-11302.pdf')]
    premerger=filings[(filings.cik=='1759546')&filings.selection_group.eq('all_positive_evaluation')&filings.period.lt('20201001')]
    summary={'evaluation_positives':len(a),'representative_source_episode_proxies':len(set(zip(a.cik,a.source_AAER))),
        'representative_shared_positive_rows':int(a.representative_proxy_seen_in_refit.sum()),'any_original_shared_positive_rows':int(a.any_proxy_seen_in_refit.sum()),
        'positive_economic_keys_with_multiple_original_proxies':sum(len(v)>1 for v in all_associations.values()),
        'evaluation_linked_release_before_or_on_source_period':int((pd.to_datetime(a.source_release_date)<=pd.to_datetime(a.period.astype(str))).sum()),
        'official_headers_inspected':len(headers),'representative_header_mismatches':int(headers.header_match.eq('0').sum()),
        'FirstEnergy_mismatched_original_positive_rows':len(mismatch),
        'pre_October2020_Lordstown_CIK_positive_observations':len(premerger),
        'source_scores_reproduce_original_AP_ROC':True,'no_model_refit_or_relabeling':True,
        'scope':'Post hoc fixed-score subsets and targeted documented-event histories; no certified first-discovery dates, causal comparison, full episode identity or historical risk-set reconstruction'}
    (ROOT/'results/episode_timing_summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2));print(pd.DataFrame(rows).to_string(index=False))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source-dir',type=Path,required=True);p.add_argument('--bootstrap',type=int,default=1000);a=p.parse_args()
    if a.bootstrap<100:p.error('Use at least 100 replicates')
    main(a.source_dir,a.bootstrap)
