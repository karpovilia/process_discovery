"""Frozen-policy replay for bottleneck queues and complete arrival cohorts; diagnostic only."""
from pathlib import Path
import json
import numpy as np
from native import *
from campaign import write,save_npz,sha
OUT=HERE/'analysis/resource_diagnostic'
def run():
    assert (HERE/'main_v1/DONE.json').exists();OUT.mkdir(parents=True,exist_ok=True);rows=[]
    write(OUT/'DESIGN.json',dict(classification='post-main diagnostic',processes=['P4','P5'],worlds=['fixed','service','routing','combined'],seeds=list(range(12)),conditions=[3,5],repeat=0,policies='Every action type at smallest frozen threshold, plus saved comparator choices and no action',original_horizon='180T',drain_horizon='600T',post_horizon_action_continues=True,selection_uses_test_outcomes=False,source_sha256=sha(Path(__file__))))
    for process in ['P4','P5']:
        for world in ['fixed','service','routing','combined']:
            for seed in range(12):
                task=HERE/'main_v1'/f'{process}_{world}_s{seed:02d}'
                if not (task/'DONE.json').exists():continue
                p=json.loads((task/'PREPARED.json').read_text());spec=p['spec'];net=compile_net(spec);T=spec['cycle_scale'];H=180*T;dt=spec['sample_interval'];policies=p['policies'];names={'none',p['choices']['heuristic']['policy'],p['choices']['oracle']['policy']}
                for key in ['known_retained','known_predictive','known_static','discovered_retained']:
                    if key in p['choices']:names.add(p['choices'][key]['policy'])
                names.update(policy['name'] for policy in policies if policy.get('threshold')==spec['thresholds'][0])
                for ci in [3,5]:
                    rep=0;source=task/'test_main'/f'c{ci}_r{rep}.npz';data=np.load(source);schedule=data['schedule']
                    output=OUT/f'{process}_{world}_s{seed:02d}_c{ci}.json';archive=output.with_suffix('.npz')
                    if output.exists():
                        old=json.loads(output.read_text());assert old['source_sha256']==sha(source) and old['archive_sha256']==sha(archive);rows.extend(old['rows']);continue
                    current=[];traj={}
                    for pi,policy in enumerate(policies):
                        if policy['name'] not in names:continue
                        r=simulate(spec,net,schedule,p['base_seed']+600000+ci*100+rep,world,policy=policy,horizon=600*T,dt=dt,keep=True,verify=True)
                        original=data[f'p{pi}_samples'];assert np.array_equal(r['samples'][:len(original)],original), 'replay prefix changed'
                        if len(r['completed'])!=len(schedule):raise RuntimeError('diagnostic drain incomplete')
                        rec=r['records'];poolstats=[]
                        for pool in range(len(net['pools'])):
                            rr=rec[(rec[:,11]//1000==pool)&(rec[:,4]<H)];waiting=np.maximum(0,np.minimum(rr[:,5],H)-rr[:,4]);busy=np.maximum(0,np.minimum(rr[:,6],H)-np.minimum(rr[:,5],H))
                            poolstats.append(dict(pool=net['pools'][pool],queue_area=float(waiting.sum()),busy_area=float(busy.sum()),mean_queue=float(waiting.sum()/H),capacity=spec['capacities'][net['pools'][pool]]))
                        completed=r['completed'];byprocess=[]
                        for process_id in range(len(spec['process_fractions'])):
                            vals=completed[completed[:,3]==process_id,2]
                            byprocess.append(dict(process_id=process_id,n=len(vals),cycle_mean=float(np.mean(vals)),cycle_p50=float(np.quantile(vals,.5)),cycle_p95=float(np.quantile(vals,.95)),cycle_max=float(np.max(vals))))
                        current.append(dict(process=process,world=world,seed=seed,condition=ci,repeat=rep,policy=policy['name'],queue_bottleneck=max(poolstats,key=lambda x:x['queue_area'])['pool'],pools=poolstats,complete_cohort=byprocess,prefix_exact=True,classification='post-freeze diagnostic, no policy reselection',post_horizon_action_continues=True,complete_cohort_scope='600T drain with action maintained; queue areas and replay equivalence concern original180T only'))
                        traj[f'p{pi}_records']=rec;traj[f'p{pi}_completed']=completed
                    save_npz(archive,traj);write(output,dict(source_sha256=sha(source),archive_sha256=sha(archive),rows=current));rows.extend(current)
    write(OUT/'summary.json',rows);write(OUT/'DONE.json',dict(rows=len(rows),all_prefixes_exact=True,files={x.name:sha(x) for x in OUT.glob('*') if x.name!='DONE.json'}));print('resource diagnostic',len(rows),'fixed-policy replays',flush=True)
if __name__=='__main__':run()
