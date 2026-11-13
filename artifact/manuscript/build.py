"""Compile manuscripts sequentially. Run under the owner's shared CPU gate."""
from pathlib import Path
import subprocess,sys,json,re
root=Path(__file__).resolve().parent
documents=sys.argv[1:] or ['paper_en','paper_ru','supplement_en','supplement_ru']
for document in documents:
    name='paper_'+document if document in ['en','ru'] else document
    assert name in ['paper_en','paper_ru','supplement_en','supplement_ru']
    lang=name.rsplit('_',1)[1]
    engine='pdflatex' if lang=='en' else 'xelatex'
    commands=[[engine,'-interaction=nonstopmode','-halt-on-error',name+'.tex'],['bibtex',name],
              [engine,'-interaction=nonstopmode','-halt-on-error',name+'.tex'],
              [engine,'-interaction=nonstopmode','-halt-on-error',name+'.tex']]
    for command in commands:
        p=subprocess.run(command,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors='replace')
        (root/(name+'_build_last.txt')).write_text(p.stdout)
        if p.returncode:
            print(p.stdout[-4500:]);raise SystemExit(p.returncode)
    subprocess.run(['pdftotext','-layout',name+'.pdf',name+'.txt'],cwd=root,check=True)
    log=(root/(name+'.log')).read_text(errors='replace')
    aux=(root/(name+'.aux')).read_text()
    print(name, re.findall(r'newlabel\{maintextend\}[^\n]*',aux))
    print('\n'.join(x for x in log.splitlines() if any(w in x for w in ['Overfull','undefined','Output written','Warning'])))
