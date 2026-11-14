"""Resumable structural campaign. Preparation commits before independent test generation."""
import argparse,copy,hashlib,json,os,sys,time,traceback
from pathlib import Path
import numpy as np
from scipy.special import softmax
from native import *
from learning import fit,discover,compare_languages,model_for,language
PRIORITY=['P1','P2','P3','P5','P4','P6']
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_name(path.name+'.tmp');temp.write_text(json.dumps(value,indent=2,allow_nan=False));os.replace(temp,path)
def save_npz(path,values):
    path=Path(path);temp=path.with_name(path.name+'.tmp')
    with temp.open('wb') as f:np.savez_compressed(f,**values)
    os.replace(temp,path)
def policies(spec):
    result=[spec['actions'][0]]
    for a in spec['actions'][1:]:
        for t in spec['thresholds']:result.append(dict(a,name=a['name']+'_q'+str(t),threshold=t))
    return result

def conditions(spec,stage):
    T=spec['cycle_scale'];nom=spec['nominal_fixed_throughput'];safe=spec['safe_rate']
    if stage=='planning':return [(f*safe,p) for p in [None,(20*T,30*T,1.1*nom),(20*T,40*T,1.5*nom)] for f in [.7,.9]]
    return [(f*safe,p) for p in [None,(35*T,50*T,1.35*nom),(35*T,60*T,1.65*nom)] for f in [.75,.95]]

def heuristic(fitted,spec,net):
    labels=net['labels'];coef=np.array(fitted['load']['duration_coef']);rc=np.array(fitted['load']['route_coef']);scores={}
    classweights=[1-spec['complex_fraction'],spec['complex_fraction']]
    contexts=[(c,p,cw*pw) for p,pw in enumerate(spec['process_fractions']) for c,cw in enumerate(classweights)]
    dx=np.array([0,0,0,np.log(3),np.log(5),np.log(5 if len(spec['process_fractions'])==1 else 3)])
    for action in spec['actions'][1:]:
        if action['kind']=='capacity':
            members=[i for i,l in enumerate(labels) if spec['roles'][l]==action['target']]
            score=float(np.mean([max(0.,coef[i]@dx) for i in members])/spec['capacities'][action['target']])
        else:
            values=[]
            for source_label in action['target']:
                source=labels.index(source_label);contextscores=[]
                for c,p,weight in contexts:
                    targets=fitted['repeat_targets'].get(f'{source}_{c}_{p}',[])
                    def prob(x):
                        ps=softmax(rc[source]@x);return float(np.sum(ps[targets]))
                    x=np.array([1,c,p,0,0,0]);low,high=prob(x),prob(x+dx);contextscores.append(weight*max(0,high-low)/max(.05,1-high))
                values.append(sum(contextscores))
            score=float(np.mean(values))
        scores[action['name']]=score
    choice=max(spec['actions'][1:],key=lambda a:scores[a['name']])['name']+'_q'+str(spec['thresholds'][0])
    return dict(policy=choice,scores=scores,threshold=spec['thresholds'][0])

def inputs(name,world,k,pilot=False):
    spec=json.loads((HERE/'calibration'/f'{name}.json').read_text())['spec'];net=compile_net(spec)
    base=(1800000000000 if pilot else 1900000000000)+int(name[1])*1000000000+WORLDS.index(world)*100000000+k*1000000
    return spec,net,base

def verify_freeze():
    f=json.loads((HERE/'FREEZE.json').read_text())
    for name,digest in f['files'].items():
        if sha(HERE/name)!=digest:raise RuntimeError('frozen file changed: '+name)
    return sha(HERE/'FREEZE.json')

def prepare(folder,name,world,k,pilot=False):
    prepared=folder/'PREPARED.json'
    if prepared.exists():
        p=json.loads(prepared.read_text());assert p['freeze_sha256']==('pilot' if pilot else verify_freeze())
        for name,digest in p['files'].items():assert sha(folder/name)==digest
        return p
    folder.mkdir(parents=True,exist_ok=True);spec,net,base=inputs(name,world,k,pilot);T=spec['cycle_scale'];dt=spec['sample_interval'];catalog=policies(spec);audit=[];training=[];validation=[];data={}
    for stage,rates,offset in [('train',[.4,.6,.8,1.]*2,10000),('validation',[.5,.7,.9],30000)]:
        for i,fraction in enumerate(rates):
            schedule=arrivals(spec,base+offset+i*100,fraction*spec['safe_rate'],40*T)
            run=simulate(spec,net,schedule,base+offset+10000+i*100,world,horizon=300*T,dt=dt,verify=True)
            m=metrics(run,spec,catalog[0],dt);valid=len(run['completed'])==len(schedule) and not m['crisis']
            audit.append(dict(stage=stage,episode=i,arrival_seed=base+offset+i*100,operation_seed=base+offset+10000+i*100,valid_precrisis=valid,cases=len(schedule),**m))
            if len(run['completed'])!=len(schedule):raise RuntimeError('incomplete calibration trace; fit failure retained')
            (training if stage=='train' else validation).append(run)
            for key in ['records','samples','completed']:data[f'{stage}{i}_{key}']=run[key]
            data[f'{stage}{i}_schedule']=schedule
    save_npz(folder/'calibration.npz',data);write(folder/'calibration_audit.json',audit)
    fitted=fit(training,validation,spec,net);write(folder/'fitted.json',fitted);write(folder/'known_net.json',net)
    nets={'known':net};dmeta={}
    try:
        dn,dmeta=discover(training,spec,folder);dmeta['language']=compare_languages(net,dn);language(dn);nets['discovered']=dn;write(folder/'discovered_net.json',dn)
    except Exception as exc:dmeta=dict(status='failed',error=repr(exc),traceback=traceback.format_exc())
    if (folder/'legacy_discovered_net.json').exists():nets['legacy_discovered']=json.loads((folder/'legacy_discovered_net.json').read_text())
    write(folder/'discovery.json',dmeta)
    if pilot and dmeta.get('status')!='executable':raise RuntimeError('technical pilot discovery failure: '+repr(dmeta))
    masks={m:model_for(fitted,m) for m in ['00','10','01','11']}
    if len(fitted['route_sources'])>1:
        for source in fitted['route_sources']:masks['11_without_'+net['labels'][source]]=model_for(fitted,'11',[source])
    mask_selected=str(int(fitted['gains']['duration']>.01))+str(int(fitted['gains']['route']>.005))
    choices={};planning=[];trajectories={};val_wip=[]
    for structure,structure_net in nets.items():
        for mi,(mask,model) in enumerate(masks.items()):
            scores={p['name']:[] for p in catalog}
            for ci,(rate,pulse) in enumerate(conditions(spec,'planning')):
                for rep in range(2):
                    schedule=arrivals(spec,base+50000+ci*100+rep,rate,140*T,pulse)
                    for pi,policy in enumerate(catalog):
                        run=simulate(spec,structure_net,schedule,base+60000+ci*100+rep,world,model=model,policy=policy,horizon=140*T,dt=dt,keep=False)
                        metric=metrics(run,spec,policy,dt);scores[policy['name']].append(metric['cost'])
                        planning.append(dict(structure=structure,mask=mask,condition=ci,repeat=rep,policy=policy['name'],**metric))
                        key=f'{structure}_{mask}_{ci}_{rep}_{pi}';trajectories[key]=run['samples']
            means={p:float(np.mean(v)) for p,v in scores.items()};choice=min(catalog,key=lambda p:means[p['name']])['name'];choices[structure+'_'+mask]=dict(policy=choice,costs=means)
        for mask in ['00','11']:
            for vi,val in enumerate(validation):
                schedule=data[f'validation{vi}_schedule'];run=simulate(spec,structure_net,schedule,base+40000+vi*100,world,model=masks[mask],horizon=300*T,dt=dt,keep=False)
                # First 40T only, before the deliberately long drain tail.
                use=val['samples'][:,0]<=40*T;diff=run['samples'][use,1]-val['samples'][use,1]
                val_wip.append(dict(structure=structure,mask=mask,episode=vi,rmse=float(np.sqrt(np.mean(diff**2))),nrmse=float(np.sqrt(np.mean(diff**2))/max(1,np.mean(val['samples'][use,1])))))
    oracle_scores={p['name']:[] for p in catalog}
    for ci,(rate,pulse) in enumerate(conditions(spec,'planning')):
        for rep in range(2):
            schedule=arrivals(spec,base+50000+ci*100+rep,rate,140*T,pulse)
            trajectories[f'schedule_{ci}_{rep}']=schedule
            for pi,policy in enumerate(catalog):
                run=simulate(spec,net,schedule,base+60000+ci*100+rep,world,policy=policy,horizon=140*T,dt=dt,keep=False);metric=metrics(run,spec,policy,dt);oracle_scores[policy['name']].append(metric['cost'])
                planning.append(dict(structure='generator',mask='truth',condition=ci,repeat=rep,policy=policy['name'],**metric));trajectories[f'generator_{ci}_{rep}_{pi}']=run['samples']
    oracle_means={p:float(np.mean(v)) for p,v in oracle_scores.items()};oracle=min(catalog,key=lambda p:oracle_means[p['name']])['name']
    choices['oracle']=dict(policy=oracle,costs=oracle_means);choices['heuristic']=heuristic(fitted,spec,net)
    for structure in nets:
        for method,mask in [('static','00'),('retained','11'),('predictive',mask_selected)]:choices[structure+'_'+method]=dict(choices[structure+'_'+mask],mask=mask)
    write(folder/'planning.json',planning);save_npz(folder/'planning_trajectories.npz',trajectories);write(folder/'validation_wip.json',val_wip)
    files={p.name:sha(p) for p in sorted(folder.iterdir()) if p.is_file() and not p.name.endswith('.tmp')}
    p=dict(process=name,world=world,seed=k,classification='technical_pilot' if pilot else 'prospective_structural_extension',freeze_sha256='pilot' if pilot else verify_freeze(),spec=spec,base_seed=base,policies=catalog,choices=choices,discovery_status=dmeta.get('status'),selected_mask=mask_selected,all_precrisis=all(x['valid_precrisis'] for x in audit),test_outcomes_generated=False,prepared_at=time.time(),files=files)
    write(prepared,p);return p

def test(folder,prepared,variant='main',pilot=False):
    spec=prepared['spec'];net=compile_net(spec);base=prepared['base_seed'];T=spec['cycle_scale'];dt=spec['sample_interval'];catalog=prepared['policies'];target=folder/('test_'+variant);target.mkdir(exist_ok=True)
    mix=.65 if variant=='mix65' else None;effect={'efficacy30':.7,'efficacy70':.3}.get(variant,.5)
    rows=[]
    for ci,(rate,pulse) in enumerate(conditions(spec,'test')):
        for rep in range(2 if pilot else 8):
            path=target/f'c{ci}_r{rep}.json';archive=path.with_suffix('.npz')
            if path.exists():
                item=json.loads(path.read_text());assert item['prepared_sha256']==sha(folder/'PREPARED.json') and item['trajectory_sha256']==sha(archive);rows.extend(item['rows']);continue
            schedule=arrivals(spec,base+500000+ci*100+rep,rate,180*T,pulse,mix);trajectories={'schedule':schedule};current=[]
            for pi,policy in enumerate(catalog):
                run=simulate(spec,net,schedule,base+600000+ci*100+rep,prepared['world'],policy=policy,horizon=180*T,dt=dt,keep=False,effect=effect,verify=True)
                metric=metrics(run,spec,policy,dt);current.append(dict(condition=ci,repeat=rep,variant=variant,policy=policy['name'],**metric));trajectories[f'p{pi}_samples']=run['samples'];trajectories[f'p{pi}_completed']=run['completed']
            control=current[0]
            for row in current:
                row.update(prevented=control['crisis'] and not row['crisis'],at_risk=control['crisis'],lead=control['crisis_onset']-row['trigger'] if control['crisis'] and row['trigger']>=0 else None,nonsevere_activation=not control['crisis'] and row['trigger']>=0,calm_activation=ci<2 and row['trigger']>=0)
            save_npz(archive,trajectories);write(path,dict(prepared_sha256=sha(folder/'PREPARED.json'),trajectory_sha256=sha(archive),arrival_seed=base+500000+ci*100+rep,operation_seed=base+600000+ci*100+rep,rows=current));rows.extend(current)
    write(target/'DONE.json',dict(rows=len(rows),episodes=len(rows)//len(catalog),files={p.name:sha(p) for p in sorted(target.glob('c*'))}));return rows

def run_task(root,name,world,k,pilot=False):
    folder=root/f'{name}_{world}_s{k:02d}';started=time.time()
    if (folder/'DONE.json').exists():
        done=json.loads((folder/'DONE.json').read_text())
        for file,digest in done['files'].items():assert sha(folder/file)==digest
        return
    prepared=prepare(folder,name,world,k,pilot);test(folder,prepared,pilot=pilot)
    variants=['main']
    if name=='P2':test(folder,prepared,'mix65',pilot);variants.append('mix65')
    if name=='P3':
        for v in ['efficacy30','efficacy70']:test(folder,prepared,v,pilot);variants.append(v)
    files={'PREPARED.json':sha(folder/'PREPARED.json'),**{'test_'+v+'/DONE.json':sha(folder/('test_'+v)/'DONE.json') for v in variants}}
    write(folder/'DONE.json',dict(status='complete',process=name,world=world,seed=k,variants=variants,seconds=time.time()-started,files=files,discovery_status=prepared['discovery_status'],all_precrisis=prepared['all_precrisis']))
    print(folder.name,'complete',round(time.time()-started,2),'precrisis',prepared['all_precrisis'],'discovery',prepared['discovery_status'],flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['pilot','main']);p.add_argument('--limit-processes',type=int,default=6);args=p.parse_args()
    pilot=args.mode=='pilot';root=HERE/('pilot_final' if pilot else 'main_v1');root.mkdir(exist_ok=True)
    if not pilot:verify_freeze()
    tasks=[(name,w,k) for w in (['routing'] if pilot else ['routing','combined','fixed','service']) for name in PRIORITY[:args.limit_processes] for k in range(1 if pilot else 12)]
    for name,w,k in tasks:
        failure=root/f'{name}_{w}_s{k:02d}'/'FAILED.json'
        if failure.exists():continue
        try:run_task(root,name,w,k,pilot)
        except Exception as e:
            write(failure,dict(process=name,world=w,seed=k,status='failed',error=repr(e),traceback=traceback.format_exc(),time=time.time()))
            print(name,w,k,'FAILED',repr(e),flush=True)
            if pilot:raise
    accepted=sum((root/f'{n}_{w}_s{k:02d}'/'DONE.json').exists() for n,w,k in tasks);failed=sum((root/f'{n}_{w}_s{k:02d}'/'FAILED.json').exists() for n,w,k in tasks)
    write(root/'DONE.json',dict(accepted=accepted,failed=failed,expected=len(tasks),classification='technical_pilot' if pilot else 'prospective_extension'))
if __name__=='__main__':main()
