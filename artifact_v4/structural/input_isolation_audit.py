"""Technical audit: changing unused truth fields cannot change learned preparation.
Uses only the excluded technical pilot. Never selects a policy from main test costs.
"""
from pathlib import Path
import copy,json,hashlib
import numpy as np
from learning import fit,discover,model_for
from native import simulate
HERE=Path(__file__).resolve().parent
PILOT=HERE/'pilot_final' if (HERE/'pilot_final').exists() else HERE.parent/'development/pilot_final'
OUT=HERE/'analysis/input_isolation_diagnostic'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 OUT.mkdir(parents=True,exist_ok=True);checks=[]
 for name in ['P1','P2','P3','P4','P5','P6']:
  source=PILOT/(name+'_routing_s00');prepared=json.loads((source/'PREPARED.json').read_text());spec=prepared['spec'];poison=copy.deepcopy(spec)
  # The campaign carries a full specification object. These fields are available
  # in memory but are not allowed to influence fitted learning or discovery.
  poison['tree']={'op':'unsupported_truth_sentinel','children':[]}
  poison['base_duration']={k:101.+i for i,k in enumerate(spec['base_duration'])}
  poison['service_feedback']={k:203.+i for i,k in enumerate(spec['base_duration'])}
  poison['truth_wip_onset']=301.;poison['truth_wip_saturation']=503.
  poison['log_duration_sigma']=.93;poison['complexity_duration_multiplier']=7.
  for route in poison['routes'].values():
   route['base']=.81;route['complexity']=.29;route['amplitude']=.87
  net=json.loads((source/'known_net.json').read_text())
  fitted=json.loads((source/'fitted.json').read_text())
  with np.load(source/'calibration.npz') as archive:
   train=[{'records':archive[f'train{i}_records']} for i in range(8)]
   validation=[{'records':archive[f'validation{i}_records']} for i in range(3)]
   schedule=archive['validation0_schedule'].copy()
  observations_only={'labels':sorted(spec['roles']),'pools':sorted(spec['capacities']),'transitions':[],'groups':[]}
  refit=fit(train,validation,poison,observations_only)
  assert refit==fitted,(name,'truth fields changed fitted parameters')
  directory=OUT/name;directory.mkdir(exist_ok=True)
  discovered,meta=discover(train,poison,directory)
  assert discovered==json.loads((source/'discovered_net.json').read_text()),(name,'truth fields changed discovery')
  previous=json.loads((source/'discovery.json').read_text())
  assert meta['selected_candidate']==previous['selected_candidate'] and meta['precision']==previous['precision']
  # One policy of each type, with identical observable arrivals and random stream.
  policies=[p for p in prepared['policies'] if p['kind']=='none' or p.get('threshold')==spec['thresholds'][0]]
  for policy in policies:
   args=dict(schedule=schedule,seed=prepared['base_seed']+777777,world='routing',model=model_for(fitted,'11'),policy=policy,horizon=140*spec['cycle_scale'],dt=spec['sample_interval'],verify=True)
   a=simulate(spec,discovered,**args);b=simulate(poison,discovered,**args)
   for field in ['samples','records','completed']:assert np.array_equal(a[field],b[field]),(name,policy['name'],field)
   for field in ['trigger','max_wip','operations']:assert a[field]==b[field],(name,policy['name'],field)
  checks.append({'process':name,'pilot_prepared_sha256':sha(source/'PREPARED.json'),'fitted_parameters_exact':True,'fitting_without_control_flow_exact':True,'selected_executable_structure_exact':True,'fitted_execution_exact':True,'policy_types_checked':len(policies)})
 report={'status':'passed','checks':checks,'scope':'Excluded technical pilot only. Perturbing truth control flow and generative duration/return coefficients, and removing topology from fitting, does not change fitted parameters, selected structure, or fitted execution. Engineering resource maps, candidate return sites, observation mappings and normal-regime scales are held fixed. This audit establishes absence of dependence on the perturbed fields, not absence of all possible information leakage.'}
 (HERE/'analysis/input_isolation_audit.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()
