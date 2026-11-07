"""Fixed-score finite-sample AP reference and period-batch retrieval audit.

Requires original pinned sources and generated_test_scores.csv from analyze.py.
No fitting, tuning, relabeling or row exclusions occur here.
"""
from pathlib import Path
from itertools import combinations
import argparse, csv, hashlib, json, math
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
MODELS = ['logit', 'logit_balanced', 'forest', 'prevalence']

def random_ap(n, p):
    """Exact mean AP for all uniform tie-free rankings given 1 <= P <= N."""
    n, p = int(n), int(p)
    if not 1 <= p <= n:
        raise ValueError('Expected 1 <= positives <= records')
    if n == 1:
        return 1.0
    h = math.fsum(1.0/k for k in range(1, n+1))
    a = h/n
    return a + (p-1)/(n-1)*(1-a)

def retrieve(y, score, k):
    """Expected hits when uniformly resolving ties at the cutoff."""
    y, score = np.asarray(y), np.asarray(score)
    assert 1 <= k <= len(y)
    cut = np.sort(score)[-k]
    above, tied = score > cut, score == cut
    return float(y[above].sum() + (k-above.sum())*y[tied].mean())

def exhaustive_check():
    rows = []
    for n in range(1, 10):
        score = -np.arange(n)
        for p in range(1, n+1):
            total = 0.0
            count = 0
            for places in combinations(range(n), p):
                y = np.zeros(n, dtype=int)
                y[list(places)] = 1
                hand = sum(np.cumsum(y)[j]/(j+1) for j in places)/p
                actual = float(average_precision_score(y, score))
                assert math.isclose(hand, actual, abs_tol=1e-13)
                total += actual
                count += 1
            empirical = total/count
            exact = random_ap(n, p)
            assert math.isclose(empirical, exact, abs_tol=1e-13)
            rows.append(dict(records=n, positives=p, distinct_label_orderings=count,
                             exhaustive_mean_AP=empirical, formula_mean_AP=exact,
                             absolute_error=abs(empirical-exact)))
    return rows

def main(src, bootstrap):
    for r in csv.DictReader((ROOT/'documentation/source_manifest.csv').open()):
        if r['file'] in ['hf_train.csv', 'hf_test.csv']:
            assert hashlib.sha256((src/r['file']).read_bytes()).hexdigest() == r['sha256']
    raw = pd.concat([pd.read_csv(src/n) for n in ['hf_train.csv','hf_test.csv']], ignore_index=True)
    raw['release_sort'] = pd.to_datetime(raw.aeer_date, errors='coerce')
    d = raw.sort_values(['release_sort','report_id'], na_position='last').drop_duplicates(['cik','year','quarter']).copy()
    d['date'] = pd.to_datetime(d.period.astype(str), format='%Y%m%d')
    x = d[d.date.between('2019-01-01','2021-12-31')].copy()
    scores = pd.read_csv(src/'generated_test_scores.csv')
    assert scores.report_id.is_unique and set(scores.report_id) == set(x.report_id)
    x = x.merge(scores[['report_id']+MODELS], on='report_id', validate='one_to_one').sort_values('report_id')
    x['batch'] = x.date.dt.to_period('Q').astype(str)
    assert len(x) == 2695 and x.is_fraud.sum() == 93
    ref = pd.read_csv(ROOT/'results/metrics.csv').query("setting=='chronological'").set_index('model')
    y = x.is_fraud.astype(int).to_numpy()
    predictions = {m:x[m].to_numpy() for m in MODELS}
    for m in MODELS:
        assert abs(average_precision_score(y, predictions[m])-ref.loc[m,'AP']) < 1e-12
        assert abs(roc_auc_score(y, predictions[m])-ref.loc[m,'ROC_AUC']) < 1e-12
    exhaustive = exhaustive_check()
    pd.DataFrame(exhaustive).to_csv(ROOT/'results/random_AP_exhaustive_check.csv', index=False)
    exact = random_ap(len(x), int(y.sum()))
    point = {m:float(average_precision_score(y, predictions[m])) for m in MODELS}
    groups, inverse = np.unique(x.cik.to_numpy(), return_inverse=True)
    rng = np.random.default_rng(20261108)
    samples = {m:[] for m in MODELS}
    for _ in range(bootstrap):
        w = np.bincount(rng.integers(0,len(groups),len(groups)), minlength=len(groups))[inverse]
        n, p = int(w.sum()), int((w*y).sum())
        if p == 0 or p == n:
            continue
        # A cluster resample is an expanded multiset. Random ranking distinguishes
        # each record copy; fixed-score AP retains the actual model's ties.
        baseline = random_ap(n, p)
        for m in MODELS:
            samples[m].append(float(average_precision_score(y,predictions[m],sample_weight=w))-baseline)
    rows = []
    for m in MODELS:
        lo, hi = np.quantile(samples[m], [.025,.975])
        rows.append(dict(model=m, records=len(x), positives=int(y.sum()), constant_AP=y.mean(),
                         expected_random_tie_free_AP=exact, AP=point[m],
                         AP_minus_random_expectation=point[m]-exact,
                         contrast_lower=lo, contrast_upper=hi,
                         valid_cluster_replicates=len(samples[m])))
    pd.DataFrame(rows).to_csv(ROOT/'results/random_AP_reference.csv',index=False)
    detail, aggregate = [], []
    for rate in [.01,.05]:
        for m in MODELS:
            local = []
            for batch, b in x.groupby('batch', sort=True):
                k = math.ceil(rate*len(b))
                hits = retrieve(b.is_fraud.astype(int), b[m], k)
                local.append(dict(rate=rate, model=m, batch=batch, records=len(b),
                                  positives=int(b.is_fraud.sum()), capacity=k, expected_hits=hits,
                                  random_expected_hits=k*float(b.is_fraud.mean())))
            detail += local
            cap = sum(r['capacity'] for r in local)
            hits = sum(r['expected_hits'] for r in local)
            for setting, k, found, random_hits in [
                ('quarter_batches', cap, hits, sum(r['random_expected_hits'] for r in local)),
                ('pooled_original', math.ceil(rate*len(x)), retrieve(y,predictions[m],math.ceil(rate*len(x))),math.ceil(rate*len(x))*y.mean()),
                ('pooled_matched_quarter_capacity',cap,retrieve(y,predictions[m],cap),cap*y.mean())]:
                aggregate.append(dict(rate=rate,model=m,setting=setting,records=len(x),positives=int(y.sum()),
                                      capacity=k,capacity_fraction=k/len(x),expected_hits=found,
                                      precision=found/k,recall=found/y.sum(),random_expected_hits=random_hits))
            for rate_name, r in [(.01,'hits1'),(.05,'hits5')]:
                if rate == rate_name:
                    assert abs(retrieve(y,predictions[m],math.ceil(rate*len(x)))-ref.loc[m,r])<1e-12
    pd.DataFrame(detail).to_csv(ROOT/'results/period_batch_detail.csv',index=False)
    pd.DataFrame(aggregate).to_csv(ROOT/'results/period_batch_retrieval.csv',index=False)
    summary = dict(records=len(x),positives=int(y.sum()),calendar_quarter_batches=x.batch.nunique(),
                   batch_sizes=x.groupby('batch').size().to_dict(),
                   constant_AP=float(y.mean()),expected_random_tie_free_AP=exact,
                   random_reference_excess_over_constant=exact-y.mean(),
                   exhaustive_N_P_combinations=len(exhaustive),
                   exhaustive_label_orderings=sum(r['distinct_label_orderings'] for r in exhaustive),
                   maximum_exhaustive_error=max(r['absolute_error'] for r in exhaustive),
                   score_file_sha256=hashlib.sha256((src/'generated_test_scores.csv').read_bytes()).hexdigest(),
                   all_primary_AP_ROC_and_pooled_retrieval_reproduced=True,
                   no_refit_or_relabeling=True,
                   scope='Post hoc fixed scores; analytical random ordering reference, not a permutation test; period batches are not filing-time deployment.')
    (ROOT/'results/evaluation_reference_summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))
    print(pd.DataFrame(rows).to_string(index=False))
    print(pd.DataFrame(aggregate).query("model=='logit'").to_string(index=False))

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source-dir',type=Path,required=True)
    parser.add_argument('--bootstrap',type=int,default=1000)
    args=parser.parse_args()
    if args.bootstrap < 100:
        parser.error('Use at least 100 replicates')
    main(args.source_dir,args.bootstrap)
