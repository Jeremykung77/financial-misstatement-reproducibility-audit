"""Descriptive SEC provenance audit. Frozen selection, no fitted predictive model.

Fetch: python code/sec_filing_audit.py fetch --cache local_sec
Analyze included extracts: python code/sec_filing_audit.py analyze
Rebuild extracts: python code/sec_filing_audit.py extract --cache local_sec --financials local_sources/hf_financials.csv
"""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import argparse, csv, hashlib, json, math, time, subprocess

ROOT = Path(__file__).resolve().parents[1]
TAGS = ['Assets', 'AssetsCurrent', 'Liabilities', 'LiabilitiesCurrent',
        'CashAndCashEquivalentsAtCarryingValue', 'NetIncomeLoss']
RATIOS = {
    'ratio_CurrentRatio': ('AssetsCurrent', 'LiabilitiesCurrent'),
    'ratio_WorkingCapitalToTotalAssets': ('WORKING_CAPITAL', 'Assets'),
    'ratio_TotalLiabilitiesToAssets': ('Liabilities', 'Assets'),
    'ratio_CashToTotalAsset': ('CashAndCashEquivalentsAtCarryingValue', 'Assets'),
}
# Follow-up definitions, added after observing cash-only discrepancies.
CASH_DIAGNOSTIC_TAGS = ['ShortTermInvestments','OtherShortTermInvestments',
    'MarketableSecuritiesCurrent','AvailableForSaleSecuritiesDebtSecuritiesCurrent',
    'AvailableForSaleSecuritiesCurrent','ShortTermInvestmentsAvailableForSale',
    'CashCashEquivalentsAndShortTermInvestments']

def read_csv(path):
    with Path(path).open(newline='') as f:
        return list(csv.DictReader(f))

def write_csv(path, rows, fields=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not fields:
        fields = list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)

def selection():
    return read_csv(ROOT/'documentation/SEC_PILOT_SELECTION.csv')

def verify_selection(source_dir):
    records=read_csv(source_dir/'hf_train.csv')+read_csv(source_dir/'hf_test.csv')
    records.sort(key=lambda r:(r['aeer_date'] or '9999',int(r['report_id'])))
    unique={}
    for r in records:unique.setdefault((r['cik'],r['year'],r['quarter']),r)
    cohort=list(unique.values())
    evaluation=[r for r in cohort if '20190101'<=r['period']<='20211231']
    positives=[r for r in evaluation if r['is_fraud']=='True']
    positive_firms={r['cik'] for r in cohort if r['is_fraud']=='True'}
    control_firms=sorted({r['cik'] for r in evaluation if r['cik'] not in positive_firms},
        key=lambda c:hashlib.sha256(('SEC-PILOT-20261106:'+c).encode()).hexdigest())[:26]
    controls=[min((r for r in evaluation if r['cik']==c),key=lambda r:(r['period'],int(r['report_id']))) for c in control_firms]
    amy=next(r for r in cohort if r['cik']=='1365916' and r['period']=='20180630')
    rebuilt=[]
    for group,items in [('all_positive_evaluation',positives),('hashed_nonlinked_control',controls),('targeted_Amyris_example',[amy])]:
        for r in items:rebuilt.append({k:r[k] for k in ['report_id','cik','year','quarter','period','is_fraud']}|{'selection_group':group})
    assert sorted(rebuilt,key=lambda r:int(r['report_id']))==sorted(selection(),key=lambda r:int(r['report_id'])), 'Selection differs from frozen snapshot'
    print('PASS: all 120 frozen selections reconstructed from the original split files')

def load(cache, name):
    return json.loads((cache/name).read_text())

def fetch(cache):
    cache.mkdir(parents=True, exist_ok=True)
    manifest_path = cache/'fetch_manifest.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    def get(name, url):
        dest = cache/name
        if dest.exists():
            if name not in manifest:
                raise ValueError('Cache needs recorded retrieval provenance: '+name)
            if hashlib.sha256(dest.read_bytes()).hexdigest() != manifest[name]['sha256']:
                raise ValueError('Changed cached source: '+name)
            return load(cache, name)
        time.sleep(.2)
        rec = {'file': name, 'url': url, 'retrieved_utc': datetime.now(timezone.utc).isoformat()}
        try:
            # System curl uses the operating system trust store; TLS verification stays enabled.
            response = subprocess.run(['curl','--silent','--show-error','--fail','--location',
                '--max-time','45','--max-filesize','30000000','--user-agent',
                'AcademicFinancialMisstatementResearch/1.0 public-reproducibility-audit',url],
                capture_output=True,check=True)
            raw = response.stdout
            if len(raw)>30_000_000:
                raise ValueError('Payload exceeds pilot bound')
            value = json.loads(raw)
            dest.write_bytes(raw)
            rec.update(status='ok', bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        except Exception as exc:
            detail = exc.stderr.decode(errors='replace') if isinstance(exc,subprocess.CalledProcessError) else str(exc)
            rec.update(status='error', error=detail); value=None
        manifest[name] = rec
        manifest_path.write_text(json.dumps(manifest, indent=2))
        return value
    selected = selection()
    for i,cik in enumerate(sorted({int(r['cik']) for r in selected})):
        periods=[datetime.strptime(r['period'],'%Y%m%d').date() for r in selected if int(r['cik'])==cik]
        first,last=min(periods),(max(periods)+timedelta(days=366))
        facts=get(f'companyfacts_{cik}.json',f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010}.json')
        sub=get(f'submissions_{cik}.json',f'https://data.sec.gov/submissions/CIK{cik:010}.json')
        if sub:
            for history in sub['filings'].get('files',[]):
                if history['filingFrom']<=last.isoformat() and history['filingTo']>=first.isoformat():
                    get(history['name'],'https://data.sec.gov/submissions/'+history['name'])
        print(f'{i+1}/53 CIK {cik} facts={facts is not None} submissions={sub is not None}',flush=True)
    write_csv(ROOT/'documentation/sec_source_manifest.csv',list(manifest.values()))

def columnar_rows(data):
    return [{k:v[i] for k,v in data.items()} for i in range(len(data.get('accessionNumber',[])))]

def extract(cache, financials):
    selected=selection(); wanted={(int(r['cik']),r['period']) for r in selected}
    ratios={}
    with Path(financials).open(newline='') as f:
        for r in csv.DictReader(f):
            if (int(r['cik']),r['period']) in wanted:
                key=(int(r['cik']),r['period'])
                if key in ratios: raise ValueError('Duplicate source period')
                ratios[key]={k:r[k] for k in RATIOS}
    assert len(ratios)==len(wanted)
    filing_rows=[];fact_rows=[];cash_rows=[];nearby_rows=[]
    for r in selected:
        cik=int(r['cik']);end=datetime.strptime(r['period'],'%Y%m%d').date().isoformat()
        identity={k:r[k] for k in ['report_id','cik','period','selection_group']}
        fs=cache/f'companyfacts_{cik}.json';ss=cache/f'submissions_{cik}.json'
        metadata=[]
        if ss.exists():
            sub=load(cache,ss.name);metadata=columnar_rows(sub['filings']['recent'])
            for h in sub['filings'].get('files',[]):
                if (cache/h['name']).exists():metadata+=columnar_rows(load(cache,h['name']))
        by_accn={}
        for item in metadata:
            acc=item['accessionNumber']
            if acc in by_accn and by_accn[acc]!=item:raise ValueError('Conflicting filing metadata')
            by_accn[acc]=item
        matches=[m for m in by_accn.values() if m['form'] in ['10-Q','10-K'] and m['reportDate']==end and m['filingDate']>=end]
        matches.sort(key=lambda m:(m['filingDate'],m.get('acceptanceDateTime',''),m['accessionNumber']))
        chosen=matches[0] if matches else {}
        if not matches:
            for item in by_accn.values():
                if item['form'] not in ['10-Q','10-K'] or not item.get('reportDate'):continue
                delta=(datetime.fromisoformat(item['reportDate'])-datetime.fromisoformat(end)).days
                if abs(delta)<=7:
                    nearby_rows.append(identity|{'accessionNumber':item['accessionNumber'],
                        'candidate_report_date':item['reportDate'],'source_period_date':end,
                        'difference_days':delta,'filingDate':item['filingDate'],'form':item['form'],
                        'primary_document_url':f"https://www.sec.gov/Archives/edgar/data/{cik}/{item['accessionNumber'].replace('-','')}/{item['primaryDocument']}"})
        filing_rows.append(identity|{'matched':int(bool(chosen)),'matching_accessions':len(matches),
            'name':sub.get('name','') if ss.exists() else '',
            **{k:chosen.get(k,'') for k in ['accessionNumber','filingDate','reportDate','acceptanceDateTime','form','primaryDocument']},
            'date_level_available_from':(datetime.strptime(chosen['filingDate'],'%Y-%m-%d').date()+timedelta(days=1)).isoformat() if chosen else '',
            'filing_lag_days':(datetime.strptime(chosen['filingDate'],'%Y-%m-%d').date()-datetime.fromisoformat(end).date()).days if chosen else '',
            'primary_document_url':f"https://www.sec.gov/Archives/edgar/data/{cik}/{chosen['accessionNumber'].replace('-','')}/{chosen['primaryDocument']}" if chosen else '',
            **ratios[(cik,r['period'])]})
        if not fs.exists():continue
        facts=load(cache,fs.name)
        for tag in CASH_DIAGNOSTIC_TAGS:
            for fact in facts.get('facts',{}).get('us-gaap',{}).get(tag,{}).get('units',{}).get('USD',[]):
                if fact['accn']==chosen.get('accessionNumber') and fact['end']==end and not fact.get('start'):
                    cash_rows.append(identity|{'tag':tag,'value':fact['val'],'unit':'USD','end':end,
                        'accessionNumber':fact['accn'],'filed':fact['filed']})
        for tag in TAGS:
            for fact in facts.get('facts',{}).get('us-gaap',{}).get(tag,{}).get('units',{}).get('USD',[]):
                if fact['end']!=end or fact['form'] not in ['10-Q','10-Q/A','10-K','10-K/A']:continue
                start=fact.get('start','')
                duration=(datetime.fromisoformat(end)-datetime.fromisoformat(start)).days+1 if start else None
                if tag=='NetIncomeLoss' and (duration is None or not 60<=duration<=120):continue
                if tag!='NetIncomeLoss' and start:continue
                meta=by_accn.get(fact['accn'],{})
                fact_rows.append(identity|{'tag':tag,'unit':'USD','start':start,'end':end,'value':fact['val'],
                    'accessionNumber':fact['accn'],'filed':fact['filed'],'form':fact['form'],
                    'in_chosen_accession':int(fact['accn']==chosen.get('accessionNumber')),
                    'acceptanceDateTime':meta.get('acceptanceDateTime',''),
                    'primary_document_url':f"https://www.sec.gov/Archives/edgar/data/{cik}/{fact['accn'].replace('-','')}/{meta['primaryDocument']}" if meta.get('primaryDocument') else ''})
    write_csv(ROOT/'data/sec_pilot_filing_extract.csv',filing_rows)
    write_csv(ROOT/'data/sec_pilot_fact_extract.csv',fact_rows)
    write_csv(ROOT/'data/sec_pilot_cash_diagnostic_extract.csv',cash_rows)
    write_csv(ROOT/'results/sec_pilot_unmatched_candidates.csv',nearby_rows)
    analyze()

def analyze():
    selected=selection();filings=read_csv(ROOT/'data/sec_pilot_filing_extract.csv');facts=read_csv(ROOT/'data/sec_pilot_fact_extract.csv')
    assert len(filings)==len(selected)==120
    assert {(x['report_id'],x['period']) for x in filings}=={(x['report_id'],x['period']) for x in selected}
    cash_facts=read_csv(ROOT/'data/sec_pilot_cash_diagnostic_extract.csv')
    comparisons=[];coverage=[];changes=[];cash_checks=[]
    for row in filings:
        mine=[x for x in facts if x['report_id']==row['report_id']]
        values={}
        for tag in TAGS:
            chosen=[x for x in mine if x['tag']==tag and x['in_chosen_accession']=='1']
            # More than one quarterly duration is ambiguous even if values happen to agree.
            distinct={(x['start'],x['end'],float(x['value'])) for x in chosen}
            if len(distinct)==1:values[tag]=next(iter(distinct))[2]
            coverage.append({'report_id':row['report_id'],'selection_group':row['selection_group'],'tag':tag,
                'status':'unique' if len(distinct)==1 else 'missing' if not distinct else 'ambiguous'})
            starts={x['start'] for x in mine if x['tag']==tag}
            for start in starts:
                group=[x for x in mine if x['tag']==tag and x['start']==start]
                original=[x for x in group if x['in_chosen_accession']=='1']
                if len({float(x['value']) for x in original})!=1:continue
                first=original[0]
                later=[x for x in group if x['filed']>first['filed'] and float(x['value'])!=float(first['value'])]
                if later:
                    nxt=min(later,key=lambda x:(x['filed'],x['accessionNumber']))
                    changes.append({'report_id':row['report_id'],'cik':row['cik'],'period':row['period'],'selection_group':row['selection_group'],
                        'tag':tag,'start':start,'end':first['end'],'original_value':float(first['value']),
                        'later_value':float(nxt['value']),'original_accession':first['accessionNumber'],
                        'later_accession':nxt['accessionNumber'],'original_filed':first['filed'],'later_filed':nxt['filed']})
        if 'AssetsCurrent' in values and 'LiabilitiesCurrent' in values:
            values['WORKING_CAPITAL']=values['AssetsCurrent']-values['LiabilitiesCurrent']
        for ratio,(num,den) in RATIOS.items():
            value=values[num]/values[den] if num in values and den in values and values[den]!=0 else None
            benchmark=float(row[ratio])
            comparisons.append({'report_id':row['report_id'],'cik':row['cik'],'period':row['period'],
                'selection_group':row['selection_group'],'ratio':ratio,'reconstructed':value,'processed_source':benchmark,
                'status':'unavailable' if value is None else 'match' if math.isclose(value,benchmark,rel_tol=1e-6,abs_tol=1e-8) else 'different',
                'absolute_difference':abs(value-benchmark) if value is not None else None})
            if ratio=='ratio_CashToTotalAsset' and comparisons[-1]['status']=='different':
                candidates={}
                for tag in CASH_DIAGNOSTIC_TAGS:
                    vals={float(x['value']) for x in cash_facts if x['report_id']==row['report_id'] and x['tag']==tag}
                    if len(vals)==1:
                        amount=next(iter(vals))
                        numerator=amount if tag=='CashCashEquivalentsAndShortTermInvestments' else values['CashAndCashEquivalentsAtCarryingValue']+amount
                        candidates[tag]=numerator/values['Assets']
                compatible=[tag for tag,v in candidates.items() if math.isclose(v,benchmark,rel_tol=1e-6,abs_tol=1e-8)]
                cash_checks.append({'report_id':row['report_id'],'cik':row['cik'],'period':row['period'],
                    'selection_group':row['selection_group'],'processed_source':benchmark,
                    'narrow_cash_ratio':value,'compatible_definition_tags':';'.join(compatible),
                    'reconciled_numerically':int(bool(compatible)),
                    'candidate_ratios_json':json.dumps(candidates,sort_keys=True)})
    out=ROOT/'results'
    write_csv(out/'sec_pilot_ratio_comparison.csv',comparisons)
    write_csv(out/'sec_pilot_fact_coverage.csv',coverage)
    write_csv(out/'sec_pilot_version_changes.csv',changes)
    write_csv(out/'sec_pilot_cash_reconciliation.csv',cash_checks)
    manual=read_csv(ROOT/'data/sec_pilot_manual_filing_check.csv')
    m={(r['period_end'],r['line_item']):float(r['USD_value']) for r in manual}
    current_cash=m[('2020-09-30','cash_and_cash_equivalents')]
    current_assets=m[('2020-09-30','total_assets')]
    prior_investment=m[('2019-12-31','investment_in_debt_securities')]
    processed=float(next(r['processed_source'] for r in comparisons if r['cik']=='1494891' and r['period']=='20200930' and r['ratio']=='ratio_CashToTotalAsset'))
    residual={'CIK':1494891,'period':'2020-09-30','original_current_cash':current_cash,
        'original_current_investment':m[('2020-09-30','investment_in_debt_securities')],
        'original_prior_year_investment':prior_investment,'original_current_assets_total':current_assets,
        'processed_ratio':processed,'current_cash_over_assets':current_cash/current_assets,
        'cash_plus_prior_year_investment_over_current_assets':(current_cash+prior_investment)/current_assets,
        'absolute_difference_to_processed':abs((current_cash+prior_investment)/current_assets-processed),
        'interpretation':'Exact numerical compatibility with including the prior-year investment balance; original transformation code not re-executed, so implementation cause is unproven. Not evidence of future-information leakage.'}
    (out/'sec_pilot_residual_case.json').write_text(json.dumps(residual,indent=2))
    summary=[]
    for group in sorted({r['selection_group'] for r in filings}):
        sub=[r for r in filings if r['selection_group']==group]
        for ratio in RATIOS:
            c=[r for r in comparisons if r['selection_group']==group and r['ratio']==ratio]
            summary.append({'group':group,'n_observations':len(sub),'firms':len({r['cik'] for r in sub}),
                'matched_statutory_filings':sum(r['matched']=='1' for r in sub),'ratio':ratio,
                **{status:sum(r['status']==status for r in c) for status in ['match','different','unavailable']}})
    write_csv(out/'sec_pilot_summary.csv',summary)
    audit={'observations':len(filings),'firms':len({r['cik'] for r in filings}),
        'matched_statutory_filings':sum(r['matched']=='1' for r in filings),
        'fact_extract_rows':len(facts),'ratio_comparisons':len(comparisons),
        'ratio_matches':sum(r['status']=='match' for r in comparisons),
        'ratio_differences':sum(r['status']=='different' for r in comparisons),
        'ratio_unavailable':sum(r['status']=='unavailable' for r in comparisons),
        'changed_fact_contexts':len(changes),'observations_with_changed_facts':len({r['report_id'] for r in changes}),
        'cash_differences_numerically_reconciled':sum(r['reconciled_numerically'] for r in cash_checks),
        'limitation':'Post hoc selected-company source audit; no population error-rate inference, model refit, new holdout, or claim of complete point-in-time data.'}
    (out/'sec_pilot_checks.json').write_text(json.dumps(audit,indent=2))
    print(json.dumps(audit,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['fetch','extract','analyze','verify-selection']);p.add_argument('--cache',type=Path,default=Path('local_sec'));p.add_argument('--financials',type=Path);p.add_argument('--source-dir',type=Path)
    a=p.parse_args()
    if a.mode=='fetch':fetch(a.cache)
    elif a.mode=='extract':
        if not a.financials:p.error('extract requires --financials')
        extract(a.cache,a.financials)
    elif a.mode=='verify-selection':
        if not a.source_dir:p.error('verify-selection requires --source-dir')
        verify_selection(a.source_dir)
    else:analyze()
