"""Calibration using observable lifecycle records, without generator coefficients."""
from collections import defaultdict, deque
import json, math
import numpy as np
from sklearn.linear_model import Ridge, LogisticRegression
from scipy.special import softmax
from native import compile_net, arrays


def features(rows,spec,net,route=False):
    a=arrays(spec,net);labels=net['labels'];q=rows[:,12] if route else rows[:,7];w=rows[:,13] if route else rows[:,8];wp=rows[:,14] if route else rows[:,9]
    pools=a['route_pool'][rows[:,1].astype(int),rows[:,2].astype(int)] if route else np.array([net['pools'].index(spec['roles'][labels[int(i)]]) for i in rows[:,1]])
    return np.column_stack([np.ones(len(rows)),rows[:,2:4],np.log1p(q/a['capacity'][pools]),np.log1p(w/spec['normal_scale']),np.log1p(wp/spec['normal_scale'])])


def route_dataset(episodes,spec,net):
    """Next enabled activity is a target, never an input; simultaneous labels are canonicalized."""
    n=len(net['labels']);xx=[];yy=[];ss=[]
    for episode in episodes:
        records=episode['records'];x=features(records,spec,net,True)
        bycase=defaultdict(list)
        for k,row in enumerate(records):bycase[int(row[0])].append(k)
        for cid,indices in bycase.items():
            rr=records[indices];ready=sorted([(row[4],int(row[1])) for row in rr]);times=np.array([v[0] for v in ready]);labels=np.array([v[1] for v in ready])
            for k in indices:
                row=records[k];pos=np.searchsorted(times,row[6]-1e-9);target=int(labels[pos]) if pos<len(times) else n
                xx.append(x[k]);yy.append(target);ss.append(int(row[1]))
            # Initial branch choice uses the class/process observed at admission.
            row=rr[0];xx.append([1,row[2],row[3],0,0,0]);yy.append(int(labels[0]));ss.append(n)
    return np.array(xx),np.array(yy,int),np.array(ss,int)


def fit(episodes,validation,spec,net):
    n=len(net['labels']);tr=np.concatenate([e['records'] for e in episodes]);va=np.concatenate([e['records'] for e in validation]);X=features(tr,spec,net);V=features(va,spec,net)
    RX,RY,RS=route_dataset(episodes,spec,net);VX,VY,VS=route_dataset(validation,spec,net)
    result={};loss={}
    route_sources=sorted({net['labels'].index(r['source']) for r in spec['routes'].values()})
    for loaded in (False,True):
        nf=6 if loaded else 3;dc=np.zeros((n,6));ds=np.zeros(n);rc=np.zeros((n+1,n+1,6));rc[:,:,0]=-30
        derror=[];dnll=[]
        for activity in range(n):
            idx=tr[:,1]==activity;vidx=va[:,1]==activity
            if np.sum(idx)<2:raise ValueError('insufficient observed activity '+net['labels'][activity])
            reg=Ridge(alpha=1.,fit_intercept=False).fit(X[idx,:nf],tr[idx,10]);dc[activity,:nf]=reg.coef_
            ds[activity]=max(.05,float(np.std(tr[idx,10]-reg.predict(X[idx,:nf]))))
            residual=va[vidx,10]-V[vidx]@dc[activity]
            derror.extend(np.abs(residual));dnll.extend(.5*(residual/ds[activity])**2+np.log(ds[activity]))
        for source in range(n+1):
            rf=6 if loaded and source in route_sources else 3
            idx=RS==source;y=RY[idx];x=RX[idx,:rf];classes=np.unique(y)
            if len(classes)==0:rc[source,n,0]=0;continue
            if len(classes)==1:rc[source,classes[0],0]=0;continue
            reg=LogisticRegression(C=10.,fit_intercept=False,max_iter=600,tol=1e-7).fit(x,y)
            if len(classes)==2:
                rc[source,classes[0],:rf]=-reg.coef_[0]/2;rc[source,classes[1],:rf]=reg.coef_[0]/2
            else:rc[source,reg.classes_,:rf]=reg.coef_
        predictions=softmax(np.einsum('ik,ijk->ij',VX,rc[VS]),axis=1);target=np.eye(n+1)[VY]
        ri=np.isin(VS,route_sources)
        # Binary Brier-compatible convention, context preserved in both competitors.
        route_loss=float(np.mean(np.sum((predictions[ri]-target[ri])**2,axis=1)/2))
        name='load' if loaded else 'static'
        result[name]=dict(duration_coef=dc.tolist(),duration_sigma=ds.tolist(),route_coef=rc.tolist())
        loss[name]=dict(duration_nll=float(np.mean(dnll)),route_cross_entropy=float(-np.mean(np.log(np.clip(predictions[np.arange(len(VY)),VY][ri],1e-9,1)))),duration_mae_log=float(np.mean(derror)),route_brier=route_loss)
    gains=dict(duration=loss['static']['duration_nll']-loss['load']['duration_nll'],route=loss['static']['route_cross_entropy']-loss['load']['route_cross_entropy'])
    result['validation']=loss;result['gains']=gains;result['route_sources']=route_sources
    result['observed_range']=dict(max_wip=float(np.max(tr[:,8])),max_route_wip=float(np.max(tr[:,13])),duration_rows=len(tr),route_rows=len(RY),activity_counts={label:int(np.sum(tr[:,1]==i)) for i,label in enumerate(net['labels'])})
    repeat_targets={}
    for episode in episodes:
        rec=episode['records']
        for cid in np.unique(rec[:,0]):
            rr=rec[rec[:,0]==cid];ready=sorted([(row[4],int(row[1])) for row in rr]);times=np.array([v[0] for v in ready])
            for row in rr:
                source=int(row[1])
                if source not in route_sources:continue
                pos=np.searchsorted(times,row[6]-1e-9)
                if pos<len(ready):
                    target=ready[pos][1]
                    if np.any((rr[:,1]==target)&(rr[:,5]<row[6]-1e-9)):
                        key=f'{source}_{int(row[2])}_{int(row[3])}'
                        repeat_targets.setdefault(key,set()).add(target)
    result['repeat_targets']={key:sorted(v) for key,v in repeat_targets.items()}
    result['validation_predictions']={key:value.tolist() for key,value in dict(route_source=VS,route_target=VY,route_features=VX,duration_features=V,duration_target=va[:,10],duration_activity=va[:,1]).items()}
    return result


def model_for(fit,mask,disabled_sources=()):
    d=fit['load' if mask[0]=='1' else 'static'];r=fit['load' if mask[1]=='1' else 'static'];rc=np.array(r['route_coef'])
    for source in disabled_sources:rc[source]=fit['static']['route_coef'][source]
    return dict(duration_coef=d['duration_coef'],duration_sigma=d['duration_sigma'],route_coef=rc.tolist())


def discover(episodes,spec,out):
    import pandas as pd,pm4py
    from pm4py.util import constants
    constants.SHOW_PROGRESS_BAR=False
    labels=sorted(spec['roles']);rows=[]
    for ei,e in enumerate(episodes):
        for k,r in enumerate(e['records']):
            rows.append({'case:concept:name':f'{ei}_{int(r[0])}','concept:name':labels[int(r[1])],'time:timestamp':pd.Timestamp('2020-01-01',tz='UTC')+pd.to_timedelta(float(r[6])+ei*100000,unit='s')})
    frame=pd.DataFrame(rows).sort_values(['case:concept:name','time:timestamp','concept:name'],kind='stable')
    tree=pm4py.discover_process_tree_inductive(frame,noise_threshold=0.)
    def convert(node):
        if node.operator is None:return node.label
        op=str(node.operator);children=[convert(c) for c in node.children]
        mapping={'->':'seq','+':'and','X':'xor','*':'loop'}
        if op not in mapping:raise ValueError('unsupported discovered operator '+op)
        if op in ['+','X']:children=sorted(children,key=lambda x:json.dumps(x,sort_keys=True))
        return dict(op=mapping[op],children=children)
    dsl=convert(tree);net=compile_net(spec,dsl)
    pn,im,fm=pm4py.convert_to_petri_net(tree)
    pm4py.write_pnml(pn,im,fm,str(out/'discovered.pnml'))
    fitness=pm4py.fitness_token_based_replay(frame,pn,im,fm)
    precision=pm4py.precision_token_based_replay(frame,pn,im,fm)
    return net,dict(tree=str(tree),dsl=dsl,fitness=fitness,precision=float(precision),training_cases=int(frame['case:concept:name'].nunique()),training_events=len(frame),pm4py=pm4py.__version__,resource_mapping='supplied operational pool map, not inferred',status='executable')


def language(net,limit=10000):
    """Reachable markings of an untimed, single-case safe net, including silent edges."""
    ts=net['transitions'];todo=[1];graph={};final=2
    while todo:
        m=todo.pop()
        if m in graph:continue
        if len(graph)>=limit:raise ValueError('language state bound')
        edges=[]
        for t in ts:
            if m&t['inputs']==t['inputs']:
                dest=(m^t['inputs'])|t['outputs']
                if (m^t['inputs'])&t['outputs']:raise ValueError('unsafe untimed marking')
                edges.append((t['label'],dest));todo.append(dest)
        if m!=final and not edges:raise ValueError('reachable deadlock')
        graph[m]=edges
    reverse=defaultdict(list)
    for m,edges in graph.items():
        for _,dest in edges:reverse[dest].append(m)
    reachable=set();todo=[final]
    while todo:
        m=todo.pop()
        if m in reachable:continue
        reachable.add(m);todo.extend(reverse[m])
    if set(graph)-reachable:raise ValueError('markings without final continuation')
    return graph


def compare_languages(correct,discovered,limit=10000):
    graphs=[language(correct),language(discovered)]
    def close(graph,states):
        todo=list(states);seen=set()
        while todo:
            m=todo.pop()
            if m in seen:continue
            seen.add(m);todo.extend(dest for label,dest in graph.get(m,[]) if label is None)
        return frozenset(seen)
    initial=tuple(close(g,[1]) for g in graphs);todo=deque([(initial,[])]);seen=set();added=missing=None
    while todo:
        pair,word=todo.popleft()
        if pair in seen:continue
        seen.add(pair)
        if len(seen)>limit:return dict(status='state_bound',states=len(seen),added=added,missing=missing)
        accept=[2 in s for s in pair]
        if accept==[False,True] and added is None:added=word
        if accept==[True,False] and missing is None:missing=word
        if added is not None and missing is not None:break
        symbols=set(l for g,s in zip(graphs,pair) for m in s for l,_ in g.get(m,[]) if l is not None)
        for l in sorted(symbols):
            nxt=tuple(close(g,[dest for m in s for label,dest in g.get(m,[]) if label==l]) for g,s in zip(graphs,pair))
            if any(nxt):todo.append((nxt,word+[l]))
    return dict(status='checked',equivalent=added is None and missing is None,states=len(seen),added=added,missing=missing)
