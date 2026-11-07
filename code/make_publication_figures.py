"""Publication figures from frozen outputs. No model fitting or new test data."""
from pathlib import Path
import argparse,csv,json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.metrics import average_precision_score,precision_recall_curve

ROOT=Path(__file__).resolve().parents[1]
NAMES={'logit':'Logistic regression','logit_balanced':'Weighted logistic regression','forest':'Class weighted random forest'}
COLORS={'logit':'#245779','logit_balanced':'#B66B29','forest':'#47745D'}
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False,'savefig.facecolor':'white'})
def save(fig,name):
    fig.tight_layout();fig.savefig(ROOT/'results'/name,dpi=220);plt.close(fig)

def main(src=None):
    skill=pd.read_csv(ROOT/'results/baseline_skill_intervals.csv')
    fig,ax=plt.subplots(figsize=(6.6,2.6))
    for i,r in skill.iterrows():
        ax.errorbar(r['estimate']*100,i,xerr=[[100*(r['estimate']-r['lo'])],[100*(r['hi']-r['estimate'])]],fmt='o',color=COLORS[r['model']],capsize=4,lw=1.7)
    ax.set_yticks(range(3),[NAMES[m] for m in skill.model]);ax.invert_yaxis();ax.axvline(0,color='#555555',ls='--',lw=1)
    ax.set_xlabel('AP minus constant-score AP (percentage points)');ax.set_xlim(-1.2,4.3);ax.grid(axis='x',alpha=.18)
    save(fig,'focused_AP_skill.png')
    metrics=pd.read_csv(ROOT/'results/metrics.csv');main=metrics[metrics.setting.eq('chronological')].set_index('model')
    search=pd.read_csv(ROOT/'results/validation_search.csv');pairs=[]
    fig,ax=plt.subplots(figsize=(6.6,3))
    for m in NAMES:
        val=float(search.loc[search.model.eq(m),'validation_AP'].max());test=float(main.loc[m,'AP'])
        pairs.append({'model':m,'selected_validation_AP':val,'evaluation_AP':test})
        ax.plot([0,1],[val,test],marker='o',lw=1.8,color=COLORS[m],label=NAMES[m])
    sample=pd.read_csv(ROOT/'results/sample_flow.csv').set_index('split')
    prevalence=[float(sample.loc['validation','positive_rate']),float(main.loc['prevalence','AP'])]
    ax.plot([0,1],prevalence,color='#555555',ls='--',label='Cohort positive fraction')
    ax.set_xticks([0,1],['Validation 2016–2017','Evaluation 2019–2021']);ax.set_ylabel('Average precision');ax.set_ylim(0,.145);ax.set_xlim(-.12,1.12)
    ax.legend(frameon=False,fontsize=8,loc='upper right');ax.grid(axis='y',alpha=.18)
    save(fig,'focused_validation_evaluation.png')
    pd.DataFrame(pairs).to_csv(ROOT/'results/validation_evaluation_display.csv',index=False)
    first=pd.read_csv(ROOT/'results/sec_pilot_summary.csv');extra=pd.read_csv(ROOT/'results/sec_extended_summary.csv')
    # The first table's field names differ; normalize explicitly.
    first=first.rename(columns={'ratio':'feature','direct_agreement':'match'})
    first=first.groupby('feature',sort=False)[['match','different','unavailable']].sum().reset_index()
    labels=['Current ratio','Working capital / assets','Liabilities / assets','Narrow cash / assets','Quarterly ROA','Quick ratio','Gross margin','Operating margin','Net margin']
    normalized=[]
    for frame in [first,extra]:
        for _,r in frame.iterrows():normalized.append({'match':int(r['match']),'different':int(r['different']),'unavailable':int(r['unavailable'])})
    assert len(normalized)==9 and all(sum(r.values())==120 for r in normalized)
    fig,ax=plt.subplots(figsize=(7,4.5));left=np.zeros(9)
    for key,color,label in [('match','#47745D','Agreement'),('different','#B66B29','Difference'),('unavailable','#CBD2D8','Unavailable')]:
        values=np.array([r[key] for r in normalized]);ax.barh(range(9),values/120*100,left=left,color=color,label=label,height=.7)
        for i,(v,l) in enumerate(zip(values,left)):
            if v>0:ax.text(l+v/120*50,i,str(v),ha='center',va='center',fontsize=8,color='white' if key!='unavailable' else '#222222')
        left+=values/120*100
    ax.set_yticks(range(9),labels);ax.invert_yaxis();ax.set_xlim(0,100);ax.set_xlabel('Percent of 120 requested comparisons per ratio');ax.legend(loc='lower left',bbox_to_anchor=(0,1.02),ncol=3,frameon=False)
    save(fig,'supplement_measurement_coverage.png')
    if src:
        train=pd.read_csv(src/'hf_train.csv');test=pd.read_csv(src/'hf_test.csv')
        x=pd.concat([train,test],ignore_index=True);x['release_sort']=pd.to_datetime(x.aeer_date,errors='coerce')
        x=x.sort_values(['release_sort','report_id'],na_position='last').drop_duplicates(['cik','year','quarter'])
        scores=pd.read_csv(src/'generated_test_scores.csv')
        x=x.merge(scores,on='report_id',validate='one_to_one');assert len(x)==2695 and x.is_fraud.sum()==93
        fig,ax=plt.subplots(figsize=(6.6,4))
        for m in NAMES:
            ap=average_precision_score(x.is_fraud,x[m]);assert abs(ap-float(main.loc[m,'AP']))<1e-12
            precision,recall,_=precision_recall_curve(x.is_fraud,x[m]);assert recall[-1]==0 and precision[-1]==1
            # precision_recall_curve returns decreasing recall; keep that order
            # for a post-step display consistent with threshold AP rectangles.
            ax.step(recall,precision,where='post',color=COLORS[m],lw=1.2,label=f'{NAMES[m]} (AP {ap:.4f})')
        ax.plot([0],[1],marker='o',color='#555555',markersize=4,clip_on=False,zorder=6)
        ax.axhline(x.is_fraud.mean(),ls='--',color='#555555',label='Cohort positive fraction')
        ax.set(xlim=(0,1),ylim=(0,1),xlabel='Recall',ylabel='Precision');ax.legend(frameon=False,fontsize=8,loc='upper right');ax.grid(alpha=.15)
        save(fig,'supplement_precision_recall_full.png')
    print('Figures generated from frozen outputs; no refit')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source-dir',type=Path);main(p.parse_args().source_dir)
