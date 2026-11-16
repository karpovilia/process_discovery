"""Extract manuscript quantities from the completed, audited campaign; no model selection."""
from pathlib import Path
import json,hashlib,statistics
HERE=Path(__file__).resolve().parent;A=HERE/'analysis'
def main():
 names=['summary.json','contrasts.json','aggregate.json','confirmatory_summary.json','selector_summary.json','discovery_summary.json','resource_summary.json','trigger_support.json','decision_integrity_audit.json','raw_audit.json']
 data={n:json.loads((A/n).read_text()) for n in names}
 assert data['raw_audit.json']['status']=='passed' and data['decision_integrity_audit.json']['status']=='passed'
 summary=data['summary.json'];get=lambda p,w,m,v='main':next(r for r in summary if (r['process'],r['world'],r['method'],r['variant'])==(p,w,m,v))
 out={'source_sha256':{n:hashlib.sha256((A/n).read_bytes()).hexdigest() for n in names},'precrisis_violations':data['decision_integrity_audit.json']['precrisis_violations'],'primary':[{k:v for k,v in r.items() if k!='cells'} for r in data['confirmatory_summary.json']['contrasts']],'routing':[],'cross_process_means':[]}
 methods=['discovered_static','discovered_predictive','discovered_retained','legacy_discovered_retained','heuristic','oracle']
 for p in ['P1','P2','P3','P4','P5','P6']:
  out['routing'].append({'process':p,'methods':{m:{k:get(p,'routing',m)[k] for k in ['normalized_cost','normalized_regret','crisis','policies','action_agreement']} for m in methods},'retained_vs_predictive':next(r for r in data['contrasts.json'] if (r['process'],r['world'],r['structure'],r['baseline'],r['variant'])==(p,'routing','discovered','predictive','main'))})
 for w in ['fixed','service','routing','combined']:
  out['cross_process_means'].append({'world':w,'methods':{m:statistics.mean(get(p,w,m)['normalized_cost']['mean'] for p in ['P1','P2','P3','P4','P5','P6']) for m in methods}})
 out['aggregates']=data['aggregate.json'];out['discovery']=data['discovery_summary.json']
 out['exact_planning_equivalence']=data['decision_integrity_audit.json']['exact_known_discovered_planning_scores']
 out['selected_language_equivalence']=data['decision_integrity_audit.json']['executable_language_equivalent']
 out['standard_im_equivalence']=sum(r['legacy_language'].get('equivalent') is True for r in data['decision_integrity_audit.json']['all_fit_checks'])
 out['strong_comparisons']=[r for r in data['contrasts.json'] if r['process'] in ['P3','P5','P6'] and r['structure']=='discovered' and r['baseline']=='heuristic' and r['variant']=='main']
 out['p6_service']={m:get('P6','service',m) for m in methods}
 out['p4_routing_ablations']={mask:get('P4','routing','discovered_'+mask) for mask in ['00','10','01','11']}
 out['p5_combined_queues']=[r for r in data['resource_summary.json'] if r['process']=='P5' and r['world']=='combined']
 out['routing_selector']=[r for r in data['selector_summary.json'] if r['world']=='routing' and r['structure']=='discovered']
 out['robustness']=[r for r in summary if r['variant']!='main' and r['world']=='routing' and r['method'] in methods]
 out['routing_triggers']=[r for r in data['trigger_support.json'] if r['world']=='routing' and r['structure']=='discovered']
 (A/'paper_claims.json').write_text(json.dumps(out,indent=2))
 print(json.dumps({k:out[k] for k in ['primary','cross_process_means','exact_planning_equivalence','selected_language_equivalence','standard_im_equivalence']},indent=2))
if __name__=='__main__':main()
