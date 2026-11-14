"""Executable process trees, a unit-arc compiler and the single-thread native simulator."""
from pathlib import Path
import ctypes as ct, json, math
import numpy as np
HERE=Path(__file__).resolve().parent
WORLDS=['fixed','service','routing','combined']

def canonicalize_observed_tree(node):
    """Move a loop choice past its shared following redo block, preserving its language.

    seq(loop(body, redo), redo) == loop(seq(body, redo), tau).
    A next-activity model cannot distinguish the old alternatives, which both begin
    with redo. The rewritten choice occurs at the observed return decision instead.
    Apply only to supplied/discovered trees, not to the truth generator specification.
    """
    if node is None or isinstance(node,str):return node
    node=dict(node,children=[canonicalize_observed_tree(x) for x in node['children']])
    if node['op']!='seq':return node
    ch=[]
    for x in node['children']:
        ch.extend(x['children'] if isinstance(x,dict) and x['op']=='seq' else [x])
    out=[];i=0
    while i<len(ch):
        x=ch[i]
        if isinstance(x,dict) and x['op']=='loop' and len(x['children'])==2 and x['children'][1] is not None and i+1<len(ch) and x['children'][1]==ch[i+1]:
            body=canonicalize_observed_tree({'op':'seq','children':[x['children'][0],ch[i+1]]})
            out.append(dict(x,children=[body,None]));i+=2
        else:out.append(x);i+=1
    return out[0] if len(out)==1 else dict(node,children=out)

def compile_net(spec,tree=None):
    if tree is not None:tree=canonicalize_observed_tree(tree)
    labels=sorted(spec['roles']);pools=sorted(spec['capacities']);trans=[];groups=[];places=2
    def place():
        nonlocal places
        x=places;places+=1;return x
    def add(label,ins,outs,g=-1,kind=0,option=0):
        trans.append(dict(label=label,inputs=sum(1<<p for p in ins),outputs=sum(1<<p for p in outs),group=g,kind=kind,option=option))
    def group(node,kind):
        g=len(groups);groups.append(dict(kind=kind,attribute=node.get('attribute','unknown'),tag=node.get('tag','unknown')));return g
    def build(node,entry,exit):
        if node is None or isinstance(node,str):add(node,[entry],[exit]);return
        op,ch=node['op'],node['children']
        if op=='seq':
            pts=[entry]+[place() for _ in ch[1:]]+[exit]
            for x,a,b in zip(ch,pts,pts[1:]):build(x,a,b)
        elif op=='and':
            starts=[place() for _ in ch];ends=[place() for _ in ch];add(None,[entry],starts)
            for x,a,b in zip(ch,starts,ends):build(x,a,b)
            add(None,ends,[exit])
        elif op=='xor':
            g=group(node,1)
            for i,x in enumerate(ch):
                start=place();add(None,[entry],[start],g,1,i);build(x,start,exit)
        elif op=='loop' and len(ch) in (1,2):
            start,choice,redo=place(),place(),place();g=group(node,2)
            add(None,[entry],[start]);build(ch[0],start,choice)
            add(None,[choice],[exit],g,2,0);add(None,[choice],[redo],g,2,1)
            build(ch[1] if len(ch)==2 else None,redo,start)
        else:raise ValueError('unsupported tree '+str(op))
    build(spec['tree'] if tree is None else tree,0,1)
    if places>62 or len(trans)>120:raise ValueError('net exceeds implementation bound')
    def first(mark):
        # Reachability through silent arcs; visible transitions terminate each path.
        todo=[p for p in range(places) if mark>>p&1];seen=set();result=0
        while todo:
            p=todo.pop()
            if p in seen:continue
            seen.add(p)
            if p==1:result|=1<<len(labels)
            for t in trans:
                if t['inputs']>>p&1:
                    if t['label'] is not None:result|=1<<labels.index(t['label'])
                    else:todo.extend(q for q in range(places) if t['outputs']>>q&1)
        return result
    for t in trans:t['first']=first(t['outputs'])
    for g,node in enumerate(groups):
        options=[t for t in trans if t['group']==g]
        if node['kind']==1 and node['attribute'] in ('complex','process'):continue
        for i,t in enumerate(options):
            for u in options[i+1:]:
                if t['first'] & u['first']:
                    raise ValueError('unidentifiable choice: overlapping first-visible labels; normalize or fit a richer routing model')
    return dict(labels=labels,pools=pools,transitions=trans,groups=groups,places=places,initial=1,final=2,tree=spec['tree'] if tree is None else tree)

PINT=ct.POINTER(ct.c_int);PDOUBLE=ct.POINTER(ct.c_double);PUINT=ct.POINTER(ct.c_uint64)
class Input(ct.Structure):
    _fields_=([(n,ct.c_int) for n in 'ncases ntrans npools nlabels ngroups nfeatures mode world action_kind action_pool max_operations keep_records verify'.split()]+
      [(n,ct.c_double) for n in 'horizon dt event_duration event_threshold trigger_threshold action_cost action_effect'.split()]+
      [(n,ct.c_uint64) for n in 'seed initial_mark final_mark action_sources'.split()]+[('schedule',PDOUBLE)]+
      [(n,PUINT) for n in 'inputs outputs first_labels'.split()]+
      [(n,PINT) for n in 'labels pools groups choice_kind choice_option group_attribute capacity route_pool group_source group_pool group_driver'.split()]+
      [(n,PDOUBLE) for n in 'duration_base duration_amplitude group_base group_complexity group_amplitude duration_coef duration_sigma route_coef'.split()]+
      [(n,ct.c_double) for n in 'load_scale truth_onset truth_saturation noise_sigma complexity_multiplier'.split()])
class Output(ct.Structure):
    _fields_=[(n,ct.c_int) for n in 'status operations completions nsamples'.split()]+[(n,ct.c_double) for n in ['trigger','max_wip']]
LIB=ct.CDLL(str(HERE/'engine.so'));LIB.input_size.restype=LIB.output_size.restype=ct.c_size_t
LIB.simulation_error.restype=ct.c_char_p
LIB.simulate.argtypes=[ct.POINTER(Input),ct.POINTER(Output),PDOUBLE,PDOUBLE,PDOUBLE]
assert LIB.input_size()==ct.sizeof(Input) and LIB.output_size()==ct.sizeof(Output)

def arrays(spec,net):
    labels,pools=net['labels'],net['pools'];ts=net['transitions'];gs=net['groups'];n=len(labels)
    a={}
    for name,key in [('inputs','inputs'),('outputs','outputs'),('first_labels','first')]:a[name]=np.array([t[key] for t in ts],dtype=np.uint64)
    for name,key in [('groups','group'),('choice_kind','kind'),('choice_option','option')]:a[name]=np.array([t[key] for t in ts],np.int32)
    a['labels']=np.array([labels.index(t['label']) if t['label'] is not None else -1 for t in ts],np.int32)
    a['pools']=np.array([pools.index(spec['roles'][t['label']]) if t['label'] is not None else -1 for t in ts],np.int32)
    a['capacity']=np.array([spec['capacities'][p] for p in pools],np.int32)
    a['duration_base']=np.array([spec['base_duration'][l] for l in labels],float)
    a['duration_amplitude']=np.array([spec['service_feedback'].get(l,0.) for l in labels],float)
    # Queue observation contract is operational metadata supplied equally to both structures.
    rp=np.array([[pools.index(spec['roles'][l])]*2 for l in labels]+[[0,0]],np.int32)
    for tag,r in spec['routes'].items():
        contexts=[0] if tag in ['simple','serial'] else ([1] if tag in ['complex','parallel'] else [0,1])
        for c in contexts:rp[labels.index(r['source']),c]=pools.index(r['queue_pool'])
    a['route_pool']=rp
    for key in ['group_attribute','group_source','group_pool','group_driver']:a[key]=np.zeros(max(1,len(gs)),np.int32)
    for key in ['group_base','group_complexity','group_amplitude']:a[key]=np.zeros(max(1,len(gs)),float)
    for g,node in enumerate(gs):
        a['group_attribute'][g]={'complex':0,'process':1}.get(node['attribute'],-1)
        if node['kind']==2 and node['tag'] in spec['routes']:
            r=spec['routes'][node['tag']];a['group_source'][g]=labels.index(r['source']);a['group_pool'][g]=pools.index(r['queue_pool']);a['group_driver'][g]=['global','queue','process'].index(r['driver'])
            for key,field in [('group_base','base'),('group_complexity','complexity'),('group_amplitude','amplitude')]:a[key][g]=r[field]
    return a

def simulate(spec,net,schedule,seed,world='fixed',model=None,policy=None,horizon=1000.,dt=1.,keep=True,verify=False,effect=.5):
    n=len(net['labels']);pp=len(net['pools']);a=arrays(spec,net);a['schedule']=np.ascontiguousarray(schedule,dtype=float).reshape(-1,3)
    if model is None:
        a.update(duration_coef=np.zeros((n,6)),duration_sigma=np.zeros(n),route_coef=np.zeros((n+1,n+1,6)))
    else:
        for name in ['duration_coef','duration_sigma','route_coef']:a[name]=np.ascontiguousarray(model[name],dtype=float)
    if np.any(~np.isfinite(a['schedule'])) or np.any(np.diff(a['schedule'][:,0])<0):raise ValueError('invalid arrival schedule')
    I=Input();I.ncases=len(schedule);I.ntrans=len(net['transitions']);I.npools=pp;I.nlabels=n;I.ngroups=len(net['groups']);I.nfeatures=6;I.mode=int(model is not None);I.world=WORLDS.index(world)
    I.max_operations=max(10000,len(schedule)*150);I.keep_records=int(keep);I.verify=int(verify);I.horizon=horizon;I.dt=dt;I.seed=seed;I.initial_mark=1;I.final_mark=2
    I.load_scale=spec.get('normal_scale') or spec['truth_wip_onset'];I.truth_onset=spec['truth_wip_onset'];I.truth_saturation=spec['truth_wip_saturation'];I.noise_sigma=spec['log_duration_sigma'];I.complexity_multiplier=spec['complexity_duration_multiplier']
    policy=policy or dict(kind='none',cost=0.)
    I.action_kind=['none','capacity','rework'].index(policy['kind']);I.trigger_threshold=policy.get('threshold',-1.);I.action_cost=policy['cost'];I.action_effect=effect
    if policy['kind']=='capacity':I.action_pool=net['pools'].index(policy['target'])
    if policy['kind']=='rework':I.action_sources=sum(1<<net['labels'].index(l) for l in policy['target'])
    for name,value in a.items():
        dtype={'i':PINT,'u':PUINT,'f':PDOUBLE}[value.dtype.kind];setattr(I,name,value.ctypes.data_as(dtype))
    samples=np.zeros((int(math.floor(horizon/dt+1e-8))+1,8+pp));records=np.empty((I.max_operations if keep else 1,16));completed=np.empty((max(1,len(schedule)),4));O=Output()
    status=LIB.simulate(ct.byref(I),ct.byref(O),samples.ctypes.data_as(PDOUBLE),records.ctypes.data_as(PDOUBLE),completed.ctypes.data_as(PDOUBLE))
    if status:raise RuntimeError(f'native simulation {status}: '+LIB.simulation_error().decode())
    return dict(samples=samples[:O.nsamples],records=records[:O.operations] if keep else records[:0],completed=completed[:O.completions],trigger=float(O.trigger),max_wip=float(O.max_wip),operations=O.operations)

def arrivals(spec,seed,baseline,horizon,pulse=None,mix=None):
    rng=np.random.default_rng(seed);result=[]
    # Independent stream per process, explicit piecewise-constant Poisson intensities.
    for p,weight in enumerate(spec['process_fractions']):
        segments=[(0,horizon,baseline)] if pulse is None else [(0,pulse[0],baseline),(pulse[0],pulse[1],pulse[2]),(pulse[1],horizon,baseline)]
        for left,right,rate in segments:
            if right<=left or rate*weight<=0:continue
            times=left+np.cumsum(rng.exponential(1/(rate*weight),size=max(20,int((right-left)*rate*weight*1.5+50))))
            while times[-1]<right:times=np.r_[times,times[-1]+np.cumsum(rng.exponential(1/(rate*weight),size=100))]
            for t in times[times<right]:result.append([t,int(rng.random()<(spec['complex_fraction'] if mix is None else mix)),p])
    return np.array(sorted(result),float).reshape(-1,3)

def metrics(run,spec,policy,dt):
    s=run['samples'];h=float(s[-1,0]);threshold=spec['severe_wip'];duration=spec['severe_duration'];streak=0;onset=None
    for row in s:
        streak=streak+1 if row[1]>=threshold else 0
        if onset is None and (streak-1)*dt>=duration:onset=float(row[0]-(streak-1)*dt)
    area=float(np.trapezoid(s[:,1],s[:,0]));charge=policy['cost']*max(0,h-run['trigger']) if run['trigger']>=0 else 0.
    cycles=run['completed'][:,2]
    return dict(cost=area+charge,wip_area=area,action_cost=charge,trigger=run['trigger'],crisis=onset is not None,crisis_onset=onset,maximum_wip=run['max_wip'],residual_wip=float(s[-1,1]),completed=len(cycles),cycle_mean=float(np.mean(cycles)) if len(cycles) else None,cycle_p95=float(np.quantile(cycles,.95)) if len(cycles) else None,process=[dict(wip_area=float(np.trapezoid(s[:,4+p],s[:,0])),completed=int(np.sum(run['completed'][:,3]==p)),cycle_mean=float(np.mean(run['completed'][run['completed'][:,3]==p,2])) if np.any(run['completed'][:,3]==p) else None) for p in range(len(spec['process_fractions']))])
