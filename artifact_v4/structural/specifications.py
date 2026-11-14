"""Owner-defined control-flow families; generator constants set before model evaluation.

These are DRAFT specifications until normal-regime calibration is frozen.
"""
from copy import deepcopy

def seq(*x):return {'op':'seq','children':list(x)}
def par(*x):return {'op':'and','children':list(x)}
def xor(attribute,*x):return {'op':'xor','attribute':attribute,'children':list(x)}
def loop(tag,body):return {'op':'loop','tag':tag,'children':[body]}
def action(name,kind,target,cost):return {'name':name,'kind':kind,'target':target,'cost':cost}
def route(source,target_pool,base=.04,complexity=.03,amplitude=.45,driver='global'):
    return {'source':source,'queue_pool':target_pool,'base':base,'complexity':complexity,'amplitude':amplitude,'driver':driver}
def make(name,tree,base,roles,caps,feedback,routes,actions):
    return {'name':name,'tree':tree,'base_duration':base,'roles':roles,'capacities':caps,'service_feedback':feedback,'routes':routes,'actions':[action('none','none',None,0.)]+actions,'complex_fraction':.35,'process_fractions':[1.], 'log_duration_sigma':.25,'complexity_duration_multiplier':.35,'truth_queue_saturation_per_worker':2.,'truth_wip_onset':None,'truth_wip_saturation':None,'normal_scale':None,'status':'draft_before_truth_only_calibration'}
SPECS={}
SPECS['P1']=make('P1',seq('A',loop('joint',seq(par('B','C'),'D'))),
    dict(A=1.,B=2.5,C=1.8,D=1.4),dict(A='entry',B='shared',C='shared',D='finish'),dict(entry=2,shared=3,finish=2),dict(B=1.2,C=.4),
    {'joint':route('D','shared')},[action('capacity_shared','capacity','shared',2.),action('rework_joint','rework',['D'],.5)])
SPECS['P2']=make('P2',seq('A',xor('complex',loop('simple',seq('B','D')),loop('complex',seq('C','E','D')))),
    dict(A=1.,B=2.2,C=2.6,E=1.8,D=1.4),dict(A='entry',B='simple',C='complex',E='complex',D='finish'),dict(entry=2,simple=2,complex=2,finish=2),dict(B=.6,C=1.,E=.4),
    {'simple':route('D','simple',base=.03,complexity=0.),'complex':route('D','complex',base=.09,complexity=0.)},
    [action('capacity_simple','capacity','simple',2.),action('capacity_complex','capacity','complex',2.),action('rework','rework',['D'],.5)])
SPECS['P3']=make('P3',loop('global',seq('A',loop('local',seq('B','C')),'D')),
    dict(A=1.1,B=2.4,C=1.3,D=1.5),dict(A='entry',B='work',C='check',D='finish'),dict(entry=2,work=3,check=2,finish=2),dict(B=1.2),
    {'local':route('C','work',base=.05,amplitude=.4,driver='queue'),'global':route('D','work',base=.025,complexity=.02,amplitude=.35)},
    [action('rework_local','rework',['C'],.5),action('rework_global','rework',['D'],.5),action('capacity_B','capacity','work',2.)])
SPECS['P4']=make('P4',xor('process',seq('A1',loop('X',seq('B1','C1'))),seq('A2',loop('Y',seq('B2','C2')))),
    dict(A1=1.,B1=2.4,C1=1.3,A2=1.2,B2=3.,C2=1.5),dict(A1='entryX',B1='shared',C1='finishX',A2='entryY',B2='shared',C2='finishY'),dict(entryX=2,shared=4,finishX=2,entryY=2,finishY=2),dict(B1=1.1,B2=.8),
    {'X':route('C1','shared',amplitude=.4),'Y':route('C2','shared',base=.07,amplitude=.35,driver='process')},
    [action('capacity_shared','capacity','shared',2.),action('rework_X','rework',['C1'],.5),action('rework_Y','rework',['C2'],.5)])
SPECS['P4']['process_fractions']=[.5,.5]
SPECS['P5']=make('P5',seq('A','B',loop('late',seq('C','D','E'))),
    dict(A=1.,B=2.2,C=1.,D=2.6,E=1.2),dict(A='entry',B='early',C='middle',D='late',E='finish'),dict(entry=2,early=2,middle=2,late=3,finish=2),dict(B=1.1,D=.65),
    {'late':route('E','late',base=.045,amplitude=.4)},
    [action('capacity_B','capacity','early',2.),action('capacity_D','capacity','late',2.),action('rework','rework',['E'],.5)])
SPECS['P6']=make('P6',seq('A',xor('complex',loop('serial',seq('E','F','G')),loop('parallel',seq(par('B','C'),'D','G')))),
    dict(A=1.,B=2.4,C=2.8,D=1.2,E=2.5,F=1.4,G=1.3),dict(A='entry',B='shared',C='parallel',D='join',E='shared',F='serial',G='finish'),dict(entry=2,shared=3,parallel=2,join=2,serial=2,finish=2),dict(B=1.,C=.8,E=.6),
    {'serial':route('G','shared',base=.035),'parallel':route('G','parallel',base=.07)},
    [action('capacity_shared','capacity','shared',2.),action('capacity_parallel','capacity','parallel',2.),action('rework','rework',['G'],.5)])

def expected_visits(spec):
    """Uncongested fixed-world visits, averaged over declared observed classes."""
    labels=sorted(spec['roles'])
    def visits(node,c,p):
        if isinstance(node,str):return {a:float(a==node) for a in labels}
        if node['op']=='xor':return visits(node['children'][c if node['attribute']=='complex' else p],c,p)
        if node['op']=='loop':
            v=visits(node['children'][0],c,p);rr=spec['routes'][node['tag']];prob=rr['base']+rr['complexity']*c
            return {a:x/(1-prob) for a,x in v.items()}
        vv=[visits(child,c,p) for child in node['children']]
        return {a:sum(x[a] for x in vv) for a in labels}
    result={a:0. for a in labels}
    for p,weight in enumerate(spec['process_fractions']):
        for c,cweight in enumerate([1-spec['complex_fraction'],spec['complex_fraction']]):
            v=visits(spec['tree'],c,p)
            for a in labels:result[a]+=weight*cweight*v[a]*(1+spec['complexity_duration_multiplier']*c)
    return result

def nominal_capacity(spec):
    visits=expected_visits(spec);demand={pool:sum(visits[a]*spec['base_duration'][a] for a in visits if spec['roles'][a]==pool) for pool in spec['capacities']}
    return min(spec['capacities'][p]/d for p,d in demand.items() if d>0),demand

def get(name):
    spec=deepcopy(SPECS[name]);capacity,demand=nominal_capacity(spec);spec['nominal_fixed_throughput']=capacity;spec['nominal_pool_demand']=demand
    # Generating laws have their own a-priori scale, distinct from the empirical alarm scale.
    work=sum(demand.values());spec['truth_wip_onset']=max(2.,.4*capacity*work);spec['truth_wip_saturation']=3*spec['truth_wip_onset']
    return spec
