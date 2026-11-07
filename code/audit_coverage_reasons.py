"""Describe unavailable accession comparisons; no model fit or data correction.

With --cache, reconstruct component availability from original SHA256-checked SEC
companyfacts payloads. Without --cache, use included component counts for offline
reproduction. Missing in this API subset does not mean missing in the filing.
"""
from pathlib import Path
from datetime import date
from collections import Counter, defaultdict
import argparse, csv, hashlib, json, math

ROOT=Path(__file__).resolve().parents[1]
REVENUE=['Revenues','SalesRevenueNet','RevenueFromContractWithCustomerExcludingAssessedTax','RevenueFromContractWithCustomerIncludingAssessedTax']
COMPONENTS={'income':['NetIncomeLoss'],'assets':['Assets'],'current_assets':['AssetsCurrent'],
 'current_liabilities':['LiabilitiesCurrent'],'inventory':['InventoryNet'],
 'revenue':REVENUE,'gross_profit':['GrossProfit'],'operating_income':['OperatingIncomeLoss']}
INSTANT={'assets','current_assets','current_liabilities','inventory'}
REQUIRED={'ratio_ReturnOnAssets':['income','assets'],
 'ratio_QuickRatio':['current_assets','inventory','current_liabilities'],
 'ratio_GrossProfitMargin':['gross_profit','revenue'],
 'ratio_OperatingMargin':['operating_income','revenue'],
 'ratio_NetProfitMargin':['income','revenue']}
PRIORITY=['unmatched_report_date','absent_current_accession_USD_fact','no_eligible_context_or_duration',
 'ambiguous_eligible_component','incompatible_flow_start','zero_denominator']

def read(p):
    with p.open(newline='') as f:return list(csv.DictReader(f))
def write(p,rows):
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def extract(cache,filings):
    manifest={r['file']:r for r in read(ROOT/'documentation/sec_source_manifest.csv')}
    out=[]
    for cik in sorted({r['cik'] for r in filings}):
        p=cache/f'companyfacts_{cik}.json';raw=p.read_bytes()
        assert hashlib.sha256(raw).hexdigest()==manifest[p.name]['sha256']
        data=json.loads(raw)['facts'].get('us-gaap',{})
        for f in [r for r in filings if r['cik']==cik]:
            for component,tags in COMPONENTS.items():
                selected=[];eligible=[]
                if f['matched']=='1':
                    for tag in tags:
                        for v in data.get(tag,{}).get('units',{}).get('USD',[]):
                            if v['accn']!=f['accessionNumber'] or v['end']!=f['reportDate']:continue
                            start=v.get('start','');selected.append((start,float(v['val'])))
                            if component in INSTANT:
                                if not start:eligible.append((start,float(v['val'])))
                            elif start and 60<=(date.fromisoformat(v['end'])-date.fromisoformat(start)).days+1<=120:
                                eligible.append((start,float(v['val'])))
                unique=sorted(set(eligible))
                out.append(dict(report_id=f['report_id'],component=component,matched=f['matched'],
                    exact_accession_end_USD_facts=len(selected),eligible_facts=len(eligible),
                    distinct_eligible_context_values=len(unique),
                    single_start=unique[0][0] if len(unique)==1 else '',
                    single_value=unique[0][1] if len(unique)==1 else ''))
    write(ROOT/'data/sec_component_availability.csv',out)
    return out

def main(cache=None):
    filings=read(ROOT/'data/sec_pilot_filing_extract.csv')
    records=extract(cache,filings) if cache else read(ROOT/'data/sec_component_availability.csv')
    by={(r['report_id'],r['component']):r for r in records}
    old=read(ROOT/'results/sec_extended_ratio_comparison.csv')
    assert len(records)==120*8 and len(by)==len(records)
    rows=[]
    for r in old:
        components=REQUIRED[r['feature']];rs={c:by[r['report_id'],c] for c in components}
        flags=set()
        if rs[components[0]]['matched']=='0':flags.add('unmatched_report_date')
        else:
            for c,v in rs.items():
                if int(v['exact_accession_end_USD_facts'])==0:flags.add('absent_current_accession_USD_fact')
                elif int(v['eligible_facts'])==0:flags.add('no_eligible_context_or_duration')
                elif int(v['distinct_eligible_context_values'])!=1:flags.add('ambiguous_eligible_component')
            if not flags:
                val={c:float(v['single_value']) for c,v in rs.items()}
                if r['feature']=='ratio_ReturnOnAssets':
                    denominator=val['assets'];value=val['income']/denominator if denominator else None
                elif r['feature']=='ratio_QuickRatio':
                    denominator=val['current_liabilities'];value=(val['current_assets']-val['inventory'])/denominator if denominator else None
                else:
                    numerator=components[0];denominator=val['revenue']
                    if rs[numerator]['single_start']!=rs['revenue']['single_start']:flags.add('incompatible_flow_start')
                    value=val[numerator]/denominator if denominator else None
                if not denominator:flags.add('zero_denominator')
                if not flags:
                    assert r['status']!='unavailable'
                    assert math.isclose(value,float(r['original_accession_ratio']),rel_tol=1e-12,abs_tol=1e-12)
        assert bool(flags)==(r['status']=='unavailable'),r
        rows.append(dict(report_id=r['report_id'],feature=r['feature'],original_status=r['status'],
            exclusive_reason=next((c for c in PRIORITY if c in flags),'computable'),
            all_reasons=';'.join(c for c in PRIORITY if c in flags)))
    write(ROOT/'results/sec_unavailable_reason_detail.csv',rows)
    summary=[]
    for feature in REQUIRED:
        selected=[r for r in rows if r['feature']==feature]
        for reason in ['computable']+PRIORITY:
            summary.append(dict(feature=feature,reason=reason,comparisons=sum(r['exclusive_reason']==reason for r in selected)))
    write(ROOT/'results/sec_unavailable_reason_summary.csv',summary)
    totals=Counter(r['exclusive_reason'] for r in rows)
    assert sum(totals.values())==600 and totals['computable']==370
    checks={'all_600_comparisons_accounted_for':len(rows)==600,'all_230_unavailable_reproduced':sum(bool(r['all_reasons']) for r in rows)==230,
        'all_370_computable_values_reproduced':totals['computable']==370,
        'all_120_reports_have_eight_component_records':len(by)==960,
        'exact_date_unmatched_requests_65':totals['unmatched_report_date']==65}
    result=dict(all_pass=all(checks.values()),checks=checks,exclusive_reason_counts=dict(totals),
        priority_rule=PRIORITY,scope='Descriptive classification of the selected audit; multiple component problems may coexist. Reasons describe retained API context coverage, not population errors or complete filing absence.')
    (ROOT/'results/coverage_reason_verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cache',type=Path);main(p.parse_args().cache)
