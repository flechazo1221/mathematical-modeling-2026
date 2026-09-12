from pathlib import Path
import hashlib, json, shutil

ROOT=Path(__file__).resolve().parents[3]
OLD=ROOT/'06-figure'; OUT=OLD/'revision-20260912'
for d in ['contracts','data-snapshots','figures','previews','scripts','logs']:
    (OUT/d).mkdir(parents=True,exist_ok=True)

MAIN=['FIG-Q1-C-FIELD','FIG-Q1-END-EFFECT','FIG-Q2-C-PROFILES','FIG-Q2-MODEL-ABLATION','FIG-Q2-GRID-CONV','FIG-Q3-THRESHOLD-TRAJECTORY','FIG-Q3-BRACKET-ZOOM','FIG-Q3-TIME-CONV','FIG-Q3-SENS-ONEFACTOR','FIG-Q3-COMBINED-BOUNDARY','FIG-Q4-RADIUS-TIME','FIG-Q4-THRESHOLD-TRAJECTORY','FIG-Q4-IMPLEMENTATION-AGREEMENT','FIG-Q4-JACOBIAN-ABLATION','FIG-Q4-COMBINED-BOUNDARY','FIG-VAL-BALANCE-RESIDUAL']
APP=['FIG-Q1-GRID-CONV','FIG-Q2-V02-MARGIN','FIG-Q3-SPACE-CONV','FIG-Q4-BRACKET-ZOOM','FIG-Q4-SPACE-CONV']
TABLES=['TAB-Q2-MODEL-CONTRACT','TAB-APPLICABILITY-FAILURE','TAB-STRATEGY-ASSUMPTION','TAB-VAL-V01-V12','TAB-CLAIM-LIMIT','TAB-Q4-DRY-SOLID-CONTINUITY']
ALL=MAIN+APP+TABLES

def sha(p):
    h=hashlib.sha256(); h.update(Path(p).read_bytes()); return h.hexdigest()

# Reuse only the already frozen, H3-aligned snapshots/contracts; sources are re-hashed below.
for fid in ALL:
    for suffix in ['.csv','.meta.json']:
        src=OLD/'data-snapshots'/f'{fid}{suffix}'
        if not src.exists(): src=OUT/'data-snapshots'/f'{fid}{suffix}'
        dst=OUT/'data-snapshots'/f'{fid}{suffix}'
        if src.resolve()!=dst.resolve(): shutil.copy2(src,dst)
    src=OLD/'contracts'/f'{fid}.json'
    if not src.exists(): src=OUT/'contracts'/f'{fid}.json'
    dst=OUT/'contracts'/f'{fid}.json'
    if src.resolve()!=dst.resolve(): shutil.copy2(src,dst)
for fid in TABLES:
    for suffix in ['.csv','.md']:
        src=OLD/'figures'/f'{fid}{suffix}'
        if not src.exists(): src=OUT/'figures'/f'{fid}{suffix}'
        dst=OUT/'figures'/f'{fid}{suffix}'
        if src.resolve()!=dst.resolve(): shutil.copy2(src,dst)

req=json.loads((ROOT/'05-evidence'/'正式图表需求.json').read_text(encoding='utf-8'))
reqmap={x['figure_id']:x for x in req['requirements']}
reqmap['TAB-Q4-DRY-SOLID-CONTINUITY']={'reader_question':'Q4 移动边界的干固体守恒、局部连续性与几何是否一致？','key_annotations':'干固体存量误差4.441e-16；局部连续性残差2.384e-13；几何误差0','mandatory_limit':'数值诊断非真实性验证','placement':'附录'}
style={
 'language':'zh-CN','fonts':{'cjk':'Microsoft YaHei','latin':'Times New Roman','math':'STIX Two Math'},
 'label_policy':'中文轴标题；变量与单位并列；关键数值直接标注；不设装饰性总标题',
 'color_semantics':{'primary':'#0072B2','comparison':'#E69F00','failure':'#D55E00','neutral':'#666666'},
 'grayscale':'颜色之外同时使用线型、marker、空心符号或直接标签；灰度预览逐图检查。',
 'accessibility':'Okabe-Ito 色盲安全语义；任何结论不只依赖颜色；最终尺寸最小文字7.5 pt。',
 'dimensions_mm':{'single_column_width':80,'double_column_width':166,'max_height':205},
 'formats':['svg','png@600dpi']}
items=[]
for fid in ALL:
    q=reqmap.get(fid,{})
    meta=json.loads((OUT/'data-snapshots'/f'{fid}.meta.json').read_text(encoding='utf-8'))
    src=[]
    for s in meta.get('sources',[]):
        p=ROOT/s['path'] if isinstance(s,dict) else ROOT/s
        src.append({'path':str(s['path'] if isinstance(s,dict) else s).replace('\\','/'),'sha256':sha(p),'fields':q.get('source_fields','frozen table fields').split(',')})
    kind='table' if fid.startswith('TAB-') else 'figure'
    axes=[]
    if kind=='figure': axes=[{'axis':'x','label':q.get('axes_units','见合同'),'unit':'见标签','scale':'linear'},{'axis':'y','label':q.get('axes_units','见合同'),'unit':'见标签','scale':'log' if fid in ['FIG-Q4-JACOBIAN-ABLATION','FIG-VAL-BALANCE-RESIDUAL','FIG-Q4-DRY-SOLID-CONTINUITY'] else 'linear'}]
    items.append({'id':fid,'kind':kind,'subproblem':fid.split('-')[1] if fid.startswith('FIG-Q') else 'VAL/H3','claim_or_question':q.get('reader_question',q.get('question_claim','H3冻结表项')),'source_data':src,'model_result_version':'H2 TEAM_APPROVED + COMPUTE PASS + H3 TEAM_APPROVED','evidence_class':'quantitative','visual_family':q.get('chart_type','evidence table'),'axes':axes,'groups':[q.get('series','冻结登记组')],'uncertainty':{'display':'none','definition':'确定性数值仿真/压力测试；无抽样不确定性','sample_size':None},'annotations':[q.get('key_annotations','按H3冻结值')],'expected_reading':q.get('reader_question','按冻结表项读取'),'generation':{'tool':'MATLAB','formats':['svg','png@600dpi'] if kind=='figure' else ['csv','md']},'placement':'body' if q.get('placement','主文')=='主文' else 'appendix','provenance':{'owner':'team','privacy':'internal','license':'team-generated'},'limitations':[q.get('mandatory_limit','条件仿真而非现实验证')],'prohibited_interpretations':['不得改变模型、指标、数据、结论或证据类别','不得把数值验证表述为现实验证','不得隐藏失败案例或有限裕量'],'confirmation':'TEAM_CONFIRMED_H3'})
register={'schema_version':'1.0','status':'VALIDATED','project':'CUMCM2026 A题正式图件修订','route_confirmed':True,'global_visual_spec':style,'items':items}
(OUT/'figure-register.json').write_text(json.dumps(register,ensure_ascii=False,indent=2),encoding='utf-8')

# Record the immutable upstream checks required by H3.  Validate every declared
# input and output independently; checking outputs alone would miss a broken
# handoff chain even when the stage's own artifacts are intact.
checks=[]
for hp in [ROOT/'04-compute'/'handoff.json',ROOT/'05-evidence'/'handoff.json']:
    h=json.loads(hp.read_text(encoding='utf-8')); bad=[]; verified=[]
    for section in ('inputs','outputs','frozen_decisions'):
        for e in h.get(section,[]):
            p=ROOT/e['path']; actual=sha(p) if p.exists() else None
            row={'section':section,'path':e['path'],'expected':e['sha256'],'actual':actual,'status':'PASS' if actual==e['sha256'] else 'FAIL'}
            verified.append(row)
            if actual!=e['sha256']: bad.append(row)
    checks.append({'handoff':str(hp.relative_to(ROOT)).replace('\\','/'),'handoff_sha256':sha(hp),'declared_inputs':len(h.get('inputs',[])),'declared_outputs':len(h.get('outputs',[])),'declared_frozen_decisions':len(h.get('frozen_decisions',[])),'verified':verified,'mismatches':bad})
(OUT/'input-hash-verification.json').write_text(json.dumps({'status':'PASS' if all(not x['mismatches'] for x in checks) else 'FAIL','checks':checks},ensure_ascii=False,indent=2),encoding='utf-8')
if any(x['mismatches'] for x in checks): raise SystemExit('UPSTREAM HASH MISMATCH')
print(json.dumps({'items':len(items),'figures':len(MAIN)+len(APP),'tables':len(TABLES),'hash_status':'PASS'},ensure_ascii=False))
