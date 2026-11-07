"""Compare pinned annotations without changing labels, cohorts or model scores."""
from pathlib import Path
from collections import defaultdict, Counter
import argparse, ast, csv, hashlib, json, re, zipfile
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
def write(name,rows):
    with (ROOT/'results'/name).open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def main(src,ann):
    for r in csv.DictReader((ROOT/'documentation/source_manifest.csv').open()):
        if r['file'] in ['hf_train.csv','hf_test.csv']:
            assert hashlib.sha256((src/r['file']).read_bytes()).hexdigest()==r['sha256']
    for r in csv.DictReader((ROOT/'documentation/annotation_source_manifest.csv').open()):
        b=(ann/r['file']).read_bytes()
        assert len(b)==int(r['bytes']) and hashlib.sha256(b).hexdigest()==r['sha256']
        if r['git_blob_sha1']:
            assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==r['git_blob_sha1']
    raw=pd.concat([pd.read_csv(src/name) for name in ['hf_train.csv','hf_test.csv']],ignore_index=True)
    raw['release_sort']=pd.to_datetime(raw.aeer_date,errors='coerce')
    key=['cik','year','quarter']
    assert raw[key].notna().all().all()
    d=raw.sort_values(['release_sort','report_id'],na_position='last').drop_duplicates(key).copy()
    assert len(d)==14657
    d['comparison_fiscal_quarter']=d.year.astype(int).astype(str)+d.quarter
    d['stage']=d.period.map(lambda p:'development' if p<=20151231 else 'validation' if p<=20171231 else 'gap' if p<=20181231 else 'evaluation')
    a=pd.read_csv(ann/'hf_aaer_since2009.csv',keep_default_na=False)
    assert len(a)==1451 and not a.duplicated(['cik','fiscal_quarter']).any()
    assert a.fiscal_quarter.str.fullmatch(r'\d{4}q[1-4]').all()
    idx={(int(r.cik),r.fiscal_quarter):r for r in a.itertuples()}
    links=defaultdict(set)
    for r in raw[raw.is_fraud].itertuples():
        links[(int(r.cik),int(r.year),r.quarter)].add(r.aaer_no)
    annotated=[]
    for r in d.itertuples():
        record=idx.get((int(r.cik),r.comparison_fiscal_quarter))
        exists=record is not None
        original=links[(int(r.cik),int(r.year),r.quarter)]
        annotated.append(dict(report_id=int(r.report_id),cik=int(r.cik),financial_fiscal_quarter=r.comparison_fiscal_quarter,
            period=int(r.period),stage=r.stage,benchmark_positive=int(r.is_fraud),
            representative_AAER=r.aaer_no if r.is_fraud else '',
            annotation_company=record.company if exists else '',annotation_AAER=record.aaer_no if exists else '',
            annotation_url=record.url if exists else '',company_quarter_annotation=int(exists),
            exact_representative_AAER_match=int(exists and r.is_fraud and record.aaer_no==r.aaer_no),
            any_original_AAER_match=int(exists and record.aaer_no in original)))
    x=pd.DataFrame(annotated);test=x[x.stage.eq('evaluation')]
    assert len(test)==2695 and test.benchmark_positive.sum()==93
    counts=[]
    for stage,n,pos in [('development',7799,342),('validation',3069,133),('gap',1094,60),('evaluation',2695,93)]:
        group=x[x.stage.eq(stage)]
        assert len(group)==n and group.benchmark_positive.sum()==pos
        for outcome in [0,1]:
            z=group[group.benchmark_positive.eq(outcome)]
            counts.append(dict(stage=stage,benchmark_positive=outcome,records=len(z),
                company_quarter_annotation=int(z.company_quarter_annotation.sum()),
                exact_representative_AAER_match=int(z.exact_representative_AAER_match.sum()),
                any_original_AAER_match=int(z.any_original_AAER_match.sum()),
                other_AAER_only=int((z.company_quarter_annotation.eq(1)&z.exact_representative_AAER_match.eq(0)).sum()),
                no_annotation=int(z.company_quarter_annotation.eq(0).sum())))
    write('annotation_match_by_stage.csv',counts)
    write('evaluation_positive_annotation_crosswalk.csv',test[test.benchmark_positive.eq(1)].to_dict('records'))
    controls=x[x.benchmark_positive.eq(0)&x.company_quarter_annotation.eq(1)]
    write('annotation_control_candidates.csv',controls.to_dict('records'))
    cases=[];archive=[]
    with zipfile.ZipFile(ann/'AAER_DETAILS.zip') as z:
        names={n for n in z.namelist() if n.endswith('.json')}
        numbers=[int(re.search(r'AAER-(\d+)',n).group(1)) for n in names]
        for (cik,aaer),b in test[test.benchmark_positive.eq(1)].groupby(['cik','representative_AAER']):
            strict=a[(a.cik==cik)&a.aaer_no.eq(aaer)]
            any_release=a[a.cik==cik]
            cases.append(dict(cik=int(cik),representative_AAER=aaer,evaluation_positives=len(b),
                benchmark_fiscal_quarters=';'.join(sorted(b.financial_fiscal_quarter)),
                same_release_annotation_quarters=';'.join(sorted(strict.fiscal_quarter)),
                any_release_annotation_quarters=';'.join(sorted(any_release.fiscal_quarter)),
                company_quarter_matches=int(b.company_quarter_annotation.sum()),
                representative_release_matches=int(b.exact_representative_AAER_match.sum())))
            path=f'AAER_DETAILS/{aaer}.json';present=path in names
            j=json.loads(z.read(path)) if present else {}
            archive.append(dict(cik=int(cik),representative_AAER=aaer,present_in_details_archive=int(present),
                                archived_details_count=len(j.get('details',[])) if present else '',
                                scope='Archive coverage only; absent file is not absent misconduct or an adjudicated label error'))
    write('annotation_case_comparison.csv',cases);write('annotation_archive_coverage.csv',archive)
    source=(ann/'sec_aaer_content_extractor.py').read_text();tree=ast.parse(source)
    prompt=next(ast.literal_eval(node.value) for node in tree.body if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SYSTEM_PROMPT' for t in node.targets))
    assert '**Full Years**' in prompt and 'all four quarters' in prompt
    assert 'purely disclosure-related' in prompt
    preprocessing=(ann/'sec_aaer_preprocessing.py').read_text()
    assert 'if len(misstatements) == 0:' in preprocessing
    assert 'existing_row = df_aaer[' in preprocessing
    summary=dict(annotation_rows=len(a),unique_company_quarters=len(idx),annotation_release_company_pairs=len(a[['aaer_no','cik']].drop_duplicates()),
        benchmark_records=len(d),benchmark_positives=int(d.is_fraud.sum()),evaluation_records=len(test),evaluation_positives=int(test.benchmark_positive.sum()),
        evaluation_positive_company_quarter_matches=int(test.loc[test.benchmark_positive.eq(1),'company_quarter_annotation'].sum()),
        evaluation_positive_representative_release_matches=int(test.exact_representative_AAER_match.sum()),
        evaluation_positive_any_original_release_matches=int(test.any_original_AAER_match.sum()),
        control_annotation_candidates_all_stages=len(controls),control_annotation_candidates_evaluation=int(controls.stage.eq('evaluation').sum()),
        archive_json_records=len(names),archive_min_numeric_AAER=min(numbers),archive_max_numeric_AAER=max(numbers),
        evaluation_representative_links_present_in_archive=sum(r['present_in_details_archive'] for r in archive),
        prompt_year_expansion_observed=True,prompt_excludes_pure_disclosure=True,preprocessing_empty_categories_excluded=True,
        no_fit_relabel_or_metric_change=True,
        scope='Cross-file annotation compatibility, not validated population label accuracy; exact production lineage and all case-quarter adjudication remain unresolved')
    (ROOT/'results/annotation_alignment_summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2));print(pd.DataFrame(counts).to_string(index=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source-dir',type=Path,required=True);p.add_argument('--annotation-dir',type=Path,required=True)
    a=p.parse_args();main(a.source_dir,a.annotation_dir)
