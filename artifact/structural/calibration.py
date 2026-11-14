from pathlib import Path
import hashlib,json,math,time
import numpy as np
from specifications import get
from native import *
OUT=HERE/'calibration';OUT.mkdir(exist_ok=True)
def write(path,value):path.write_text(json.dumps(value,indent=2))
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
if not (OUT/'started.json').exists():write(OUT/'started.json',dict(time=time.time(),protocol_sha256=digest(HERE/'CALIBRATION_PROTOCOL.md'),specifications_sha256=digest(HERE/'specifications.py'),generator_sha256=digest(HERE/'engine.cpp')))
for name in ['P1','P2','P3','P5','P4','P6']:
    if (OUT/(name+'.json')).exists():continue
    spec=get(name);net=compile_net(spec);pid=int(name[1]);nominal=spec['nominal_fixed_throughput'];rr=[];cycles=[];reference=[];archive={}
    for k in range(4):
        seed=70000000000+pid*1000000+k*100;arr=arrivals(spec,seed,.3*nominal,2000);r=simulate(spec,net,arr,seed+1,'fixed',horizon=6000,keep=False)
        assert len(r['completed'])==len(arr);rr.extend(r['samples'][(r['samples'][:,0]>=200)&(r['samples'][:,0]<2000),1]);cycles.extend(r['completed'][:,2]);reference.append(dict(seed=seed,cases=len(arr),max_wip=r['max_wip']));archive[f'ref{k}_samples']=r['samples'];archive[f'ref{k}_schedule']=arr
    S=max(2,int(math.ceil(np.quantile(rr,.95))));T=max(2,int(math.ceil(np.mean(cycles))));spec.update(normal_scale=S,cycle_scale=T,severe_wip=10*S,severe_duration=20*T,sample_interval=.5*T)
    grid=[];safe=None;contiguous=True
    for gi,fraction in enumerate([.25,.35,.45,.55,.65,.75,.85]):
        results=[]
        for k in range(4):
            seed=71000000000+pid*1000000+gi*1000+k*10;arr=arrivals(spec,seed,fraction*nominal,100*T);r=simulate(spec,net,arr,seed+1,'combined',horizon=400*T,dt=.5*T,keep=False)
            m=metrics(r,spec,spec['actions'][0],.5*T);sm=r['samples'];drift=float(np.mean(sm[(sm[:,0]>=75*T)&(sm[:,0]<100*T),1])-np.mean(sm[(sm[:,0]>=50*T)&(sm[:,0]<75*T),1]));ok=len(r['completed'])==len(arr) and not m['crisis'] and drift<=S
            results.append(dict(seed=seed,fraction=fraction,qualified=ok,drift=drift,cases=len(arr),**m));archive[f'grid{gi}_{k}_samples']=sm;archive[f'grid{gi}_{k}_schedule']=arr
        passed=all(x['qualified'] for x in results);grid.append(dict(fraction=fraction,qualified=passed,episodes=results))
        if contiguous and passed:safe=fraction*nominal
        else:contiguous=False
    if safe is None:write(OUT/(name+'_FAILED.json'),dict(reference=reference,grid=grid));raise RuntimeError('bottom stability grid failed '+name)
    spec.update(safe_rate=safe,thresholds=[2*S,4*S,8*S],status='truth_calibrated_before_main_protocol_freeze')
    stress=[]
    for wi,world in enumerate(WORLDS):
        for ci,(fraction,pulse) in enumerate([(f,p) for p in [None,(35*T,50*T,1.35*nominal),(35*T,60*T,1.65*nominal)] for f in [.75,.95]]):
            for k in range(4):
                seed=72000000000+pid*1000000+wi*10000+ci*100+k*10;arr=arrivals(spec,seed,fraction*safe,180*T,pulse);r=simulate(spec,net,arr,seed+1,world,horizon=180*T,dt=.5*T,keep=False);m=metrics(r,spec,spec['actions'][0],.5*T)
                drain=simulate(spec,net,arr,seed+1,world,horizon=600*T,dt=.5*T,keep=False)
                stress.append(dict(world=world,condition=ci,repeat=k,seed=seed,drained=len(drain['completed'])==len(arr),**m));archive[f'stress{wi}_{ci}_{k}_samples']=r['samples'];archive[f'stress{wi}_{ci}_{k}_schedule']=arr
    np.savez_compressed(OUT/(name+'_trajectories.npz'),**archive)
    write(OUT/(name+'.json'),dict(spec=spec,reference=reference,grid=grid,stress=stress,protocol_sha256=digest(HERE/'CALIBRATION_PROTOCOL.md')))
    print(name,'S',S,'T',T,'safe/nominal',round(safe/nominal,2),'severe',[sum(r['crisis'] for r in stress if r['world']==w) for w in WORLDS],'drained',sum(r['drained'] for r in stress),flush=True)
write(OUT/'DONE.json',dict(processes=6,files={p.name:digest(p) for p in sorted(OUT.glob('P*'))}))
