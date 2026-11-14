"""Verify published package bytes and regenerate numerical results in a fresh location."""
from pathlib import Path
import hashlib,json,sys,zipfile,subprocess,time,re

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
def main():
 packages=Path(sys.argv[1]).resolve();dest=Path(sys.argv[2]).resolve()
 if dest.exists():raise RuntimeError('Use an empty new verification directory')
 dest.mkdir(parents=True);index=json.loads((packages/'packages.json').read_text());checks=[];member_hashes={}
 for part in index:
  src=packages/part['file'];assert sha(src)==part['sha256'] and src.stat().st_size==part['bytes']
  target=dest/part['extract_to'];target.mkdir(parents=True,exist_ok=True)
  with zipfile.ZipFile(src) as z:
   for info in z.infolist():
    path=Path(info.filename);assert not path.is_absolute() and '..' not in path.parts
    output=target/path
    if info.is_dir():output.mkdir(parents=True,exist_ok=True);continue
    assert not output.exists(), 'Duplicate archive member: '+str(path)
    output.parent.mkdir(parents=True,exist_ok=True);h=hashlib.sha256()
    with z.open(info) as source,output.open('wb') as destination:
     for block in iter(lambda:source.read(1024*1024),b''):h.update(block);destination.write(block)
    member_hashes[str(output.relative_to(dest))]=h.hexdigest()
  checks.append(dict(file=part['file'],sha256=part['sha256']));print('extracted',part['file'],flush=True)
 manifest=json.loads((dest/'SHA256.json').read_text())
 for name,digest in manifest.items():assert member_hashes[name]==digest, name
 print('all extracted member hashes verified',len(manifest),flush=True)
 source_freeze=sha(dest/'structural/SOURCE_FREEZE.json')
 for file in (dest/'structural/main_v1').glob('*/PREPARED.json'):assert json.loads(file.read_text())['freeze_sha256']==source_freeze
 numeric=['structural/analysis/'+x for x in ['summary.json','per_fit.json','contrasts.json','aggregate.json','selector_per_fit.json','calibration_audits.json','model_quality.json','selector_summary.json','discovery_summary.json','hindsight_per_fit.json','structural_conformance.json','resource_summary.json','P4_process_outcomes.json','recovery_summary.json','trigger_support.json','full_summary.csv','selector_summary.csv']]+['selector/selector_results/summary.json','selector/selector_results/per_seed.json']
 figures=[str(x.relative_to(dest)) for x in (dest/'manuscript/generated').iterdir() if x.name.startswith(('structural_','operational_')) if x.suffix in {'.tex','.png','.pdf'}]
 before={name:sha(dest/name) for name in numeric+figures}
 jobs=[['structural/summarize.py'],['structural/report_diagnostics.py'],['structural/operational_report.py'],['structural/render_results.py'],['selector/selector_sensitivity.py','analyze']]
 for args in jobs:
  result=subprocess.run([sys.executable,*args],cwd=dest,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
  log=dest/('verification_'+Path(args[0]).stem+'.txt');log.write_text(result.stdout)
  if result.returncode:raise RuntimeError(result.stdout[-4000:])
  print('regenerated',args[0],flush=True)
 for name,digest in before.items():assert sha(dest/name)==digest, 'Reproduction mismatch: '+name
 terms=json.loads(Path(sys.argv[3]).read_text()) if len(sys.argv)>3 else []
 forbidden=re.compile('|'.join([r'/(?:home|Users)/[^/\s]+/',r'192\.168\.\d+\.\d+']+[re.escape(x) for x in terms]),re.I);bad=[]
 for src in dest.rglob('*'):
  if src.is_file() and src.suffix in {'.json','.md','.tex','.py','.cpp','.txt','.bib','.csv','.pnml','.log'}:
   if src.name.startswith('verification_'):continue
   if forbidden.search(src.read_text(errors='replace')):bad.append(str(src.relative_to(dest)))
 assert not bad, bad
 pdfs=[]
 for src in (dest/'manuscript').glob('*.pdf'):
  info=subprocess.check_output(['pdfinfo',str(src)],text=True)
  assert not re.search(r'^Author:[ \t]*\S+',info,re.M)
  txt=subprocess.check_output(['pdftotext',str(src),'-'],text=True)
  assert not forbidden.search(txt)
  pdfs.append(dict(file=str(src.relative_to(dest)),sha256=sha(src)))
 receipt=dict(status='passed',time=time.time(),packages=checks,members_verified=len(manifest),numeric_outputs_reproduced=numeric,figures_tables_reproduced=figures,pdfs=pdfs,anonymity_scan='passed',identity_terms_checked=len(terms),scope='Fresh extraction; original execution freeze linked to every preparation receipt; all package/member hashes checked; numerical analyses, selector diagnostics and manuscript tables/figures regenerated exactly. No new simulation or policy selection using test outcomes.')
 (packages.parent/'VERIFIED.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2),flush=True)
if __name__=='__main__':main()
