"""Run narrowly scoped AST-selected source helpers on observed SEC facts.
Requires pandas, exact upstream file and retained API cache; no full pipeline reproduction.
No imports, top-level source commands, model fitting or source networking are executed.
"""
from pathlib import Path
import argparse,ast,csv,hashlib,json
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
def main(source,cache):
    with (ROOT/'documentation/upstream_code_manifest.csv').open() as f:
        fingerprint=next(r for r in csv.DictReader(f) if r['file']==source.name)
    raw=source.read_bytes();assert hashlib.sha256(raw).hexdigest()==fingerprint['sha256']
    with (ROOT/'documentation/sec_source_manifest.csv').open() as f:
        api_manifest={r['file']:r for r in csv.DictReader(f)}
    for filename in ['companyfacts_1365916.json','companyfacts_1494891.json']:
        assert hashlib.sha256((cache/filename).read_bytes()).hexdigest()==api_manifest[filename]['sha256'],'Changed API snapshot'
    tree=ast.parse(raw)
    functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['safe_divide','safe_sum','get_tag_value']]
    assert len(functions)==3
    namespace={'pd':pd};exec(compile(ast.Module(body=functions,type_ignores=[]),str(source),'exec'),namespace)
    src=json.loads((cache/'companyfacts_1365916.json').read_text())['facts']['us-gaap']
    acc='0001171843-18-006064';end='2018-06-30';start='2018-04-01'
    def vals(tag,flow=False):
        return {float(x['val']) for x in src.get(tag,{}).get('units',{}).get('USD',[]) if x['accn']==acc and x['end']==end and (x.get('start')==start if flow else not x.get('start'))}
    income=vals('NetIncomeLoss',True);modern=vals('RevenueFromContractWithCustomerIncludingAssessedTax',True);legacy=vals('Revenues',True)
    assert len(income)==len(modern)==1 and not legacy
    ni=next(iter(income));rev=next(iter(modern))
    got=namespace['safe_divide'](ni,namespace['get_tag_value']('Revenues',{}))
    # Source selector expression is evaluated as its actual AST statement on observed API instants.
    extract=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='extract_quarter_dataset')
    selector=next(n for n in extract.body if isinstance(n,ast.Assign) and 'drop_duplicates' in ast.unparse(n.value) and 'ddate' in ast.unparse(n.value))
    data=pd.read_csv(ROOT/'data/sensus_accession_instant_facts.csv')
    selector_ns={'df_num':data};exec(compile(ast.Module(body=[selector],type_ignores=[]),str(source),'exec'),selector_ns)
    row=selector_ns['df_num'].query("tag=='HeldToMaturitySecuritiesCurrent'").iloc[0]
    assert int(row.ddate)==20191231 and float(row.value)==7389407
    record={'original_source_sha256':fingerprint['sha256'],
        'loaded_source_functions':{n.name:[n.lineno,n.end_lineno] for n in functions},
        'called_source_helpers':['safe_divide','get_tag_value'],
        'executed_source_selector_lines':[selector.lineno,selector.end_lineno],
        'Amyris_actual_quarterly_income':ni,'Amyris_actual_modern_revenue':rev,
        'Amyris_legacy_Revenues_missing_in_API':True,'source_helper_margin_with_missing_legacy_tag':float(got),
        'observed_income_divided_by_modern_revenue':ni/rev,
        'source_selector_retains_Sensus_prior_investment':True,
        'selected_date':int(row.ddate),'selected_value':float(row.value),
        'scope':'Actual pinned helper/selector AST replay on observed alternative API inputs; not complete original NUM/PRE/TAG extraction or taxonomy imputation; not proof of the released snapshot production history'}
    (ROOT/'results/upstream_actual_function_replay.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--cache',type=Path,required=True);a=p.parse_args();main(a.source,a.cache)
