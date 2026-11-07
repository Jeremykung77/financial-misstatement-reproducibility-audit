"""Executed exploratory analysis. Run from anywhere; see README for public downloads.
No generative AI is used as a predictive model in this experiment.
"""
from pathlib import Path
import argparse, json, hashlib, platform, csv, importlib.metadata
import numpy as np
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (average_precision_score, roc_auc_score, precision_recall_curve,
                             f1_score, precision_score, recall_score, brier_score_loss)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
SEED=20261106
FEATURES=['ratio_GrossProfitMargin','ratio_OperatingMargin','ratio_NetProfitMargin',
'ratio_ReturnOnAssets','ratio_CurrentRatio','ratio_QuickRatio','ratio_CashRatio',
'ratio_WorkingCapitalToTotalAssets','ratio_DebtToAssetsRatio',
'ratio_TotalLiabilitiesToAssets','ratio_AssetTurnover','ratio_CashToTotalAsset']
def signlog(x): return np.sign(x)*np.log1p(np.abs(x))
def metrics(y,p,ids,threshold=.5):
    y=np.asarray(y,dtype=int);p=np.asarray(p)
    if len(y)==0 or len(y)!=len(p) or not np.isfinite(p).all():
        raise ValueError('Metrics require nonempty aligned finite scores')
    r={'n':len(y),'positives':int(y.sum()),'prevalence':float(y.mean()),
       'AP':float(average_precision_score(y,p)) if y.sum() else None,
       'ROC_AUC':float(roc_auc_score(y,p)) if len(np.unique(y))==2 else None,
       'Brier':float(brier_score_loss(y,p)),
       'F1':float(f1_score(y,p>=threshold,zero_division=0)) if threshold is not None else None,
       'precision_threshold':float(precision_score(y,p>=threshold,zero_division=0)) if threshold is not None else None,
       'recall_threshold':float(recall_score(y,p>=threshold,zero_division=0)) if threshold is not None else None,
       'threshold':float(threshold) if threshold is not None else None}
    for pct in [1,5]:
        k=int(np.ceil(len(y)*pct/100));cut=np.sort(p)[-k]
        above=p>cut; tied=p==cut
        hits=float(y[above].sum()+(k-above.sum())*y[tied].mean())
        r.update({f'k{pct}':k,f'hits{pct}':hits,f'P{pct}':hits/k,f'R{pct}':hits/y.sum() if y.sum() else None})
    return r

def build(kind,param):
    est=RandomForestClassifier(n_estimators=300,max_depth=param,min_samples_leaf=10,
            class_weight='balanced_subsample',bootstrap=True,max_features='sqrt',criterion='gini',random_state=SEED,n_jobs=1) if kind=='forest' else LogisticRegression(
            C=param,class_weight='balanced' if kind=='logit_balanced' else None,
            max_iter=3000,random_state=SEED)
    return make_pipeline(FunctionTransformer(signlog),SimpleImputer(strategy='median',add_indicator=True),StandardScaler(),est)

def clean_aaer(path,out):
    x=pd.read_csv(path,sep=';'); e=x.copy()
    e['release_date']=pd.to_datetime(e.dateTime.astype(str).str.replace(r'[\u200b\ufeff]','',regex=True).str[:10],errors='coerce')
    e['start_date']=pd.to_datetime(e.fraud_start,format='%m-%Y',errors='coerce')
    e['end_date']=pd.to_datetime(e.fraud_end,format='%m-%Y',errors='coerce')+pd.offsets.MonthEnd(0)
    e['lag_years']=(e.release_date-e.end_date).dt.days/365.25
    z=e.lag_years.dropna(); both=(e.certainty_start.eq(1)&e.certainty_end.eq(1))
    summary={'rows':len(e),'unique_CIK':e.cik.nunique(),'unique_AAER':e.aaerNo.nunique(),
    'missing_id':int(e.id.isna().sum()),'fsf_flag_1':int(e.fsf.eq(1).sum()),
    'corruption_flag_1':int(e.corruption.eq(1).sum()),'asset_misappropriation_flag_1':int(e.amis.eq(1).sum()),
    'both_timing_certain':int(both.sum()),'missing_release':int(e.release_date.isna().sum()),
    'missing_start':int(e.start_date.isna().sum()),'missing_end':int(e.end_date.isna().sum()),
    'start_after_end':int((e.start_date>e.end_date).sum()),'release_before_end':int(z.lt(0).sum()),
    'lag_n':len(z),'lag_median_years':float(z.median()),'lag_q25':float(z.quantile(.25)),
    'lag_q75':float(z.quantile(.75)),'lag_gt1':int(z.gt(1).sum()),'lag_gt2':int(z.gt(2).sum()),'lag_gt3':int(z.gt(3).sum()),
    'release_min':str(e.release_date.min().date()),'release_max':str(e.release_date.max().date())}
    summary['missing_category_flags']={k:int(e[k].isna().sum()) for k in ['fsf','amis','corruption']}
    strata=[]
    for label,mask in [('all',pd.Series(True,index=e.index)),('FSF_flag_1',e.fsf.eq(1)),('FSF_flag_0',e.fsf.eq(0)),('FSF_flag_missing',e.fsf.isna()),('FSF_flag_1_both_dates_certain',e.fsf.eq(1)&both)]:
        v=e.loc[mask,'lag_years'].dropna();strata.append({'stratum':label,'n':len(v),'median_years':float(v.median()),'q25':float(v.quantile(.25)),'q75':float(v.quantile(.75))})
    pd.DataFrame(strata).to_csv(out/'aaer_timing_strata.csv',index=False)
    e[['aaerNo','cik','release_date','start_date','end_date','certainty_start','certainty_end','fsf','lag_years']].to_csv(out/'aaer_timing_audit.csv',index=False)
    return summary,e

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source-dir',type=Path,required=True);ap.add_argument('--package-dir',type=Path,default=Path(__file__).resolve().parents[1]);ap.add_argument('--bootstrap',type=int,default=1000);a=ap.parse_args()
    root=a.package_dir;out=root/'results';out.mkdir(exist_ok=True); src=a.source_dir
    if a.bootstrap<100: raise ValueError('Use at least 100 bootstrap replicates')
    checked=[]
    for item in csv.DictReader((root/'documentation/source_manifest.csv').open()):
        name=item['file']
        if name.endswith('.zip'): continue  # supplied extracted data have their own fingerprints
        location=(root/'data'/name) if (root/'data'/name).exists() else (src/name)
        if hashlib.sha256(location.read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError(f'Changed source file: {name}')
        checked.append(name)
    hfa=pd.read_csv(src/'hf_train.csv');hfb=pd.read_csv(src/'hf_test.csv')
    for frame in [hfa,hfb]:
        if frame[['cik','year','quarter','period','report_id','is_fraud']].isna().any().any():
            raise ValueError('Missing economic identity or outcome')
        if not frame.is_fraud.isin([True,False]).all(): raise ValueError('Nonbinary target')
    audit={'provided_train_n':len(hfa),'provided_test_n':len(hfb),
           'provided_train_positives':int(hfa.is_fraud.sum()),'provided_test_positives':int(hfb.is_fraud.sum()),
           'provided_train_max_period':int(hfa.period.max()),'provided_test_min_period':int(hfb.period.min()),
           'provided_shared_periods':len(set(hfa.period)&set(hfb.period)),
           'provided_shared_firms':len(set(hfa.cik)&set(hfb.cik)),
           'provided_shared_reports':len(set(hfa.report_id)&set(hfb.report_id))}
    d=pd.concat([hfa,hfb],ignore_index=True)
    assert not d.report_id.duplicated().any(), 'Duplicate report IDs require adjudication'
    # report_id belongs to the prepared split, not to the full financial table.
    # Use the unique economic observation key and require exact period agreement.
    key=['cik','year','quarter']
    audit['source_unique_economic_keys']=d.groupby(key).ngroups
    audit['source_duplicate_economic_rows']=int(d.duplicated(key).sum())
    audit['source_conflicting_labels']=int(d.groupby(key).is_fraud.nunique().gt(1).sum())
    audit['provided_shared_economic_keys']=len(set(map(tuple,hfa[key].to_numpy()))&set(map(tuple,hfb[key].to_numpy())))
    assert audit['source_conflicting_labels']==0
    assert d.groupby(key).period.nunique().le(1).all(), 'Conflicting period within economic key'
    d['release_sort']=pd.to_datetime(d.aeer_date,errors='coerce')
    d=d.sort_values(['release_sort','report_id'],na_position='last').drop_duplicates(key).reset_index(drop=True)
    f=pd.read_csv(src/'hf_financials.csv')
    assert not f.duplicated(key).any()
    q=d.merge(f[key+['period']+FEATURES],on=key,how='left',validate='one_to_one',suffixes=('','_fin'),indicator=True)
    assert q['_merge'].eq('both').all()
    assert q.period.eq(q.period_fin).all(), 'Mismatched economic reporting period'
    d=q.drop(columns=['_merge']); d['y']=d.is_fraud.astype(int);d['date']=pd.to_datetime(d.period.astype(str),format='%Y%m%d')
    X=d[FEATURES].apply(pd.to_numeric,errors='coerce').replace([np.inf,-np.inf],np.nan)
    d[FEATURES]=X
    masks={'development':d.date.le('2015-12-31'),'validation':d.date.between('2016-01-01','2017-12-31'),
           'gap':d.date.between('2018-01-01','2018-12-31'),'test':d.date.between('2019-01-01','2021-12-31')}
    train=d[masks['development']];val=d[masks['validation']];test=d[masks['test']].sort_values('report_id').reset_index(drop=True)
    fit=d[masks['development']|masks['validation']]
    assert train.date.max()<val.date.min() and fit.date.max()<test.date.min()
    assert not set(fit.report_id)&set(test.report_id)
    counts=[]
    for k,m in masks.items():
        sub=d[m];counts.append({'split':k,'n':len(sub),'positive':int(sub.y.sum()),'firms':sub.cik.nunique(),'positive_firms':sub.loc[sub.y.eq(1),'cik'].nunique(),'min_date':str(sub.date.min().date()),'max_date':str(sub.date.max().date()),'positive_rate':sub.y.mean()})
    pd.DataFrame(counts).to_csv(out/'sample_flow.csv',index=False)
    pd.DataFrame({'feature':FEATURES,'missing_fraction':X.isna().mean().values,'zero_fraction':X.eq(0).mean().values}).to_csv(out/'feature_audit.csv',index=False)
    pd.DataFrame({'report_id':d.report_id,'split':np.select(list(masks.values()),list(masks.keys()),default='unused')}).to_csv(out/'split_manifest.csv',index=False)
    tune=[]; chosen={};preds={};thresholds={};rows=[]
    for kind,params in [('logit',[.1,1.,10.]),('logit_balanced',[.1,1.,10.]),('forest',[4,8])]:
        best=None
        for param in params:
            model=build(kind,param);model.fit(train[FEATURES],train.y);vp=model.predict_proba(val[FEATURES])[:,1]
            score=average_precision_score(val.y,vp);tune.append({'model':kind,'parameter':param,'validation_AP':score})
            if best is None or score>best[0]: best=(score,param,vp)
        chosen[kind]={'parameter':best[1],'validation_AP':best[0]}
        pr,re,ts=precision_recall_curve(val.y,best[2]);f1=2*pr[:-1]*re[:-1]/np.maximum(pr[:-1]+re[:-1],1e-15);th=float(ts[np.argmax(f1)])
        model=build(kind,best[1]);model.fit(fit[FEATURES],fit.y);p=model.predict_proba(test[FEATURES])[:,1]
        preds[kind]=p;thresholds[kind]=th;rows.append({'model':kind,'setting':'chronological',**metrics(test.y,p,test.report_id,th)})
    p=np.full(len(test),fit.y.mean());preds['prevalence']=p;thresholds['prevalence']=.5
    rows.append({'model':'prevalence','setting':'chronological',**metrics(test.y,p,test.report_id)})
    # Post-outcome metadata positive control; explicitly invalid as a forecasting feature.
    p=test.aaer_no.notna().astype(float).to_numpy()
    rows.append({'model':'AAER_presence_INVALID','setting':'leakage_positive_control',**metrics(test.y,p,test.report_id)})
    # Cold-company test of same fixed fitted models, without tuning on subset.
    cold=~test.cik.isin(fit.cik);audit['test_unseen_firm_n']=int(cold.sum());audit['test_unseen_firm_positives']=int(test.loc[cold,'y'].sum());audit['test_seen_firm_n']=int((~cold).sum())
    for k,p in preds.items():
        if cold.any(): rows.append({'model':k,'setting':'unseen_company_subset',**metrics(test.loc[cold,'y'],p[cold],test.loc[cold,'report_id'],thresholds[k])})
    # A partial label-availability stress test, not a fully historical simulation.
    releases=pd.to_datetime(fit.aeer_date,errors='coerce');unknown=fit.y.eq(1)&(releases.isna()|releases.gt('2018-01-01'))
    audit['refit_positive_labels_unavailable_at_2018_01_01']=int(unknown.sum());audit['refit_positives']=int(fit.y.sum())
    avail=fit[~unknown];audit['availability_train_n']=len(avail);audit['availability_train_positives']=int(avail.y.sum())
    for k,v in chosen.items():
        model=build(k,v['parameter']);model.fit(avail[FEATURES],avail.y);p=model.predict_proba(test[FEATURES])[:,1]
        preds[k+'_availability']=p
        rows.append({'model':k,'setting':'partial_label_availability',**metrics(test.y,p,test.report_id,None)})
    # Post hoc revision diagnostics: hold the selected main settings fixed.
    # No new untouched holdout is claimed and these are not a model-selection search.
    supplementary=[]
    for condition in ['narrow_category','nonfinancial_SIC_exclusion','zero_pattern_only']:
        keep_fit=pd.Series(True,index=fit.index);keep_test=pd.Series(True,index=test.index)
        if condition=='narrow_category':
            keep_fit=~(fit.y.eq(1)&~fit.glabels.fillna('').str.contains('FinancialMistatement',regex=False))
            keep_test=~(test.y.eq(1)&~test.glabels.fillna('').str.contains('FinancialMistatement',regex=False))
        if condition=='nonfinancial_SIC_exclusion':
            keep_fit=~fit.sic.between(6000,6999);keep_test=~test.sic.between(6000,6999)
        fa=fit.loc[keep_fit];te=test.loc[keep_test]
        for kind,v in chosen.items():
            xt=fa[FEATURES];xe=te[FEATURES]
            if condition=='zero_pattern_only': xt=xt.eq(0).astype(float);xe=xe.eq(0).astype(float)
            model=build(kind,v['parameter']);model.fit(xt,fa.y);sp=model.predict_proba(xe)[:,1]
            supplementary.append({'condition':condition,'model':kind,'fit_n':len(fa),'fit_positive':int(fa.y.sum()),**metrics(te.y,sp,te.report_id,None)})
    pd.DataFrame(supplementary).to_csv(out/'posthoc_robustness.csv',index=False)
    sector=[]
    for label,mask in [('SIC_6000_to_6999',d.sic.between(6000,6999)),('other_SIC',~d.sic.between(6000,6999))]:
        part=d[mask]
        sector.append({'sector':label,'n':len(part),'positive':int(part.y.sum()),'net_margin_zero_fraction':float(part.ratio_NetProfitMargin.eq(0).mean()),'debt_assets_zero_fraction':float(part.ratio_DebtToAssetsRatio.eq(0).mean())})
    pd.DataFrame(sector).to_csv(out/'sector_feature_audit.csv',index=False)
    influence=[]
    for firm in sorted(test.loc[test.y.eq(1),'cik'].unique()):
        retain=test.cik.ne(firm)
        for kind in ['logit','logit_balanced','forest']:
            met=metrics(test.loc[retain,'y'],preds[kind][retain],test.loc[retain,'report_id'],None)
            influence.append({'removed_positive_firm':int(firm),'model':kind,'removed_records':int((~retain).sum()),'removed_positives':int(test.loc[~retain,'y'].sum()),**met})
    pd.DataFrame(influence).to_csv(out/'positive_firm_influence.csv',index=False)
    pd.DataFrame(rows).to_csv(out/'metrics.csv',index=False)
    pd.DataFrame(tune).to_csv(out/'validation_search.csv',index=False)
    # Scores retained for exact local rechecking; no third-party row data redistributed.
    pd.DataFrame({'report_id':test.report_id,**preds}).to_csv(src/'generated_test_scores.csv',index=False)
    annual=[]
    for yr,g in test.groupby(test.date.dt.year):
        for k,p in preds.items():
            if 'availability' not in k: annual.append({'year':yr,'model':k,**metrics(g.y,p[g.index],g.report_id,thresholds[k])})
    pd.DataFrame(annual).to_csv(out/'annual_metrics.csv',index=False)
    # Paired firm-cluster percentile intervals conditional on fixed fitted models.
    rng=np.random.default_rng(SEED); firms,group=np.unique(test.cik,return_inverse=True);B=a.bootstrap
    vals={k:[] for k in preds if 'availability' not in k};diffs=[];skill={k:[] for k in ['logit','logit_balanced','forest']}
    for b in range(B):
        cluster_counts=np.bincount(rng.integers(0,len(firms),len(firms)),minlength=len(firms));w=cluster_counts[group]
        if (w*test.y.to_numpy()).sum()==0 or (w*(1-test.y.to_numpy())).sum()==0: continue
        aps={}
        for k in vals:
            aps[k]=average_precision_score(test.y,preds[k],sample_weight=w)
            vals[k].append([aps[k],roc_auc_score(test.y,preds[k],sample_weight=w)])
        diffs.append([aps['forest']-aps['logit'],aps['forest']-aps['logit_balanced']])
        for kind in skill: skill[kind].append(aps[kind]-aps['prevalence'])
    ci=[]
    for k,v in vals.items():
        arr=np.asarray(v)
        for j,name in enumerate(['AP','ROC_AUC']):
            lo,hi=np.quantile(arr[:,j],[.025,.975]);ci.append({'model':k,'metric':name,'lo':lo,'hi':hi,'replicates':len(arr)})
    for j,k in enumerate(['forest_minus_logit','forest_minus_logit_balanced']):
        lo,hi=np.quantile(np.asarray(diffs)[:,j],[.025,.975]);ci.append({'model':k,'metric':'AP_difference','lo':lo,'hi':hi,'replicates':len(diffs)})
    pd.DataFrame(ci).to_csv(out/'cluster_bootstrap.csv',index=False)
    contrast=[]
    for kind,v in skill.items():
        lo,hi=np.quantile(v,[.025,.975]);point=average_precision_score(test.y,preds[kind])-test.y.mean()
        contrast.append({'model':kind,'contrast':'AP_minus_constant_AP','estimate':float(point),'lo':float(lo),'hi':float(hi),'replicates':len(v)})
    pd.DataFrame(contrast).to_csv(out/'baseline_skill_intervals.csv',index=False)
    aaer,e=clean_aaer(root/'data/aaer_mark5.csv',out)
    u=pd.read_csv(root/'data/audit_risk.csv')
    uc={'rows':len(u),'positive':int(u.Risk.sum()),'exact_duplicate_rows':int(u.duplicated().sum()),'threshold_mismatch':int(((u.Audit_Risk>1).astype(int)!=u.Risk).sum()),
        'audit_formula_max_error':float((u.Audit_Risk-u.Inherent_Risk*u.CONTROL_RISK*u.Detection_Risk).abs().max()),'missing_Money_Value':int(u.Money_Value.isna().sum())}
    summary={'seed':SEED,'source_split_audit':audit,'sample_flow':counts,'selected':chosen,'AAER':aaer,'UCI':uc,
      'source_files_verified':checked,'review_revision':'v2 post hoc audit',
      'positive_firm_concentration':{'firms':int(test.loc[test.y.eq(1),'cik'].nunique()),'largest_firm_positives':int(test.loc[test.y.eq(1),'cik'].value_counts().max()),'top3_firm_positives':int(test.loc[test.y.eq(1),'cik'].value_counts().head(3).sum())},
      'features':FEATURES,'bootstrap_replicates':B,'python':platform.python_version(),
      'packages':{k:importlib.metadata.version(k) for k in ['numpy','pandas','scipy','scikit-learn','matplotlib']}}
    (out/'summary.json').write_text(json.dumps(summary,indent=2))
    # Compact publication figures.
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':13,'axes.spines.top':False,'axes.spines.right':False})
    fig,axs=plt.subplots(1,2,figsize=(10.4,4.0))
    for k in ['logit','logit_balanced','forest']:
        p,r,_=precision_recall_curve(test.y,preds[k]);keep=r>0;axs[0].step(r[keep],p[keep],where='post',label={'logit':'Logit','logit_balanced':'Weighted logit','forest':'Forest'}[k])
    axs[0].axhline(test.y.mean(),color='grey',ls='--',label='Positive fraction');axs[0].set(xlabel='Recall',ylabel='Precision',title='A   Chronological holdout');axs[0].set_ylim(0,.2);axs[0].legend(fontsize=11)
    axs[1].hist(e.lag_years.dropna(),bins=np.arange(np.floor(e.lag_years.min())-1,np.ceil(e.lag_years.max())+2,1),color='#355c7d',edgecolor='white');axs[1].axvline(aaer['lag_median_years'],color='#b04a36',ls='--');axs[1].set(xlabel='Years from coded end\nto associated release',ylabel='Label records',title='B   AAER linked release lag')
    fig.tight_layout();fig.savefig(out/'figure_1.png',dpi=220);fig.savefig(out/'figure_1.pdf');plt.close(fig)
    print(json.dumps(summary,indent=2))
if __name__=='__main__': main()
