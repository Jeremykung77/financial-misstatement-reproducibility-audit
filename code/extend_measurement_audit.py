"""Post hoc measurement audit. No model fit. See REVISION_V4_PLAN.md.

Offline: python code/extend_measurement_audit.py analyze
Re-extract: python code/extend_measurement_audit.py extract --cache local_sec --source-dir local_sources
The separate upstream replay requires pandas and the exact original file, not redistributed.
"""
from pathlib import Path
from collections import Counter,defaultdict
from datetime import date
import argparse,csv,hashlib,json,math
ROOT=Path(__file__).resolve().parents[1]
FEATURES=['ratio_GrossProfitMargin','ratio_OperatingMargin','ratio_NetProfitMargin','ratio_ReturnOnAssets',
    'ratio_CurrentRatio','ratio_QuickRatio','ratio_CashRatio','ratio_WorkingCapitalToTotalAssets',
    'ratio_DebtToAssetsRatio','ratio_TotalLiabilitiesToAssets','ratio_AssetTurnover','ratio_CashToTotalAsset']
NEW=['ratio_ReturnOnAssets','ratio_QuickRatio','ratio_GrossProfitMargin','ratio_OperatingMargin','ratio_NetProfitMargin']
REVENUE=['Revenues','SalesRevenueNet','RevenueFromContractWithCustomerExcludingAssessedTax','RevenueFromContractWithCustomerIncludingAssessedTax']
INSTANT=['Assets','AssetsCurrent','LiabilitiesCurrent','InventoryNet']
FLOW=['NetIncomeLoss','GrossProfit','OperatingIncomeLoss']+REVENUE
def read(p):
    with Path(p).open(newline='') as f:return list(csv.DictReader(f))
def write(p,rs):
    fields=list(dict.fromkeys(k for r in rs for k in r))
    with p.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rs)
def extract(cache,src):
    filings=read(ROOT/'data/sec_pilot_filing_extract.csv');selected={r['report_id']:r for r in filings}
    wanted={(r['cik'],r['period']):r['report_id'] for r in filings}
    manifest={r['file']:r for r in read(ROOT/'documentation/sec_source_manifest.csv')}
    facts=[];sensus=[]
    for cik in sorted({r['cik'] for r in filings}):
        file=cache/f'companyfacts_{cik}.json';raw=file.read_bytes()
        assert hashlib.sha256(raw).hexdigest()==manifest[file.name]['sha256'],'Changed API snapshot'
        data=json.loads(raw)['facts']['us-gaap']
        for row in [r for r in filings if r['cik']==cik and r['matched']=='1']:
            end=row['reportDate'];a=row['accessionNumber']
            for tag in INSTANT+FLOW:
                for f in data.get(tag,{}).get('units',{}).get('USD',[]):
                    if f['accn']!=a or f['end']!=end:continue
                    start=f.get('start','')
                    if tag in INSTANT and start:continue
                    if tag in FLOW and (not start or not 60<=(date.fromisoformat(end)-date.fromisoformat(start)).days+1<=120):continue
                    facts.append({'report_id':row['report_id'],'cik':cik,'period':row['period'],'accession':a,
                        'tag':tag,'start':start,'end':end,'unit':'USD','value':f['val'],'filed':f['filed']})
        if cik=='1494891':
            for tag,item in data.items():
                for f in item.get('units',{}).get('USD',[]):
                    if f['accn']=='0001213900-20-036128' and not f.get('start'):
                        sensus.append({'adsh':f['accn'],'tag':tag,'ddate':f['end'].replace('-',''),
                            'value':f['val'],'uom':'USD','qtrs':0,'segments':'',
                            'input_source':'Observed SEC companyfacts USD instant fact; not original NUM table'})
    write(ROOT/'data/sec_extended_fact_extract.csv',facts)
    write(ROOT/'data/sensus_accession_instant_facts.csv',sensus)
    splits=read(src/'hf_train.csv')+read(src/'hf_test.csv');keys={(r['cik'],r['year'],r['quarter']) for r in splits}
    n=Counter();zero=Counter();missing=Counter();inputs=[]
    # Validate the pinned financial input before producing new counts.
    source_manifest=read(ROOT/'documentation/source_manifest.csv')
    for filename in ['hf_train.csv','hf_test.csv','hf_financials.csv']:
        expected=next(r['sha256'] for r in source_manifest if r['file']==filename)
        assert hashlib.sha256((src/filename).read_bytes()).hexdigest()==expected
    with (src/'hf_financials.csv').open(newline='') as f:
        for r in csv.DictReader(f):
            for population in ['full_release']+(['modeled_cohort'] if (r['cik'],r['year'],r['quarter']) in keys else []):
                group=(population,r['quarter']);n[group]+=1
                for feature in FEATURES:
                    v=float(r[feature]) if r[feature] else float('nan')
                    if not math.isfinite(v):missing[group,feature]+=1
                    elif v==0:zero[group,feature]+=1
            key=(r['cik'],r['period'])
            if key in wanted:
                rid=wanted[key];inputs.append({'report_id':rid,'cik':r['cik'],'period':r['period'],
                    'selection_group':selected[rid]['selection_group'],**{k:r[k] for k in NEW}})
    assert len(inputs)==120
    write(ROOT/'data/sec_extended_comparison_inputs.csv',inputs)
    table=[]
    for group,count in sorted(n.items()):
        for feature in FEATURES:table.append({'population':group[0],'fiscal_quarter':group[1],'feature':feature,
            'observations':count,'zeros':zero[group,feature],'missing':missing[group,feature],
            'zero_fraction':zero[group,feature]/count})
    write(ROOT/'results/quarter_zero_patterns.csv',table)
    analyze()
def analyze():
    facts=read(ROOT/'data/sec_extended_fact_extract.csv');inputs=read(ROOT/'data/sec_extended_comparison_inputs.csv')
    result=[]
    for r in inputs:
        mine=[f for f in facts if f['report_id']==r['report_id']]
        def instant(tag):
            v={float(f['value']) for f in mine if f['tag']==tag and not f['start']}
            return next(iter(v)) if len(v)==1 else None
        def flow(tags):
            v={(f['start'],float(f['value'])) for f in mine if f['tag'] in tags}
            return next(iter(v)) if len(v)==1 else None
        ni=flow(['NetIncomeLoss']);revenue=flow(REVENUE);assets=instant('Assets');ca=instant('AssetsCurrent');cl=instant('LiabilitiesCurrent');inventory=instant('InventoryNet')
        values={'ratio_ReturnOnAssets':ni[1]/assets if ni and assets not in [None,0] else None,
            'ratio_QuickRatio':(ca-inventory)/cl if ca is not None and inventory is not None and cl not in [None,0] else None}
        for feature,tag in [('ratio_GrossProfitMargin','GrossProfit'),('ratio_OperatingMargin','OperatingIncomeLoss'),('ratio_NetProfitMargin','NetIncomeLoss')]:
            numerator=flow([tag]);values[feature]=numerator[1]/revenue[1] if numerator and revenue and numerator[0]==revenue[0] and revenue[1]!=0 else None
        for feature,value in values.items():
            source=float(r[feature]);status='unavailable' if value is None else 'match' if math.isclose(value,source,rel_tol=1e-6,abs_tol=1e-8) else 'different'
            result.append({k:r[k] for k in ['report_id','cik','period','selection_group']}|{'feature':feature,
                'original_accession_ratio':value,'processed_source':source,'status':status,
                'source_zero_with_nonzero_reconstruction':int(source==0 and value is not None and value!=0),
                'unavailable_reason':'Missing, ambiguous, unmatched duration or zero denominator' if value is None else ''})
    write(ROOT/'results/sec_extended_ratio_comparison.csv',result)
    summary=[]
    for feature in NEW:
        rs=[r for r in result if r['feature']==feature]
        summary.append({'feature':feature,'requested':len(rs),**{k:sum(r['status']==k for r in rs) for k in ['match','different','unavailable']},
            'source_zero_nonzero_reconstruction':sum(r['source_zero_with_nonzero_reconstruction'] for r in rs)})
    write(ROOT/'results/sec_extended_summary.csv',summary)
    # Equivalent latest-date selector on an observed alternative input, not the whole source pipeline.
    raw=read(ROOT/'data/sensus_accession_instant_facts.csv');chosen={}
    for f in sorted(raw,key=lambda f:(f['adsh'],f['tag'],f['ddate'])):chosen[f['adsh'],f['tag']]=f
    debt=chosen['0001213900-20-036128','HeldToMaturitySecuritiesCurrent']
    assert debt['ddate']=='20191231' and float(debt['value'])==7389407
    case={'input':'Observed companyfacts USD instants within accession 0001213900-20-036128',
        'selected_investment_tag':debt['tag'],'selected_date':debt['ddate'],'selected_value':float(debt['value']),
        'target_period':'20200930','selected_prior_period':debt['ddate']<'20200930',
        'scope':'Equivalent isolated selector replay; not original NUM/PRE/TAG input and not end-to-end source pipeline replication'}
    (ROOT/'results/upstream_selector_replay.json').write_text(json.dumps(case,indent=2))
    checks={'comparisons':len(result),'summary':summary,'selector_prior_period_retained':True,
        'all_matched_flow_contexts':'60-120 inclusive days in original accession with common start/end',
        'scope':'Post hoc measurement audit; no new model result or population data-error estimate'}
    (ROOT/'results/measurement_audit_checks.json').write_text(json.dumps(checks,indent=2));print(json.dumps(checks,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['extract','analyze']);p.add_argument('--cache',type=Path);p.add_argument('--source-dir',type=Path);a=p.parse_args()
    if a.mode=='extract':
        if not a.cache or not a.source_dir:p.error('extract requires --cache and --source-dir')
        extract(a.cache,a.source_dir)
    else:analyze()
