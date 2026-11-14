"""Operational diagnostics from saved tests and exact-prefix resource replays."""
from pathlib import Path
from collections import defaultdict,Counter
import json,csv,math
import numpy as np
from scipy.stats import t
HERE=Path(__file__).resolve().parent;A=HERE/'analysis';G=HERE.parent/'manuscript/generated'
def mean(x):return float(np.mean(x)) if x else None
def ci(x):
 x=np.array([v for v in x if v is not None],float);n=len(x)
 if not n:return dict(mean=None,low=None,high=None,n=0)
 m=float(x.mean());h=float(t.ppf(.975,n-1)*x.std(ddof=1)/math.sqrt(n)) if n>1 else 0.;return dict(mean=m,low=m-h,high=m+h,n=n)
def write(path,x):path.write_text(json.dumps(x,indent=2,allow_nan=False))
def main():
 perfit=json.loads((A/'per_fit.json').read_text());resource=json.loads((A/'resource_diagnostic/summary.json').read_text());recovery=json.loads((A/'recovery_per_trajectory.json').read_text())
 assert json.loads((A/'resource_diagnostic/DONE.json').read_text())['all_prefixes_exact']
 current=[r for r in perfit if r['variant']=='main'];lookup={(r['process'],r['world'],r['seed'],r['method']):r for r in current};scales={p:json.loads((HERE/'calibration'/f'{p}.json').read_text()) for p in ['P1','P2','P3','P4','P5','P6']}
 # No dependency on assumptions about the calibration JSON wrapper: use saved preparation specs.
 scales={p:json.loads((HERE/'main_v1'/f'{p}_routing_s00/PREPARED.json').read_text())['spec'] for p in scales}
 queues=[];p4=[]
 for process in ['P4','P5']:
  for world in ['fixed','service','routing','combined']:
   selected=[r for r in resource if r['process']==process and r['world']==world]
   names=['none','capacity_shared_q10','rework_X_q10','rework_Y_q10'] if process=='P4' else ['none','capacity_B_q10','capacity_D_q10','rework_q10']
   for policy in names:
    rr=[r for r in selected if r['policy']==policy];assert len(rr)==24
    byseed=defaultdict(list)
    for r in rr:byseed[r['seed']].append(r)
    poolstats={pool:ci([mean([next(v['mean_queue'] for v in r['pools'] if v['pool']==pool) for r in xx]) for xx in byseed.values()]) for pool in [v['pool'] for v in rr[0]['pools']]}
    migration=sum(next(r for r in selected if r['seed']==x['seed'] and r['condition']==x['condition'] and r['policy']=='none')['queue_bottleneck']=='early' and x['queue_bottleneck']=='late' for x in rr) if process=='P5' else None
    queues.append(dict(process=process,world=world,policy=policy,n_fits=len(byseed),trajectories=len(rr),pool_queues=poolstats,bottlenecks=dict(Counter(x['queue_bottleneck'] for x in rr)),early_to_late=migration))
    if process=='P4':
     method='no_action' if policy=='none' else 'fixed_'+policy
     for proc in [0,1]:
      full=[lookup[(process,world,k,method)]['process_metrics'][proc] for k in range(12)]
      cohort=[mean([r['complete_cohort'][proc]['cycle_mean'] for r in xx]) for xx in byseed.values()]
      p4.append(dict(world=world,policy=policy,process_id=proc,wip_area=ci([r['wip_area'] for r in full]),completed_case_cycle=ci([r['cycle_mean'] for r in full]),extended_complete_cohort_cycle=ci(cohort),cohort_scope='Two fixed high-baseline pulse conditions, one replicate each, action maintained through600T; WIP uses all48 original test episodes.'))
 write(A/'resource_summary.json',queues);write(A/'P4_process_outcomes.json',p4)
 recoveries=[];recover_by=defaultdict(list)
 for r in recovery:recover_by[(r['process'],r['world'],r['seed'],r['policy'])].append(r)
 methods=['no_action','oracle','heuristic','known_retained','known_predictive','discovered_retained','discovered_predictive']
 for p in ['P1','P2','P3','P4','P5','P6']:
  T=scales[p]['cycle_scale']
  for w in ['fixed','service','routing','combined']:
   for method in methods:
    fitrows=[]
    for seed in range(12):
     selected=lookup[(p,w,seed,method)];rr=recover_by[(p,w,seed,selected['policy'])];assert len(rr)==32
     fitrows.append(dict(seed=seed,recovered_fraction=mean([x['recovered_by_horizon'] for x in rr]),capped_delay_T=mean([(x['recovery_delay']/T if x['recovery_delay'] is not None else 180-x['pulse_end']/T) for x in rr]),tail_wip_area=mean([x['tail_wip_area'] for x in rr]),above_severe_after_pulse_T=mean([x['above_severe_after_pulse']/T for x in rr])))
    recoveries.append(dict(process=p,world=w,method=method,n=12,criterion='WIP<=2S for10T, observed after pulse, censored at180T; capped delay assigns each censored path its available follow-up',per_fit=fitrows,**{k:ci([r[k] for r in fitrows]) for k in ['recovered_fraction','capped_delay_T','tail_wip_area','above_severe_after_pulse_T']}))
 write(A/'recovery_summary.json',recoveries)
 support=[]
 for p in ['P1','P2','P3','P4','P5','P6']:
  for w in ['fixed','service','routing','combined']:
   for structure in ['known','discovered']:
    rr=[lookup[(p,w,k,structure+'_retained')] for k in range(12)];ratios=[r['threshold_relative_observed_max'] for r in rr if r['threshold_relative_observed_max'] is not None]
    support.append(dict(process=p,world=w,structure=structure,threshold_counts={str(k):v for k,v in Counter(r['threshold'] for r in rr).items()},training_max_wip_range=[min(r['calibration_max_wip'] for r in rr),max(r['calibration_max_wip'] for r in rr)],threshold_to_training_max_range=[min(ratios),max(ratios)] if ratios else None,above_training_range=sum(r['threshold'] is not None and r['threshold']>r['calibration_max_wip'] for r in rr),activation=ci([r['activation'] for r in rr]),nonsevere_activation=ci([r['nonsevere_activation'] for r in rr]),lead_T=ci([r['lead']/scales[p]['cycle_scale'] if r['lead'] is not None else None for r in rr]),crisis=ci([r['crisis'] for r in rr]),prevented_fraction=ci([r['prevented_fraction'] for r in rr])))
 write(A/'trigger_support.json',support)
 for lang in ['en','ru']:
  en=lang=='en';lines=[r'\clearpage',r'\subsection{'+('Trigger support and recovery' if en else 'Диапазон наблюдений, активация и восстановление')+'}']
  lines.append(('The following routing-feedback table reports retained-load choices. Threshold counts show actual WIP values and numbers of fits. The training range is the range, across fits, of maximum observed training WIP; $q/\\max w$ is calculated within each fit. K/D denote known/discovered structure. These diagnostics do not alter activation rules.' if en else 'Таблица при нагрузочных возвратах показывает выбор retained-load. Числа порогов обозначают фактические значения WIP и число обучений. Диапазон обучения — разброс максимального наблюдавшегося WIP между наборами; $q/\\max w$ считается внутри каждого набора. K/D обозначают известную/обнаруженную структуру. Диагностика не меняет правила активации.'))
  lines.extend([r'\begin{center}\small\setlength{\tabcolsep}{3pt}\begin{tabular}{llp{.24\textwidth}rrr}\toprule',r'Process & N & Threshold:count & Train max & $q/\max w$ & Above\\\midrule'])
  for r in support:
   if r['world']!='routing':continue
   counts='; '.join(('none' if k=='None' else f'{float(k):g}')+':'+str(v) for k,v in r['threshold_counts'].items());ranges=r['training_max_wip_range'];ratio=r['threshold_to_training_max_range']
   lines.append(r['process']+' & '+('K' if r['structure']=='known' else 'D')+' & '+counts+f' & {ranges[0]:g}--{ranges[1]:g} & {ratio[0]:.2f}--{ratio[1]:.2f} & '+str(r['above_training_range'])+r'/12\\')
  lines.append(r'\bottomrule\end{tabular}\end{center}')
  lines.extend([r'\begin{center}\small\setlength{\tabcolsep}{4pt}\begin{tabular}{llrrrrr}\toprule',r'Process & N & Activate & Nonsevere & Lead/$T$ & Event & Prevented\\\midrule'])
  for r in support:
   if r['world']=='routing':lines.append(r['process']+' & '+('K' if r['structure']=='known' else 'D')+' & '+' & '.join('--' if r[k]['mean'] is None else f"{r[k]['mean']:.3f}" for k in ['activation','nonsevere_activation','lead_T','crisis','prevented_fraction'])+r'\\')
  lines.append(r'\bottomrule\end{tabular}\end{center}')
  lines.append(('Nonsevere activation is conditional on no severe event in matched no action; it is not necessarily a harmful intervention. Lead time is measured against that counterfactual event onset. Prevention is conditional on an event without action. Recovery below is WIP at most $2S$ for $10T$ after a pulse, censored at the original $180T$ horizon. Entries average within each independent fit before averaging over fits; they concern all pulse trajectories, not only crisis trajectories.' if en else 'Nonsevere — активация при отсутствии тяжёлого события в парной траектории без действия; это не обязательно вредное вмешательство. Время предупреждения измеряется относительно начала такого контрфактического события. Предотвращение условно по событию без действия. Восстановление ниже означает WIP не выше $2S$ в течение $10T$ после импульса с цензурированием на исходном горизонте $180T$. Сначала усредняются траектории каждого независимого обучения, затем сами обучения; учитываются все импульсные траектории, а не только кризисные.'))
  lines.extend([r'\begin{center}\small\begin{tabular}{lrrrr}\toprule',r'Process & No action & Predictive K & Retained K & Generator\\\midrule'])
  for p in ['P1','P2','P3','P4','P5','P6']:
   vals=[next(r for r in recoveries if r['process']==p and r['world']=='routing' and r['method']==m)['recovered_fraction']['mean'] for m in ['no_action','known_predictive','known_retained','oracle']];lines.append(p+' & '+' & '.join(f'{x:.3f}' for x in vals)+r'\\')
  lines.append(r'\bottomrule\end{tabular}\end{center}')
  lines.append(r'\subsection{'+('Shared-resource consequences and bottleneck location' if en else 'Последствия общих ресурсов и положение узкого места')+'}')
  lines.append((f'The resource diagnostic replays P4/P5 under all four mechanisms and all 12 fits, using the two high-baseline pulse conditions and replicate 0. Every action type at the smallest frozen threshold is included, together with saved selected policies. All {len(resource)} prefixes through $180T$ exactly match original test samples. Arrivals then stop and actions remain active through $600T$ to complete the arrival cohort. Queue integrals use only the original horizon. Complete-cohort duration therefore has a different horizon from the primary endpoint.' if en else f'Ресурсная диагностика повторяет P4/P5 при всех четырёх механизмах и всех 12 обучениях для двух импульсных условий с высокой базовой интенсивностью и повтора 0. Включены все типы действий на минимальном фиксированном пороге и сохранённые выбранные политики. Все {len(resource)} префиксов до $180T$ точно совпадают с исходными тестовыми отсчётами. Затем поступления прекращаются, а действия сохраняются до $600T$ для завершения когорты. Интегралы очередей относятся только к исходному горизонту. Поэтому длительность полной когорты имеет другой горизонт, чем основной показатель.'))
  lines.extend([r'\begin{longtable}{llrrrr}\caption{'+('P4: process-specific WIP integrals (thousands) from the full test, and complete-cohort cycle times from the extended diagnostic.' if en else 'P4: интегралы WIP каждого процесса (тысячи) по полному тесту и времена завершения полной когорты по продлённой диагностике.')+r'}\\\toprule',r'Mechanism & Action at 10 & WIP X & WIP Y & Cycle X & Cycle Y\\\midrule\endfirsthead',r'\toprule Mechanism & Action at 10 & WIP X & WIP Y & Cycle X & Cycle Y\\\midrule\endhead'])
  for w in ['fixed','service','routing','combined']:
   for policy,label in [('none','None'),('capacity_shared_q10','Capacity'),('rework_X_q10','Rework X'),('rework_Y_q10','Rework Y')]:
    rr=[next(r for r in p4 if r['world']==w and r['policy']==policy and r['process_id']==q) for q in [0,1]];lines.append(w+' & '+label+' & '+' & '.join(f"{x['wip_area']['mean']/1000:.2f}" for x in rr)+' & '+' & '.join(f"{x['extended_complete_cohort_cycle']['mean']:.2f}" for x in rr)+r'\\')
  lines.append(r'\bottomrule\end{longtable}')
  lines.extend([r'\begin{longtable}{llrrr}\caption{'+('P5: mean queue lengths at B and D during the original horizon; number of paired paths whose largest queue moves from B to D.' if en else 'P5: средние очереди B и D на исходном горизонте; число парных траекторий с перемещением наибольшей очереди от B к D.')+r'}\\\toprule',r'Mechanism & Action at 10 & Queue B & Queue D & B to D\\\midrule\endfirsthead',r'\toprule Mechanism & Action at 10 & Queue B & Queue D & B to D\\\midrule\endhead'])
  for r in queues:
   if r['process']=='P5':lines.append(r['world']+' & '+{'none':'None','capacity_B_q10':'Capacity B','capacity_D_q10':'Capacity D','rework_q10':'Rework'}[r['policy']]+f" & {r['pool_queues']['early']['mean']:.2f} & {r['pool_queues']['late']['mean']:.2f} & {r['early_to_late']}/24"+r'\\')
  lines.append(r'\bottomrule\end{longtable}')
  (G/f'operational_supplement_{lang}.tex').write_text('\n\n'.join(lines)+'\n')
 print('P5 QUEUES',[(r['world'],r['policy'],r['early_to_late'],r['bottlenecks'],{k:round(v['mean'],2) for k,v in r['pool_queues'].items() if k in ['early','late']}) for r in queues if r['process']=='P5'])
 print('RECOVERY ROUTING',[(r['process'],r['method'],round(r['recovered_fraction']['mean'],3)) for r in recoveries if r['world']=='routing' and r['method'] in ['no_action','known_retained','known_predictive','oracle']])
if __name__=='__main__':main()
