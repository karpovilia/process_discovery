"""Generate tables and a common-scale process-by-mechanism figure from audited fit summaries."""
from pathlib import Path
import json,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE=Path(__file__).resolve().parent;A=HERE/'analysis'
PAPER=HERE.parent/'manuscript'
# New campaign output is isolated from the published v7 manuscript.
G=PAPER/'generated'

def main():
    summary=json.loads((A/'summary.json').read_text());contrasts=json.loads((A/'contrasts.json').read_text())
    get=lambda p,w,m:next(x for x in summary if x['process']==p and x['world']==w and x['method']==m and x['variant']=='main')
    processes=['P1','P2','P3','P4','P5','P6'];worlds=['fixed','service','routing','combined']
    mats=[]
    for structure in ['discovered','legacy_discovered']:
        mats.append(np.array([[100*next(x for x in contrasts if x['process']==p and x['world']==w and x['structure']==structure and x['variant']=='main' and x['baseline']=='predictive')['relative_mean_reduction'] for w in worlds] for p in processes]))
    limit=max(5,float(np.max(np.abs(mats))))
    for lang in ['en','ru']:
        fig,axes=plt.subplots(1,2,figsize=(6.0,3.6),layout='constrained')
        for j,(ax,matrix) in enumerate(zip(axes,mats)):
            im=ax.imshow(matrix,cmap='RdBu',vmin=-limit,vmax=limit,aspect='auto')
            ax.set_xticks(range(4),['Fixed','Service','Routing','Combined'] if lang=='en' else ['Без связей','Время','Возвраты','Оба']);ax.tick_params(axis='x',labelsize=9)
            plt.setp(ax.get_xticklabels(),rotation=25,ha='right',rotation_mode='anchor')
            ax.set_yticks(range(6),processes);ax.set_title((['Selected discovery','Standard IM'] if lang=='en' else ['Выбранная структура','Стандартный IM'])[j],fontsize=10)
            for pi,p in enumerate(processes):
                for wi,w in enumerate(worlds):
                    c=next(x for x in contrasts if x['process']==p and x['world']==w and x['structure']==['discovered','legacy_discovered'][j] and x['variant']=='main' and x['baseline']=='predictive')
                    sig=c['primary'] and (c['family_adjusted_difference']['high']<0 or c['family_adjusted_difference']['low']>0)
                    ax.text(wi,pi,f'{matrix[pi,wi]:+.1f}'+('*' if sig else ''),ha='center',va='center',fontsize=10,color='white' if abs(matrix[pi,wi])>.65*limit else 'black')
        bar=fig.colorbar(im,ax=axes,shrink=.8);bar.ax.tick_params(labelsize=9);bar.set_label('Cost reduction (%)' if lang=='en' else 'Снижение стоимости (%)',fontsize=9)
        fig.savefig(G/f'structural_matrix_{lang}.pdf',metadata={'Creator':'','Author':'','CreationDate':None,'ModDate':None});fig.savefig(G/f'structural_matrix_{lang}.png',dpi=170);plt.close(fig)
        lines=[]
        for p in processes:
            values=[get(p,'routing',m) for m in ['discovered_static','discovered_predictive','discovered_retained','heuristic','oracle']]
            lines.append(p+' & '+' & '.join(f"{r['normalized_cost']['mean']:.3f}" for r in values)+f" & {values[2]['normalized_regret']['mean']:.3f}"+r' \\')
        caption=('Routing feedback, selected discovered structure: mean per-fit cost divided by matched no-action cost. Regret is retained-load minus known-generator cost, normalized by no action. Each row contains 12 independent fits.' if lang=='en' else 'Routing feedback при выбранной обнаруженной структуре: стоимость каждого обученного варианта нормирована на соответствующую стоимость без вмешательства. Regret равен разности стоимости retained-load и планировщика с известным генератором, также нормированной на no action. Каждая строка содержит 12 независимых обучений.')
        text=r'\begin{table}[t]\caption{'+caption+r'}\label{tab:structures_results}\centering\small\setlength{\tabcolsep}{4pt}'+'\n'+r'\begin{tabular}{lrrrrrr}\toprule'+'\n'+('Process & Static & Predictive & Retained & Heuristic & Generator & Regret' if lang=='en' else 'Процесс & Static & Predictive & Retained & Heuristic & Generator & Regret')+r'\\\midrule'+'\n'+'\n'.join(lines)+'\n'+r'\bottomrule\end{tabular}\end{table}'+'\n'
        (G/f'structural_primary_{lang}.tex').write_text(text)
    snapshot={'analysis_inputs':{name:hashlib.sha256((A/name).read_bytes()).hexdigest() for name in ['summary.json','contrasts.json']},'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'matplotlib':matplotlib.__version__,'outputs':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in G.glob('structural_*') if p.suffix in {'.tex','.pdf','.png'} and 'supplement' not in p.name}}
    (PAPER/'structural_evidence_snapshot.json').write_text(json.dumps(snapshot,indent=2))
    print('rendered structural tables and matrix',G)
if __name__=='__main__':main()
