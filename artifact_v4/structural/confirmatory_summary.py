"""Two predeclared aggregate contrasts; no policy selection or outcome filtering."""
from pathlib import Path
import json,hashlib,math
import numpy as np
from scipy.stats import t
HERE=Path(__file__).resolve().parent;A=HERE/'analysis'
def main():
 rows=json.loads((A/'per_fit.json').read_text());audits=json.loads((A/'calibration_audits.json').read_text());done=json.loads((A/'DONE.json').read_text())
 report={'protocol_sha256':hashlib.sha256((HERE/'PROTOCOL.md').read_bytes()).hexdigest(),'analysis_input_sha256':hashlib.sha256((A/'per_fit.json').read_bytes()).hexdigest(),'family_alpha':.05,'primary_hypotheses':2,'interval_level':.975,'contrasts':[]}
 for name,baseline in [('H1_retention','discovered_predictive'),('H2_structure','legacy_discovered_retained')]:
  cells=[];means=[];variances=[];dfs=[]
  for process in ['P1','P2','P3','P4','P5','P6']:
   pick=lambda m:{r['seed']:r for r in rows if r['process']==process and r['world']=='routing' and r['variant']=='main' and r['method']==m}
   left,right=pick('discovered_retained'),pick(baseline)
   seeds=sorted(set(left)&set(right));d=np.array([left[k]['normalized_cost']-right[k]['normalized_cost'] for k in seeds])
   cell_audits=[r for r in audits if r.get('process')==process and r['world']=='routing']
   valid=seeds==list(range(12)) and len(cell_audits)==132 and all(r['valid_precrisis'] for r in cell_audits)
   cells.append({'process':process,'seeds':seeds,'complete_and_precrisis':valid,'paired_normalized_differences':d.tolist()})
   if len(d)>1:means.append(float(d.mean()));variances.append(float(d.var(ddof=1)/len(d)));dfs.append(len(d)-1)
  complete=len(means)==6 and all(c['complete_and_precrisis'] for c in cells)
  item={'hypothesis':name,'method':'discovered_retained','baseline':baseline,'complete_and_precrisis':complete,'cells':cells}
  if complete:
   mean=sum(means)/6;variance=sum(variances)/36;den=sum(v*v/df for v,df in zip(variances,dfs));df=sum(variances)**2/den if den else 1e9
   half=float(t.ppf(1-.05/(2*2),df)*math.sqrt(variance));low,high=mean-half,mean+half
   item.update(mean=mean,low=low,high=high,df=df,benefit_established=high<0,weighting='equal 1/6 across predeclared designed process classes, independent fit-paired variance')
  else:item.update(benefit_established=False,reason='Prespecified complete pre-crisis coverage criterion not satisfied; no unqualified aggregate primary claim.')
  report['contrasts'].append(item)
  print({k:v for k,v in item.items() if k!='cells'},flush=True)
 report['campaign_accepted']=done['accepted'];report['campaign_failed']=done['failed']
 (A/'confirmatory_summary.json').write_text(json.dumps(report,indent=2,allow_nan=False))
if __name__=='__main__':main()
