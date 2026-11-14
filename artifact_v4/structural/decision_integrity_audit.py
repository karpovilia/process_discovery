"""Independent arithmetic and provenance check from sealed raw policy outcomes.
No new simulation, method choice, outcome exclusion or parameter selection.
"""
from pathlib import Path
import hashlib,json,math,statistics
from scipy.stats import t
from learning import compare_languages
HERE=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def near(a,b):
 if not math.isclose(a,b,rel_tol=1e-11,abs_tol=1e-11):raise AssertionError((a,b))

def main():
 freeze=json.loads((HERE/'FREEZE.json').read_text());source_freeze=HERE/('SOURCE_FREEZE.json' if (HERE/'SOURCE_FREEZE.json').exists() else 'FREEZE.json')
 for name,digest in freeze['files'].items():assert sha(HERE/name)==digest,name
 analysis=json.loads((HERE/'analysis/confirmatory_summary.json').read_text())
 fits=json.loads((HERE/'analysis/per_fit.json').read_text())
 index={(r['process'],r['world'],r['seed'],r['variant'],r['method']):r for r in fits}
 complete=json.loads((HERE/'main_v1/DONE.json').read_text())
 assert complete['accepted']==288 and complete['failed']==0
 report={'status':'passed','freeze_sha256':sha(source_freeze),'primary_checks':[],'all_fit_checks':[],'precrisis_violations':[]}
 differences={'H1_retention':{},'H2_structure':{}}
 for folder in sorted((HERE/'main_v1').glob('P*_s??')):
  p=json.loads((folder/'PREPARED.json').read_text());identity=(p['process'],p['world'],p['seed'])
  assert p['freeze_sha256']==sha(source_freeze)
  assert p['test_outcomes_generated'] is False
  assert p['base_seed']==1900000000000+int(p['process'][1])*1000000000+['fixed','service','routing','combined'].index(p['world'])*100000000+p['seed']*1000000
  for name,digest in p['files'].items():assert sha(folder/name)==digest
  ca=json.loads((folder/'calibration_audit.json').read_text())
  assert len(ca)==11
  violations=[{'process':p['process'],'world':p['world'],'seed':p['seed'],**{k:r[k] for k in ['stage','episode','maximum_wip','crisis_onset']}} for r in ca if not r['valid_precrisis']]
  report['precrisis_violations'].extend(violations)
  if p['world']=='routing':assert not violations,'Primary pre-crisis criterion failed'
  by={}
  for file in sorted((folder/'test_main').glob('c*.json')):
   item=json.loads(file.read_text());assert item['prepared_sha256']==sha(folder/'PREPARED.json')
   for row in item['rows']:by.setdefault(row['policy'],[]).append(row['cost'])
  assert all(len(x)==48 for x in by.values())
  costs={policy:statistics.mean(values) for policy,values in by.items()}
  normalized={m:costs[c['policy']]/costs['none'] for m,c in p['choices'].items()}
  for method,value in normalized.items():near(value,index[(*identity,'main',method)]['normalized_cost'])
  if p['world']=='routing':
   for name,baseline in [('H1_retention','discovered_predictive'),('H2_structure','legacy_discovered_retained')]:
    differences[name].setdefault(p['process'],[]).append((p['seed'],normalized['discovered_retained']-normalized[baseline]))
  d=json.loads((folder/'discovery.json').read_text())
  known_net=json.loads((folder/'known_net.json').read_text());selected_language=compare_languages(known_net,json.loads((folder/'discovered_net.json').read_text()));legacy_language=compare_languages(known_net,json.loads((folder/'legacy_discovered_net.json').read_text()))
  assert selected_language==d['language']
  report['all_fit_checks'].append({'process':p['process'],'world':p['world'],'seed':p['seed'],'selected_candidate':d['selected_candidate'],'language_equivalent':d['language'].get('equivalent'),'legacy_language':legacy_language,'selected_precision':d['precision'],'standard_im_precision':next(x['precision'] for x in d['candidates'] if x['name']=='standard_im'), 'same_all_planning_scores_as_known':all(p['choices']['known_'+mask]==p['choices']['discovered_'+mask] for mask in ['00','10','01','11']), 'prepared_sha256':sha(folder/'PREPARED.json')})
 for name,groups in differences.items():
  means=[];variances=[]
  for process,pairs in sorted(groups.items()):
   pairs=sorted(pairs);assert [x[0] for x in pairs]==list(range(12))
   values=[x[1] for x in pairs];means.append(statistics.mean(values));variances.append(statistics.variance(values)/12)
  assert len(means)==6
  mean=statistics.mean(means);variance=sum(variances)/36
  df=sum(variances)**2/sum(v*v/11 for v in variances)
  half=t.ppf(.9875,df)*math.sqrt(variance)
  expected=next(x for x in analysis['contrasts'] if x['hypothesis']==name)
  for key,value in [('mean',mean),('low',mean-half),('high',mean+half),('df',df)]:near(value,expected[key])
  assert expected['complete_and_precrisis'] and expected['benefit_established']==(mean+half<0)
  report['primary_checks'].append({'hypothesis':name,'mean':mean,'low':mean-half,'high':mean+half,'df':df,'matches_frozen_analyzer':True})
 assert len(report['all_fit_checks'])==288
 report['executable_language_equivalent']=sum(r['language_equivalent'] is True for r in report['all_fit_checks'])
 report['exact_known_discovered_planning_scores']=sum(r['same_all_planning_scores_as_known'] for r in report['all_fit_checks'])
 report['scope']='All raw candidate-policy mean costs independently recomputed; all preparation checksums and fresh seed assignments verified; both primary intervals recomputed using Python statistics rather than the fit-summary analyzer. No new policy selection.'
 (HERE/'analysis/decision_integrity_audit.json').write_text(json.dumps(report,indent=2))
 print(json.dumps({k:v for k,v in report.items() if k!='all_fit_checks'},indent=2))
if __name__=='__main__':main()
