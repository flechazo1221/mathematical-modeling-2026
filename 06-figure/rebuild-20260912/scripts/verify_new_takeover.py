from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[3]; OUT=ROOT/'06-figure'/'rebuild-20260912'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
reg=json.loads((OUT/'figure-register.json').read_text(encoding='utf-8')); failures=[]
if len(reg.get('items',[]))!=27: failures.append('register count != 27')
for x in reg.get('items',[]):
    if x['evidence_class']=='quantitative' and x['generation']['tool']!='MATLAB': failures.append(f"{x['id']}: not MATLAB")
    for s in x['source_data']:
        p=s['path'].replace('\\','/')
        if p.startswith('06-figure/'): failures.append(f"{x['id']}: old figure dependency {p}")
        q=ROOT/p
        if not q.exists() or sha(q)!=s['sha256']: failures.append(f"{x['id']}: bad source hash {p}")
new_scripts=['prepare_from_compute.py','render_from_compute.m','verify_new_takeover.py','finalize_from_compute.py']
for n in new_scripts:
    if not (OUT/'scripts'/n).exists(): failures.append(f'missing new script {n}')
for forbidden in ['setup_revision.py','render_all.m','finalize_revision.py','build_publication_figures.py','finalize_figure_stage.py']:
    if (OUT/'scripts'/forbidden).exists(): failures.append(f'legacy script present {forbidden}')
report={'status':'PASS' if not failures else 'FAIL','generation':'NEW_PIPELINE_FROM_COMPUTE','registered_items':len(reg.get('items',[])),'matlab_quantitative_items':sum(x.get('generation',{}).get('tool')=='MATLAB' for x in reg.get('items',[])),'old_figure_dependencies':0 if not any('old figure' in x for x in failures) else None,'new_script_hashes':{n:sha(OUT/'scripts'/n) for n in new_scripts if (OUT/'scripts'/n).exists()},'failures':failures}
(OUT/'new-takeover-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False));raise SystemExit(bool(failures))
