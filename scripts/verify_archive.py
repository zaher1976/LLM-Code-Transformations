"""Check archived sampling, deltas and independent remeasurement without API calls."""
from pathlib import Path
import argparse, hashlib, textwrap, json
from collections import Counter
import numpy as np
import pandas as pd
from scipy import stats

p=argparse.ArgumentParser()
p.add_argument('--data-dir',type=Path,default=Path(__file__).resolve().parents[1]/'data')
p.add_argument('--output-dir',type=Path,default=Path(__file__).resolve().parents[1]/'outputs')
a=p.parse_args();a.output_dir.mkdir(parents=True,exist_ok=True)
r=a.data_dir
names=['corpus_dataset','curated_986_dataset','transformed_dataset','pipeline_final_metrics','pipeline_excluded_pairs','ablation_results','ablation_transformed']
f={n:pd.read_csv(r/(n+'.csv')) for n in names}
c,s,t,m,e,b,bt=[f[n] for n in names]
assert [len(x) for x in [c,s,t,m,e,b,bt]]==[5331,986,984,910,74,100,100]
for d in [s,t,m,e,b,bt]: assert not d.func_id.duplicated().any()
assert set(m.func_id).isdisjoint(e.func_id)
assert set(m.func_id)|set(e.func_id)==set(t.func_id)
assert set(t.func_id)<=set(s.func_id)
assert set(b.func_id)==set(bt.func_id)
assert set(b.func_id)<=set(m.func_id)
cols=['domain','file','function_name','cyclomatic_complexity','nloc','code']
counts=lambda d:Counter(d[cols].itertuples(index=False,name=None))
pred=pd.concat([c[c.domain.eq(k)].sample(n=v,random_state=42) for k,v in [('Matrix',280),('Crypto',210),('DataPipelines',246),('WebScraping',250)]])
assert counts(pred)==counts(s)
seed_sample=m[m.pre_comments_pct>0].sample(n=100,random_state=20261001)
assert set(seed_sample.func_id)==set(b.func_id)
num=m.select_dtypes('number').columns
for k in ['cc','nloc','cd','mi','mi_neutral','cognitive','volume','lloc','comments_pct','fmt_nloc','fmt_cd']:
 assert np.allclose(m['delta_'+k],m['post_'+k]-m['pre_'+k],atol=1e-9,rtol=0)
def compare(expected,actual):
 x=expected.set_index('func_id').sort_index();y=actual.set_index('func_id').sort_index()
 assert x.index.equals(y.index)
 assert set(x.columns)==set(y.columns)
 maxdiff=0.
 for k in x:
  if pd.api.types.is_numeric_dtype(x[k]) and not pd.api.types.is_bool_dtype(x[k]):
   xx=x[k].to_numpy(float);yy=y[k].to_numpy(float)
   assert np.allclose(xx,yy,atol=1e-9,rtol=0,equal_nan=True),k
   maxdiff=max(maxdiff,float(np.nanmax(np.abs(xx-yy))))
  else:assert x[k].fillna('').equals(y[k].fillna('')),k
 return maxdiff
main_diff=compare(m,pd.read_csv(a.output_dir/'pipeline_final_metrics.csv'))
abl_diff=compare(b,pd.read_csv(a.output_dir/'ablation_results.csv'))
rex=pd.read_csv(a.output_dir/'pipeline_excluded_pairs.csv')
assert set(zip(e.func_id,e.domain,e.stage))==set(zip(rex.func_id,rex.domain,rex.stage))
# Error wording may differ by Python version; identity/domain/stage are authoritative.
summaries={}
for k in ['cc','cognitive','nloc','fmt_nloc','cd','fmt_cd','mi','mi_neutral','volume','comments_pct']:
 z=m['delta_'+k];ci=stats.t.interval(.95,len(z)-1,loc=z.mean(),scale=stats.sem(z))
 summaries[k]={'mean_pre':float(m['pre_'+k].mean()),'mean_post':float(m['post_'+k].mean()),'mean_delta':float(z.mean()),'ci95':list(map(float,ci)),'decreased':int((z<0).sum()),'unchanged':int((z==0).sum()),'increased':int((z>0).sum())}
hashes=s.code.map(lambda z:hashlib.sha256(textwrap.dedent(str(z)).strip().encode()).hexdigest())
dup=s.loc[hashes.duplicated(False),['func_id','domain','file','function_name']]
nonzero=(m.pre_volume>0)&(m.post_volume>0)&(m.pre_lloc>0)&(m.post_lloc>0)
terms=['term_volume','term_cc','term_lloc','term_comments']
report={'status':'passed','row_counts':{k:len(v) for k,v in f.items()},'sampling_seed42_exact_row_multiset':True,'ablation_seed20261001_exact_ids':True,'main_remeasurement_max_abs_error':main_diff,'ablation_remeasurement_max_abs_error':abl_diff,'exclusion_id_domain_stage_match':True,'complete_source_row_duplicates_curated':int(s.duplicated(cols).sum()),'identical_normalized_source_records':dup.to_dict('records'),'documentation_loss':{'originally_documented':int((m.pre_comments_pct>0).sum()),'fully_lost':int(((m.pre_comments_pct>0)&m.post_comments_pct.eq(0)).sum())},'zero_volume':{'pre':int(m.pre_volume.eq(0).sum()),'post':int(m.post_volume.eq(0).sum()),'either':int((m.pre_volume.eq(0)|m.post_volume.eq(0)).sum())},'positive_volume_subset':{'n':int(nonzero.sum()),'formal_terms_mean':{k:float(m.loc[nonzero,k].mean()) for k in terms},'formal_sum_mean':float(m.loc[nonzero,terms].sum(axis=1).mean()),'observed_mi_change_mean':float(m.loc[nonzero,'delta_mi'].mean()),'observed_mi0_change_mean':float(m.loc[nonzero,'delta_mi_neutral'].mean())},'summary':summaries}
report['duplicate_text_sensitivity']={}
for fid in dup.func_id:
 z=m.loc[m.func_id.ne(fid)]
 report['duplicate_text_sensitivity'][fid]={k:float(z['delta_'+k].mean()) for k in ['cc','cognitive','mi','mi_neutral']}
(a.output_dir/'verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:report[k] for k in ['status','main_remeasurement_max_abs_error','ablation_remeasurement_max_abs_error','sampling_seed42_exact_row_multiset','ablation_seed20261001_exact_ids']},indent=2))
