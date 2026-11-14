"""Tables and diagnostic summaries from frozen-policy outcomes, never threshold selection."""
from pathlib import Path
from collections import Counter,defaultdict
import json,csv,math
import numpy as np
from scipy.stats import t
HERE=Path(__file__).resolve().parent;A=HERE/'analysis';PAPER=HERE.parent/'manuscript';G=PAPER/'generated'
def mean(x):return float(np.mean(x))
def interval(x):
 x=np.asarray(x,float);m=float(x.mean());h=float(t.ppf(.975,len(x)-1)*x.std(ddof=1)/math.sqrt(len(x))) if len(x)>1 else 0.;return [m,m-h,m+h]
def write(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False))
def main():
 summary=json.loads((A/'summary.json').read_text());rows=json.loads((A/'per_fit.json').read_text());sensitivity=json.loads((A/'selector_per_fit.json').read_text());discovery=json.loads((A/'discovery.json').read_text());contrasts=json.loads((A/'contrasts.json').read_text());quality=json.loads((A/'model_quality.json').read_text())
 get=lambda p,w,m,v='main':next(x for x in summary if x['process']==p and x['world']==w and x['method']==m and x['variant']==v)
 selector=[];groups=defaultdict(list)
 for r in sensitivity:groups[(r['process'],r['world'],r['structure'],r['axis'],r['delta_duration'],r['delta_return'])].append(r)
 for (p,w,structure,axis,dd,dr),rr in groups.items():selector.append(dict(process=p,world=w,structure=structure,axis=axis,delta_duration=dd,delta_return=dr,n=len(rr),duration_retained=sum(x['duration_retained'] for x in rr),return_retained=sum(x['return_retained'] for x in rr),action_agreement=mean([x['action_agreement'] for x in rr]),cost=mean([x['cost'] for x in rr]),normalized_cost=mean([x['normalized_cost'] for x in rr]),regret=mean([x['regret'] for x in rr]),crisis=mean([x['crisis'] for x in rr])))
 write(A/'selector_summary.json',selector)
 hindsight=[];allfits=defaultdict(list)
 for row in rows:allfits[(row['process'],row['world'],row['variant'],row['seed'])].append(row)
 for (p,w,variant,seed),rr in allfits.items():
  best=min([r for r in rr if r['method']=='no_action' or r['method'].startswith('fixed_')],key=lambda r:r['cost']);oracle=next(r for r in rr if r['method']=='oracle')
  hindsight.append(dict(process=p,world=w,variant=variant,seed=seed,policy=best['policy'],cost=best['cost'],normalized_cost=best['normalized_cost'],generator_gap=oracle['cost']-best['cost'],classification='Retrospective test-selected lower bound, not an executable prospective choice'))
 write(A/'hindsight_per_fit.json',hindsight)
 structure_rows=[]
 for p in ['P1','P2','P3','P4','P5','P6']:
  rr=[r for r in discovery if r['process']==p];paired=[];agreement=0
  for w in ['fixed','service','routing','combined']:
   known={r['seed']:r for r in rows if r['process']==p and r['world']==w and r['variant']=='main' and r['method']=='known_retained'}
   discovered={r['seed']:r for r in rows if r['process']==p and r['world']==w and r['variant']=='main' and r['method']=='discovered_retained'}
   for k in known:
    if k in discovered:paired.append(discovered[k]['normalized_cost']-known[k]['normalized_cost']);agreement+=discovered[k]['policy']==known[k]['policy']
  structure_rows.append(dict(process=p,n=len(rr),fitness=mean([r['fitness']['log_fitness'] for r in rr]),precision=mean([r['precision'] for r in rr]),equivalent=sum(r.get('language',{}).get('equivalent',False) for r in rr),added=sum(r.get('language',{}).get('added') is not None for r in rr),missing=sum(r.get('language',{}).get('missing') is not None for r in rr),language_unresolved=sum(r.get('language',{}).get('status')!='checked' for r in rr),same_policy=agreement,paired_fits=len(paired),normalized_cost_change=interval(paired)))
 write(A/'discovery_summary.json',structure_rows)
 conformance=[]
 for r in discovery:
  language=r.get('language',{});equivalent=language.get('equivalent');status='conforming' if equivalent else ('nonconforming' if language.get('status')=='checked' else 'unresolved')
  conformance.append(dict(process=r['process'],world=r['world'],seed=r['seed'],computational_status=r['status'],reference_structure_status=status,reference_conformance_failure=status=='nonconforming',added_witness=language.get('added'),missing_witness=language.get('missing'),classification='Evaluation of the saved train-only structural audit against synthetic reference; not a policy filter, repaired model, or exclusion from cost analysis'))
 write(A/'structural_conformance.json',conformance)
 # Export complete method/variant table, including all fixed actions and component ablations.
 flat=[]
 for r in summary:
  item={k:r[k] for k in ['process','world','variant','method','n']}
  for metric in ['cost','normalized_cost','regret','normalized_regret','crisis','activation','calm_activation','nonsevere_activation','lead','wip_area','action_cost','residual_wip','cycle_mean','cycle_p95','action_agreement','ranking_error']:
   for key in ['mean','low','high','n']:item[metric+'_'+key]=r[metric][key]
  flat.append(item)
 with (A/'full_summary.csv').open('w') as f:
  writer=csv.DictWriter(f,fieldnames=list(flat[0]));writer.writeheader();writer.writerows(flat)
 with (A/'selector_summary.csv').open('w') as f:
  writer=csv.DictWriter(f,fieldnames=list(selector[0]));writer.writeheader();writer.writerows(selector)
 for lang in ['en','ru']:
  en=lang=='en';lines=[r'\clearpage',r'\section{'+('Independent Structural Extension' if en else 'Независимое структурное расширение')+'}']
  lines.append(('This extension contains 288 independent training datasets and 3168 audited calibration/validation episodes. All datasets satisfy the declared pre-crisis criterion. Known and discovered structures share learned behavioral parameters and supplied resource maps. No discovery repair or test-based policy reselection is applied. The complete machine-readable comparison, including every fixed action and component ablation, is in the archive file \\texttt{analysis/full\\_summary.csv}.' if en else 'Расширение содержит 288 независимых обучающих наборов и 3168 проверенных калибровочных/валидационных эпизодов. Все наборы удовлетворяют заданному предкризисному условию. Известная и обнаруженная структуры используют одинаковые обученные поведенческие параметры и заданные отображения ресурсов. Ручного исправления discovery и выбора политик по тесту нет. Полное машиночитаемое сравнение, включая каждое фиксированное действие и абляции компонентов, находится в архиве: \\texttt{analysis/full\\_summary.csv}.'))
  lines.append(r'\subsection{'+('Costs across all structures and mechanisms' if en else 'Стоимость по всем структурам и механизмам')+'}')
  lines.append(('Tables report the mean of per-fit cost ratios to matched no action, which is 1. Regret is retained-load minus generator-planner cost on that scale. Severe-event incidence refers to retained-load. K denotes known and D discovered structure. Every row has 12 independent fits; the heuristic and generator columns use the same comparator in both structure variants.' if en else 'Таблицы показывают среднее отношений стоимости каждого обученного варианта к соответствующей стоимости без вмешательства, равной 1. Regret — разность retained-load и планировщика с генератором в этой шкале. Частота тяжёлых событий относится к retained-load. K означает известную, D — обнаруженную структуру. В каждой строке 12 независимых обучений; эвристика и генератор одинаковы в обоих структурных вариантах.'))
  for p in ['P1','P2','P3','P4','P5','P6']:
   lines.extend([r'\begin{table}[htbp]\caption{'+p+(' normalized costs and event incidence.' if en else ': нормированная стоимость и частота событий.')+r'}\centering\small\setlength{\tabcolsep}{3pt}',r'\begin{tabular}{llrrrrrrr}\toprule',r'Model & Mechanism & Static & Pred. & Ret. & Heur. & Gen. & Regret & Event\\\midrule'])
   for structure,label in [('known','K'),('discovered','D')]:
    for w in ['fixed','service','routing','combined']:
     v=[get(p,w,m) for m in [structure+'_static',structure+'_predictive',structure+'_retained','heuristic','oracle']];ret=v[2]
     lines.append(label+' & '+w+' & '+' & '.join(f"{x['normalized_cost']['mean']:.3f}" for x in v)+f" & {ret['normalized_regret']['mean']:.3f} & {ret['crisis']['mean']:.3f}"+r'\\')
   lines.append(r'\bottomrule\end{tabular}\end{table}')
  lines.extend([r'\clearpage',r'\subsection{'+('Primary contrasts and discovery checks' if en else 'Основные сравнения и проверка обнаружения структуры')+'}',('The six primary routing contrasts use Bonferroni-adjusted intervals, controlling the family error rate at 0.05. Values below are absolute retained-minus-predictive cost differences divided by 1000, not percent changes. Positive differences favor predictive selection.' if en else 'Шесть основных сравнений при нагрузочных возвратах используют интервалы с поправкой Бонферрони, контролирующей ошибку семейства на уровне 0.05. Ниже приведены абсолютные разности стоимости retained минус predictive, делённые на 1000, а не проценты. Положительная разность означает преимущество предиктивного отбора.'),r'\begin{center}\small\begin{tabular}{lrrr}\toprule',r'Process & Difference & Lower & Upper\\\midrule'])
  for c in contrasts:
   if c['primary']:
    v=c['family_adjusted_difference'];lines.append(c['process']+' & '+' & '.join(f"{v[k]/1000:.3f}" for k in ['mean','low','high'])+r'\\')
  lines.append(r'\bottomrule\end{tabular}\end{center}')
  lines.extend([r'\begin{center}\small\begin{tabular}{lrrrrrr}\toprule',r'Process & Fitness & Precision & Equal & Added & Missing & Same policy\\\midrule'])
  for r in structure_rows:lines.append(f"{r['process']} & {r['fitness']:.3f} & {r['precision']:.3f} & {r['equivalent']}/{r['n']} & {r['added']}/{r['n']} & {r['missing']}/{r['n']} & {r['same_policy']}/{r['paired_fits']}"+r'\\')
  lines.append(r'\bottomrule\end{tabular}\end{center}')
  lines.append(('Language checks compare visible execution languages with a fixed state bound; unresolved checks are retained in \\texttt{discovery\\_summary.json}. Same policy counts exact retained-load action/threshold agreement between known and discovered structure across all four mechanisms. The 144 models with added paths are recorded as reference-conformance failures in \\texttt{structural\\_conformance.json}; their unrepaired costs remain in the error analysis. This reference-based evaluation flag is separate from computational failure and is not a deployed rejection rule.' if en else 'Проверка языков сравнивает видимые последовательности исполнения с фиксированным ограничением числа состояний; незавершённые проверки сохранены в \\texttt{discovery\\_summary.json}. Same policy считает полное совпадение действия и порога retained-load между известной и обнаруженной структурой во всех четырёх механизмах. 144 модели с добавленными путями зарегистрированы как нарушения соответствия исходной структуре в \\texttt{structural\\_conformance.json}; их стоимость без исправления сохраняется для анализа ошибок. Этот признак оценки по известному оригиналу отделён от вычислительного отказа и не является реализованным правилом допуска политики.'))
  lines.extend([r'\subsection{'+('Selector sensitivity' if en else 'Чувствительность селектора')+'}',('The sweeps reuse saved planning selections and independent test actions. They are diagnostic; no threshold is selected from test costs. The following tables concern routing feedback and known structure. Duration and return counts give the number of retained components out of 12. Agree is action-type agreement with generator planning; regret is absolute cost difference divided by 1000. Other mechanisms and discovered structures are included in \\texttt{selector\\_summary.csv}.' if en else 'Перебор использует сохранённые планировочные решения и независимые тестовые действия. Это диагностика; порог не выбирается по тестовой стоимости. Таблицы относятся к нагрузочным возвратам и известной структуре. D и R — число сохранённых компонентов из 12. Agree — совпадение типа действия с планировщиком по генератору; regret — абсолютная разность стоимости, делённая на 1000. Остальные механизмы и обнаруженные структуры включены в \\texttt{selector\\_summary.csv}.')])
  for axis in ['return','duration']:
   lines.extend([r'\begingroup\small\setlength{\tabcolsep}{3pt}\begin{longtable}{llrrrrrr}\caption{'+('Selector sweep: ' if en else 'Перебор селектора: ')+axis+r'.}\\\toprule',r'Process & Threshold & D & R & Agree & Cost ratio & Regret & Event\\\midrule\endfirsthead',r'\toprule Process & Threshold & D & R & Agree & Cost ratio & Regret & Event\\\midrule\endhead'])
   for r in selector:
    if r['world']=='routing' and r['structure']=='known' and r['axis']==axis:
     delta=r['delta_return' if axis=='return' else 'delta_duration'];lines.append(f"{r['process']} & {delta:g} & {r['duration_retained']} & {r['return_retained']} & {r['action_agreement']:.3f} & {r['normalized_cost']:.3f} & {r['regret']/1000:.3f} & {r['crisis']:.3f}"+r'\\')
   lines.append(r'\bottomrule\end{longtable}\endgroup')
  lines.append(('Raw trajectory archives retain all independent arrivals and candidate action outcomes. Per-fit records include actual thresholds, their relation to calibration support, activation, lead time, false and unnecessary activation, WIP area, completed-case durations and residual work. Completed-case duration is censored by the evaluation horizon; complete-cohort replays, where available, are separate extended-horizon diagnostics. P4 records preserve outcomes for both competing processes.' if en else 'Исходные архивы траекторий содержат все независимые поступления и исходы кандидатных действий. Записи по обучающим наборам включают фактические пороги, их отношение к диапазону калибровки, активацию, время предупреждения, ложные и ненужные активации, интеграл WIP, длительности завершённых экземпляров и остаточную работу. Длительности завершённых экземпляров ограничены горизонтом оценки; проверки полной когорты, где доступны, являются отдельной диагностикой с продлённым горизонтом. Записи P4 сохраняют результаты обоих конкурирующих процессов.'))
  lines.append(r'\input{generated/operational_supplement_'+lang+'.tex}')
  (G/f'structural_supplement_{lang}.tex').write_text('\n\n'.join(lines)+'\n')
 print('DISCOVERY',structure_rows)
 for p in ['P1','P2','P3','P4','P5','P6']:
  print('SELECTOR',p,[(r['axis'],r['delta_return'] if r['axis']=='return' else r['delta_duration'],r['return_retained'],round(r['normalized_cost'],4)) for r in selector if r['process']==p and r['world']=='routing' and r['structure']=='known'])
 print('FAILURE_DIAGNOSTICS',[(r['process'],r['method'],round(r['normalized_cost']['mean'],4),r['policies']) for r in summary if r['process'] in ['P3','P4'] and r['world']=='routing' and r['variant']=='main' and r['method'].startswith('known_')])
 print('ROBUSTNESS',[(r['process'],r['world'],r['variant'],r['method'],round(r['normalized_cost']['mean'],4)) for r in summary if r['variant']!='main' and r['method'] in ['known_retained','known_predictive','heuristic','oracle']])
if __name__=='__main__':main()
