"""Independent endpoint arithmetic on every saved test path; no simulator imports."""
from pathlib import Path
import json,hashlib,time
import numpy as np
HERE=Path(__file__).resolve().parent

def run():
    root=HERE/'main_v1';assert (root/'DONE.json').exists()
    paths=0;episodes=0;fits=0;maxerror=0.0
    for folder in sorted(root.iterdir()):
        if not folder.is_dir() or not (folder/'DONE.json').exists():continue
        p=json.loads((folder/'PREPARED.json').read_text());spec=p['spec'];dt=spec['sample_interval'];fits+=1
        for name,c in p['choices'].items():
            if 'costs' in c:
                assert c['costs'][c['policy']] == min(c['costs'].values())
        for directory in folder.glob('test_*'):
            for filename in sorted(directory.glob('c*.json')):
                record=json.loads(filename.read_text());z=np.load(filename.with_suffix('.npz'));episodes+=1
                for i,policy in enumerate(p['policies']):
                    s=z[f'p{i}_samples'];c=z[f'p{i}_completed'];row=record['rows'][i];paths+=1
                    assert row['policy']==policy['name']
                    assert np.array_equal(s[:,1],s[:,6]-s[:,2])
                    assert np.array_equal(s[:,1],s[:,4]+s[:,5])
                    assert len(c)==int(s[-1,2]) and len(set(c[:,0]))==len(c)
                    assert np.all(np.diff(s[:,2])>=0) and np.all(s[:,1]>=0)
                    observed=np.flatnonzero(s[:,3]>0);trigger=float(s[observed[0],0]) if len(observed) else -1.0
                    assert trigger==row['trigger']
                    if policy['name']!='none':
                        high=s[:,1]>=policy['threshold'];cross=np.flatnonzero(high[1:]&high[:-1])+1
                        expected=float(s[cross[0],0]) if len(cross) else -1.0
                        assert expected==trigger
                    area=float(np.sum((s[1:,1]+s[:-1,1])*np.diff(s[:,0])/2))
                    charge=policy['cost']*(s[-1,0]-trigger) if trigger>=0 else 0.0
                    for key,value in [('wip_area',area),('action_cost',charge),('cost',area+charge),('residual_wip',s[-1,1])]:
                        error=abs(float(value)-row[key]);maxerror=max(maxerror,error)
                        assert np.isclose(value,row[key],atol=1e-8,rtol=1e-12),(folder,filename,key,value,row[key])
                    over=s[:,1]>=spec['severe_wip'];edges=np.diff(np.r_[False,over,False].astype(int));starts=np.flatnonzero(edges==1);ends=np.flatnonzero(edges==-1)-1
                    long=starts[(ends-starts)*dt>=spec['severe_duration']];onset=float(s[long[0],0]) if len(long) else None
                    assert (onset is not None)==row['crisis'] and onset==row['crisis_onset']
                    if len(c):
                        assert np.isclose(c[:,2].mean(),row['cycle_mean']) and np.isclose(np.quantile(c[:,2],.95),row['cycle_p95'])
                    for j,pr in enumerate(row['process']):
                        a=float(np.sum((s[1:,4+j]+s[:-1,4+j])*np.diff(s[:,0])/2))
                        assert np.isclose(a,pr['wip_area'],atol=1e-8,rtol=1e-12)
                z.close()
        if fits%48==0:print('raw audit fits',fits,'paths',paths,flush=True)
    result=dict(status='passed',fits=fits,episodes=episodes,paths=paths,max_absolute_arithmetic_error=maxerror,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),time=time.time(),scope='Every saved main and robustness test path: WIP conservation, unique completions, observable trigger, costs, severe-event criterion, completed-case durations, per-process WIP; planning argmin verified.')
    (HERE/'analysis/raw_audit.json').write_text(json.dumps(result,indent=2));print(result,flush=True)
if __name__=='__main__':run()
