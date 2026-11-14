"""Read-only inference from sealed main-campaign outputs. Never selects a policy."""
from pathlib import Path
from collections import defaultdict,Counter
import json,math,time,hashlib
import numpy as np
from scipy.stats import t
HERE=Path(__file__).resolve().parent;ROOT=HERE/'main_v1';OUT=HERE/'analysis';OUT.mkdir(exist_ok=True)
METRICS=['cost','normalized_cost','regret','normalized_regret','crisis','prevented_fraction','activation','calm_activation','nonsevere_activation','wip_area','action_cost','residual_wip','cycle_mean','cycle_p95','action_agreement','policy_agreement','ranking_error','lead']
def write(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ci(x,alpha=.05):
    x=np.array([v for v in x if v is not None],float);n=len(x)
    if n==0:return dict(mean=None,low=None,high=None,n=0)
    mean=float(np.mean(x));half=float(t.ppf(1-alpha/2,n-1)*np.std(x,ddof=1)/math.sqrt(n)) if n>1 else 0
    return dict(mean=mean,low=mean-half,high=mean+half,n=n)
def average(x):return float(np.mean(x)) if len(x) else None
def rank_error(costs,truecosts):
    keys=list(costs);errors=[]
    for i,a in enumerate(keys):
        for b in keys[i+1:]:
            delta=truecosts[a]-truecosts[b]
            if abs(delta)>1e-9:errors.append((costs[a]-costs[b])*delta<0)
    return average(errors)
def main():
    done=json.loads((ROOT/'DONE.json').read_text());assert done['expected']==288 and done['accepted']+done['failed']==288
    rows=[];sensitivity=[];discovery=[];audit=[];failures=[];method_coverage=Counter();checks=[];model_quality=[]
    for folder in sorted(ROOT.iterdir()):
        if not folder.is_dir():continue
        if (folder/'FAILED.json').exists():failures.append(json.loads((folder/'FAILED.json').read_text()));continue
        d=json.loads((folder/'DONE.json').read_text());prepared=json.loads((folder/'PREPARED.json').read_text());fitted=json.loads((folder/'fitted.json').read_text())
        for name,digest in d['files'].items():assert sha(folder/name)==digest
        for name,digest in prepared['files'].items():assert sha(folder/name)==digest
        identity={key:prepared[key] for key in ['process','world','seed']};disc=json.loads((folder/'discovery.json').read_text());discovery.append({**identity,**disc});episode_audit=json.loads((folder/'calibration_audit.json').read_text());audit.extend([{**identity,**{k:v for k,v in x.items() if k!='process'},'process_metrics':x['process']} for x in episode_audit])
        model_quality.append(dict(**identity,validation=fitted['validation'],gains=fitted['gains'],observed_range=fitted['observed_range'],wip_predictions=json.loads((folder/'validation_wip.json').read_text())))
        methodpolicies={'no_action':'none',**{k:v['policy'] for k,v in prepared['choices'].items()}}
        methodpolicies.update({'fixed_'+p['name']:p['name'] for p in prepared['policies'][1:]})
        for variant in d['variants']:
            tr=folder/('test_'+variant);td=json.loads((tr/'DONE.json').read_text());assert td['episodes']==48
            for name,digest in td['files'].items():assert sha(tr/name)==digest
            tests=[r for file in sorted(tr.glob('c*.json')) for r in json.loads(file.read_text())['rows']];by=defaultdict(list)
            for r in tests:by[r['policy']].append(r)
            for policy,rr in by.items():assert len(rr)==48
            costs={p:average([r['cost'] for r in rr]) for p,rr in by.items()};none=costs['none'];oracle=prepared['choices']['oracle']['policy'];truecosts=prepared['choices']['oracle']['costs']
            for method,policy in methodpolicies.items():
                rr=by[policy];risk=sum(r['at_risk'] for r in rr);nonsevere=sum(not r['at_risk'] for r in rr);lead=[r['lead'] for r in rr if r['lead'] is not None]
                row=dict(**identity,variant=variant,method=method,policy=policy,threshold=next(p.get('threshold') for p in prepared['policies'] if p['name']==policy),calibration_max_wip=max(x['maximum_wip'] for x in episode_audit if x['stage']=='train'),validation_max_wip=max(x['maximum_wip'] for x in episode_audit if x['stage']=='validation'),calibration_feature_max_wip=max(fitted['observed_range']['max_wip'],fitted['observed_range']['max_route_wip']),all_precrisis=prepared['all_precrisis'],cost=costs[policy],normalized_cost=costs[policy]/none,regret=costs[policy]-costs[oracle],normalized_regret=(costs[policy]-costs[oracle])/none,action_agreement=int(policy.split('_q')[0]==oracle.split('_q')[0]),policy_agreement=int(policy==oracle),ranking_error=rank_error(prepared['choices'][method]['costs'],truecosts) if method in prepared['choices'] and 'costs' in prepared['choices'][method] else None,crisis=average([r['crisis'] for r in rr]),prevented_fraction=sum(r['prevented'] for r in rr)/risk if risk else None,at_risk=risk,prevented=sum(r['prevented'] for r in rr),activation=average([r['trigger']>=0 for r in rr]),calm_activation=sum(r['calm_activation'] for r in rr)/16,nonsevere_activation=sum(r['nonsevere_activation'] for r in rr)/nonsevere if nonsevere else None,lead=average(lead),early_count=sum(v>0 for v in lead),activated_risk=len(lead),**{metric:average([r[metric] for r in rr if r[metric] is not None]) for metric in ['wip_area','action_cost','residual_wip','cycle_mean','cycle_p95']})
                row['threshold_relative_scale']=row['threshold']/prepared['spec']['normal_scale'] if row['threshold'] else None
                row['threshold_relative_observed_max']=row['threshold']/row['calibration_max_wip'] if row['threshold'] and row['calibration_max_wip'] else None
                row['process_metrics']=[dict(wip_area=average([r['process'][p]['wip_area'] for r in rr]),cycle_mean=average([r['process'][p]['cycle_mean'] for r in rr if r['process'][p]['cycle_mean'] is not None])) for p in range(len(rr[0]['process']))]
                rows.append(row)
            if variant=='main':
                settings=[('return',.01,v) for v in [0,.001,.0025,.005,.01]]+[('duration',v,.005) for v in [0,.0025,.005,.01,.02]]
                for structure in ['known','discovered']:
                    if structure+'_11' not in prepared['choices']:continue
                    for axis,dd,dr in settings:
                        mask=str(int(fitted['gains']['duration']>dd))+str(int(fitted['gains']['route']>dr));policy=prepared['choices'][structure+'_'+mask]['policy'];rr=by[policy]
                        sensitivity.append(dict(**identity,structure=structure,axis=axis,delta_duration=dd,delta_return=dr,mask=mask,policy=policy,duration_retained=int(mask[0]),return_retained=int(mask[1]),cost=costs[policy],normalized_cost=costs[policy]/none,regret=costs[policy]-costs[oracle],crisis=average([r['crisis'] for r in rr]),action_agreement=int(policy.split('_q')[0]==oracle.split('_q')[0])))
        checks.append(dict(task=folder.name,done_sha256=sha(folder/'DONE.json'),prepared_sha256=sha(folder/'PREPARED.json')))
        if len(checks)%48==0:print('verified and summarized fits',len(checks),flush=True)
    groups=defaultdict(list)
    for r in rows:groups[(r['process'],r['world'],r['variant'],r['method'])].append(r)
    summary=[]
    for (process,world,variant,method),rr in groups.items():summary.append(dict(process=process,world=world,variant=variant,method=method,n=len(rr),**{m:ci([r[m] for r in rr]) for m in METRICS},policies=dict(Counter(r['policy'] for r in rr))))
    contrasts=[]
    for process,world,variant in sorted({(r['process'],r['world'],r['variant']) for r in rows}):
        for structure in ['known','discovered']:
            methods=['predictive','static','heuristic','oracle']
            for baseline in methods:
                m=structure+'_retained';b=structure+'_'+baseline if baseline in ['predictive','static'] else baseline
                aa={r['seed']:r for r in groups.get((process,world,variant,m),[])};bb={r['seed']:r for r in groups.get((process,world,variant,b),[])};seeds=sorted(set(aa)&set(bb))
                if not seeds:continue
                diff=[aa[k]['cost']-bb[k]['cost'] for k in seeds];norm=[aa[k]['normalized_cost']-bb[k]['normalized_cost'] for k in seeds]
                primary=world=='routing' and structure=='known' and baseline=='predictive' and variant=='main'
                contrasts.append(dict(process=process,world=world,variant=variant,structure=structure,baseline=baseline,primary=primary,difference=ci(diff),normalized_difference=ci(norm),family_adjusted_difference=ci(diff,.05/6) if primary else None,relative_mean_reduction=1-average([aa[k]['cost'] for k in seeds])/average([bb[k]['cost'] for k in seeds])))
    # Equal-weight aggregation over the complete six designed classes, independent fit uncertainty.
    aggregates=[]
    for world in ['fixed','service','routing','combined']:
        for structure in ['known','discovered']:
            selected=[c for c in contrasts if c['world']==world and c['structure']==structure and c['baseline']=='predictive' and c['variant']=='main']
            estimates=[];variances=[];dfs=[]
            for c in selected:
                rr=groups[(c['process'],world,'main',structure+'_retained')];bb={r['seed']:r for r in groups[(c['process'],world,'main',structure+'_predictive')]};d=np.array([r['normalized_cost']-bb[r['seed']]['normalized_cost'] for r in rr]);estimates.append(float(d.mean()));variances.append(float(d.var(ddof=1)/len(d)));dfs.append(len(d)-1)
            if estimates:
                K=len(estimates);mean=sum(estimates)/K;var=sum(variances)/K**2;den=sum(v*v/df for v,df in zip(variances,dfs));df=sum(variances)**2/den if den else 1e9;half=float(t.ppf(.975,df)*math.sqrt(var))
                aggregates.append(dict(world=world,structure=structure,processes=K,complete_six=K==6,mean=mean,low=mean-half,high=mean+half,df=df,weighting='equal designed-process weights, independent-fit variance'))
    write(OUT/'model_quality.json',model_quality);write(OUT/'per_fit.json',rows);write(OUT/'summary.json',summary);write(OUT/'contrasts.json',contrasts);write(OUT/'aggregate.json',aggregates);write(OUT/'selector_per_fit.json',sensitivity);write(OUT/'discovery.json',discovery);write(OUT/'calibration_audits.json',audit);write(OUT/'failures.json',failures)
    write(OUT/'DONE.json',dict(time=time.time(),accepted=len(checks),failed=len(failures),main_campaign=done,precrisis_episodes=len(audit),precrisis_violations=sum(not x['valid_precrisis'] for x in audit),all_source_checksums_verified=True,checks=checks,script_sha256=sha(Path(__file__)),output_files={p.name:sha(p) for p in OUT.glob('*.json') if p.name!='DONE.json'}))
    for c in contrasts:
        if c['primary']:print(c['process'],'reduction',round(100*c['relative_mean_reduction'],2),'CI',c['family_adjusted_difference'],flush=True)
    print('accepted',len(checks),'failed',len(failures),'audit violations',sum(not x['valid_precrisis'] for x in audit),flush=True)
if __name__=='__main__':main()
