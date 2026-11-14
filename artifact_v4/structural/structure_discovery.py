"""Training-only structural candidates. No known process tree or test cost is an input.

Uses PM4Py IM and its existing strict-tau-loop fallback before permissive concurrency.
Attribute guards are inferred only when an observed binary attribute deterministically
separates per-case activity sets in the calibration log, with >=10 cases per value.
Selection uses training conformance only; no known control-flow tree or test outcomes.
"""
from collections import Counter
import json
from pm4py.algo.discovery.inductive.variants.im import IMUVCL
from pm4py.algo.discovery.inductive.dtypes.im_ds import IMDataStructureUVCL
from pm4py.algo.discovery.inductive.fall_through.strict_tau_loop import StrictTauLoopUVCL
from pm4py.objects.process_tree.utils import generic

class LoopFirstIM(IMUVCL):
 def fall_through(self,obj,parameters=None):
  loop=StrictTauLoopUVCL.apply(obj,parameters=parameters)
  return loop if loop is not None else super().fall_through(obj,parameters)

def convert(node):
 if node.operator is None:return node.label
 mapping={'->':'seq','+':'and','X':'xor','*':'loop'}
 op=mapping[str(node.operator)];children=[convert(c) for c in node.children]
 if op in ['and','xor']:children.sort(key=lambda x:json.dumps(x,sort_keys=True))
 return {'op':op,'children':children}

def mine(cases,guarded=False,attributes=('process','complex')):
 if guarded:
  for attribute in attributes:
   groups={v:[x for x in cases if x[attribute]==v] for v in [0,1]}
   alphabets={v:{frozenset(x['trace']) for x in groups[v]} for v in [0,1]}
   if min(map(len,groups.values()))>=10 and all(len(a)==1 for a in alphabets.values()) and alphabets[0]!=alphabets[1]:
    remaining=tuple(a for a in attributes if a!=attribute)
    children=[mine(groups[v],True,remaining) for v in [0,1]]
    sequences=[list(x['children']) if isinstance(x,dict) and x['op']=='seq' else [x] for x in children]
    prefix=[]
    while all(sequences) and sequences[0][0]==sequences[1][0]:
     prefix.append(sequences[0].pop(0));sequences[1].pop(0)
    def pack(xs):return None if not xs else (xs[0] if len(xs)==1 else {'op':'seq','children':xs})
    guarded={'op':'xor','attribute':attribute,'guard_provenance':'training_activity_presence','children':[pack(x) for x in sequences]}
    return pack(prefix+[guarded])
 variants=Counter(tuple(x['trace']) for x in cases)
 tree=LoopFirstIM({'multiprocessing':False}).apply(IMDataStructureUVCL(variants),{'multiprocessing':False})
 return convert(generic.fold(tree))
