"""Recovery after the pulse on saved test paths, without refitting or reselection."""
from pathlib import Path
import json
import numpy as np
from campaign import write
HERE=Path(__file__).resolve().parent;ROOT=HERE/'main_v1';OUT=HERE/'analysis'
def run():
    assert (ROOT/'DONE.json').exists();rows=[]
    for folder in sorted(ROOT.iterdir()):
        if not folder.is_dir() or not (folder/'DONE.json').exists():continue
        p=json.loads((folder/'PREPARED.json').read_text());spec=p['spec'];T=spec['cycle_scale'];dt=spec['sample_interval'];S=spec['normal_scale']
        selected={'none',p['choices']['oracle']['policy'],p['choices']['heuristic']['policy']}
        for key in ['known_retained','known_predictive','discovered_retained','discovered_predictive']:
            if key in p['choices']:selected.add(p['choices'][key]['policy'])
        for ci in range(2,6):
            pulse_end=(50 if ci<4 else 60)*T
            for rep in range(8):
                z=np.load(folder/'test_main'/f'c{ci}_r{rep}.npz')
                for pi,policy in enumerate(p['policies']):
                    if policy['name'] not in selected:continue
                    s=z[f'p{pi}_samples'];tail=s[s[:,0]>=pulse_end];streak=0;recovered=None
                    for r in tail:
                        streak=streak+1 if r[1]<=2*S else 0
                        if recovered is None and (streak-1)*dt>=10*T:recovered=float(r[0]-(streak-1)*dt-pulse_end)
                    rows.append(dict(process=p['process'],world=p['world'],seed=p['seed'],condition=ci,repeat=rep,policy=policy['name'],pulse_end=pulse_end,recovery_delay=recovered,recovered_by_horizon=recovered is not None,tail_wip_area=float(np.trapezoid(tail[:,1],tail[:,0])),above_severe_after_pulse=float(np.sum(tail[:-1,1]>=10*S)*dt),criterion='WIP<=2S for10T after pulse; censored at180T',classification='post-freeze descriptive diagnostic'))
    write(OUT/'recovery_per_trajectory.json',rows);print('saved recovery diagnostic',len(rows),flush=True)
if __name__=='__main__':run()
