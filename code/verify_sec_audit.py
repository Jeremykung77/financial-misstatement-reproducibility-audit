"""Separate consistency checks of the included SEC pilot extracts; no external peer review."""
from pathlib import Path
from collections import Counter, defaultdict
from datetime import date, timedelta
import argparse, csv, hashlib, json, math

ROOT=Path(__file__).resolve().parents[1]
def rows(name):
    with (ROOT/name).open(newline='') as f:return list(csv.DictReader(f))
def main(cache=None):
    selection=rows('documentation/SEC_PILOT_SELECTION.csv')
    filings=rows('data/sec_pilot_filing_extract.csv');facts=rows('data/sec_pilot_fact_extract.csv')
    comparisons=rows('results/sec_pilot_ratio_comparison.csv')
    checks={}
    checks['frozen_selection_and_filing_ids']=len(selection)==120 and len({r['cik'] for r in selection})==53 and {r['report_id'] for r in selection}=={r['report_id'] for r in filings}
    checks['selection_groups']=Counter(r['selection_group'] for r in selection)=={'all_positive_evaluation':93,'hashed_nonlinked_control':26,'targeted_Amyris_example':1}
    by_id={r['report_id']:r for r in filings}
    chosen=[f for f in facts if f['in_chosen_accession']=='1']
    checks['chosen_fact_accession_date_unit']=all(f['accessionNumber']==by_id[f['report_id']]['accessionNumber'] and f['filed']==by_id[f['report_id']]['filingDate'] and f['unit']=='USD' for f in chosen)
    checks['exact_report_dates_and_next_day']=all(r['reportDate']==f"{r['period'][:4]}-{r['period'][4:6]}-{r['period'][6:]}" and r['date_level_available_from']==(date.fromisoformat(r['filingDate'])+timedelta(days=1)).isoformat() and date.fromisoformat(r['filingDate'])>=date.fromisoformat(r['reportDate']) for r in filings if r['matched']=='1')
    checks['quarter_duration_not_annual']=all(60<=(date.fromisoformat(r['end'])-date.fromisoformat(r['start'])).days+1<=120 if r['tag']=='NetIncomeLoss' else r['start']=='' for r in facts)
    checks['comparison_partition']=len(comparisons)==480 and Counter(r['status'] for r in comparisons)=={'match':353,'different':20,'unavailable':107}
    checks['all_raw_differences_are_narrow_cash']=all(r['ratio']=='ratio_CashToTotalAsset' for r in comparisons if r['status']=='different')
    checks['match_flags_agree_with_numbers']=all((r['status']=='match')==math.isclose(float(r['reconstructed']),float(r['processed_source']),rel_tol=1e-6,abs_tol=1e-8) for r in comparisons if r['status']!='unavailable')
    amy=[r for r in facts if r['cik']=='1365916' and r['tag']=='NetIncomeLoss' and r['start']=='2018-04-01']
    checks['Amyris_original_and_later_earnings']=any(r['accessionNumber']=='0001171843-18-006064' and float(r['value'])==1533000 for r in amy) and any(r['accessionNumber']=='0001171843-19-006389' and float(r['value'])==-14382000 for r in amy)
    nearby=rows('results/sec_pilot_unmatched_candidates.csv')
    checks['nearby_candidates_not_silently_used']=len(nearby)==13 and len({r['report_id'] for r in nearby})==13 and all(by_id[r['report_id']]['matched']=='0' and 0<abs(int(r['difference_days']))<=7 for r in nearby)
    cash=rows('results/sec_pilot_cash_reconciliation.csv')
    checks['cash_reconciliation_denominator']=len(cash)==20 and sum(int(r['reconciled_numerically']) for r in cash)==19
    manual=rows('data/sec_pilot_manual_filing_check.csv')
    md={(r['period_end'],r['line_item']):float(r['USD_value']) for r in manual}
    rr=next(r for r in comparisons if r['cik']=='1494891' and r['ratio']=='ratio_CashToTotalAsset')
    residual=(md[('2020-09-30','cash_and_cash_equivalents')]+md[('2019-12-31','investment_in_debt_securities')])/md[('2020-09-30','total_assets')]
    checks['residual_prior_period_fingerprint']=md[('2020-09-30','investment_in_debt_securities')]==0 and math.isclose(residual,float(rr['processed_source']),rel_tol=1e-12,abs_tol=1e-12)
    manifest=rows('documentation/sec_source_manifest.csv')
    checks['all_recorded_official_fetches_succeeded']=len(manifest)==108 and all(r['status']=='ok' and r['url'].startswith('https://data.sec.gov/') and len(r['sha256'])==64 for r in manifest)
    if cache:
        checks['raw_cache_payload_hashes']=all((cache/r['file']).exists() and hashlib.sha256((cache/r['file']).read_bytes()).hexdigest()==r['sha256'] for r in manifest)
        checks['raw_entity_identity']=all(json.loads((cache/f"companyfacts_{cik}.json").read_text())['cik']==int(cik) and int(json.loads((cache/f"submissions_{cik}.json").read_text())['cik'])==int(cik) for cik in {r['cik'] for r in selection})
    result={'checks':checks,'all_pass':all(checks.values()),'raw_cache_checked':bool(cache),
        'scope':'Internal consistency checks within the same AI-assisted workflow; not independent-team replication.'}
    (ROOT/'results/sec_pilot_verification.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
    if not result['all_pass']:raise SystemExit(1)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cache',type=Path);main(p.parse_args().cache)
