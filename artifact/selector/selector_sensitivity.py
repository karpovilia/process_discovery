"""Threshold sensitivity on frozen P0 fits; no new test trajectories."""
from pathlib import Path
import argparse,collections,hashlib,importlib.util,json,math,sys,time
import numpy as np
from scipy.stats import t
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
INPUT=ROOT/'legacy/caise2027_artifact/e7/main_v1/mirror/tasks'
REV=ROOT/'legacy/caise2027_artifact/revision'
sys.path.insert(0,str(REV))
sp=importlib.util.spec_from_file_location('selector_e7_cached',REV/'efficacy_engine.py');s=importlib.util.module_from_spec(sp);sp.loader.exec_module(s)
import counter_cache
OUT=HERE/'selector_results'
SETTINGS=([{'axis':'return','duration':.01,'return':v} for v in [0,.001,.0025,.005,.01]]+
          [{'axis':'duration','duration':v,'return':.005} for v in [0,.0025,.005,.01,.02]])
PLANNING=[(.4,None),(.5,None),(.4,(200,300,1.1)),(.5,(200,300,1.1)),(.4,(200,400,1.5)),(.5,(200,400,1.5))]
def read(folder,name):
    p=folder/name;expected=json.loads((folder/'DONE.json').read_text())['files'][name]
    assert s.sha(p)==expected
    return json.loads(p.read_text())
def mask(p):return str(int(p['duration_load']))+str(int(p['route_load']))
def parameters(f,m):
    p=dict(f['load'] if m[0]=='1' else f['static'])
    p.update({k:(f['load'] if m[1]=='1' else f['static'])[k] for k in ['route_coef','route_load']})
    return p
def inventory():
    rows=[]
    for w in s.WORLDS:
        for k in range(12):
            folder=INPUT/f'{w}_s{k:02d}';f=read(folder,'fitted.json')
            available={mask(f[n]):n for n in ['static','load','selected']}
            missing=sorted(set(['00','10','01','11'])-set(available))
            rows.append({'world':w,'seed':k,'available':available,'missing':missing,'new_rollouts':84*len(missing)})
    s.write(OUT/'inventory.json',{'fits':len(rows),'rows':rows,'new_rollouts':sum(x['new_rollouts'] for x in rows),'test_rollouts':0})
    print('fits',len(rows),'missing planning rollouts',sum(x['new_rollouts'] for x in rows),flush=True)
    return rows
def prepare():
    for item in inventory():
        w,k=item['world'],item['seed'];name=f'{w}_s{k:02d}';folder=INPUT/name;out=OUT/name/'prepared.json'
        if out.exists():
            saved=json.loads(out.read_text())
            assert saved['protocol_sha256']==s.sha(HERE/'SELECTOR_PROTOCOL.md')
            assert saved['engine_sha256']==s.sha(REV/'efficacy_engine.py')
            assert len(saved['planning_rows'])==336 and set(saved['masks'])=={'00','10','01','11'}
            receipt=json.loads(out.with_name('CHECKSUM.json').read_text())
            assert receipt['sha256']==s.sha(out)
            continue
        started=time.time();f=read(folder,'fitted.json');old=read(folder,'planning_results.json');prepared={};rows=[]
        base=1_000_000_000+s.WORLDS.index(w)*1_000_000_000+k*1_000_000
        for m in ['00','10','01','11']:
            params=parameters(f,m)
            if m in item['available']:
                source=item['available'][m]
                current=[{**x,'mask':m,'mode':'saved_planning_reuse','source_model':source} for x in old if x['model']==source]
            else:
                current=[]
                for ci,(rate,pulse) in enumerate(PLANNING):
                    for rep in range(2):
                        counter_cache.clear();arr=s.arrivals(base+1000+ci*100+rep,rate,pulse,1400)
                        for policy in s.POLICIES:
                            result,_,_=s.simulate(arr,s.Fitted(params),base+2000+ci*100+rep,1400,policy)
                            current.append({'mask':m,'mode':'new_planning','condition':ci,'repeat':rep,'policy':policy['name'],**result})
            assert len(current)==84
            means={p['name']:float(np.mean([x['cost'] for x in current if x['policy']==p['name']])) for p in s.POLICIES}
            choice=min(s.POLICIES,key=lambda p:means[p['name']])['name']
            prepared[m]={'policy':choice,'parameters':params,'planning_costs':means};rows.extend(current)
        settings=[]
        for setting in SETTINGS:
            m=str(int(f['validation_gains'][0]>setting['duration']))+str(int(f['validation_gains'][1]>setting['return']))
            settings.append({**setting,'mask':m,'policy':prepared[m]['policy']})
        s.write(out,{'world':w,'seed':k,'validation_gains':f['validation_gains'],'masks':prepared,'settings':settings,'planning_rows':rows,'seconds':time.time()-started,'test_outcomes_read':False,'protocol_sha256':s.sha(HERE/'SELECTOR_PROTOCOL.md'),'engine_sha256':s.sha(REV/'efficacy_engine.py')})
        s.write(out.with_name('CHECKSUM.json'),{'sha256':s.sha(out)})
        print(name,'prepared',round(time.time()-started,2),flush=True)
def ci(values):
    a=np.asarray(values);mean=float(a.mean());half=float(t.ppf(.975,len(a)-1)*a.std(ddof=1)/math.sqrt(len(a)))
    return {'mean':mean,'low':mean-half,'high':mean+half,'n':len(a)}
def analyze():
    rows=[]
    for w in s.WORLDS:
        for k in range(12):
            name=f'{w}_s{k:02d}';folder=INPUT/name
            p=json.loads((OUT/name/'prepared.json').read_text())
            result=read(folder,'result.json');oracle=json.loads((REV/'results/oracle'/name/'prepared.json').read_text())['policy']
            cost={pol['name']:float(np.mean([x['cost'] for x in result['test'] if x['policy']==pol['name']])) for pol in s.POLICIES}
            crisis={pol['name']:float(np.mean([x['crisis'] for x in result['test'] if x['policy']==pol['name']])) for pol in s.POLICIES}
            choices=p['settings']+[{'axis':'fixed_mask','duration':None,'return':None,'mask':m,'policy':v['policy']} for m,v in p['masks'].items()]
            for setting in choices:
                pol=setting['policy'];rows.append({'world':w,'seed':k,**setting,'duration_retained':int(setting['mask'][0]),'return_retained':int(setting['mask'][1]),'oracle_policy':oracle,'action_agreement':pol.split('_q')[0]==oracle.split('_q')[0],'policy_agreement':pol==oracle,'cost':cost[pol],'normalized_cost':cost[pol]/cost['none'],'regret':cost[pol]-cost[oracle],'crisis':crisis[pol]})
    groups=collections.defaultdict(list)
    for x in rows:groups[(x['world'],x['axis'],x['duration'],x['return'],x['mask'] if x['axis']=='fixed_mask' else '')].append(x)
    summary=[]
    for key,rr in groups.items():
        assert len(rr)==12
        summary.append({'world':key[0],'axis':key[1],'duration':key[2],'return':key[3],'fixed_mask':key[4],**{metric:ci([x[metric] for x in rr]) for metric in ['duration_retained','return_retained','action_agreement','policy_agreement','cost','normalized_cost','regret','crisis']},'policy_counts':dict(collections.Counter(x['policy'] for x in rr))})
    s.write(OUT/'per_seed.json',rows);s.write(OUT/'summary.json',summary);s.write(OUT/'DONE.json',{'fits':48,'rows':len(rows),'summary_rows':len(summary),'test_rollouts_generated':0,'classification':'post-confirmation diagnostic','sources_unchanged':True})
    print('selector sensitivity complete',len(rows),len(summary),flush=True)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['inventory','prepare','analyze','all']);a=parser.parse_args()
    if a.mode=='all':prepare();analyze()
    else:globals()[a.mode]()
