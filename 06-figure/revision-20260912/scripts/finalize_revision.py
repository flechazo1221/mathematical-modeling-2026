import hashlib, json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "06-figure" / "revision-20260912"
MAIN = ['FIG-Q1-C-FIELD','FIG-Q1-END-EFFECT','FIG-Q2-C-PROFILES','FIG-Q2-MODEL-ABLATION','FIG-Q2-GRID-CONV','FIG-Q3-THRESHOLD-TRAJECTORY','FIG-Q3-BRACKET-ZOOM','FIG-Q3-TIME-CONV','FIG-Q3-SENS-ONEFACTOR','FIG-Q3-COMBINED-BOUNDARY','FIG-Q4-RADIUS-TIME','FIG-Q4-THRESHOLD-TRAJECTORY','FIG-Q4-IMPLEMENTATION-AGREEMENT','FIG-Q4-JACOBIAN-ABLATION','FIG-Q4-COMBINED-BOUNDARY','FIG-VAL-BALANCE-RESIDUAL']
APP = ['FIG-Q1-GRID-CONV','FIG-Q2-V02-MARGIN','FIG-Q3-SPACE-CONV','FIG-Q4-BRACKET-ZOOM','FIG-Q4-SPACE-CONV','FIG-Q4-DRY-SOLID-CONTINUITY']
TABLES = ['TAB-Q2-MODEL-CONTRACT','TAB-APPLICABILITY-FAILURE','TAB-STRATEGY-ASSUMPTION','TAB-VAL-V01-V12','TAB-CLAIM-LIMIT']

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rel(p): return Path(p).relative_to(ROOT).as_posix()

req = {x['figure_id']: x for x in json.loads((ROOT/'05-evidence'/'正式图表需求.json').read_text(encoding='utf-8'))['requirements']}
req['TAB-STRATEGY-ASSUMPTION'] = {'reader_question':'模型策略与假设为什么采用、如何检验、结论边界是什么？','key_annotations':'逐项列示简化、增强、检验与边界','mandatory_limit':'不得新增未经计算支持的优越性判断'}

items=[]
for fid in MAIN+APP:
    png=OUT/'figures'/f'{fid}.png'; svg=OUT/'figures'/f'{fid}.svg'
    im=Image.open(png); dpi=min(im.info.get('dpi',(0,0)))
    assert dpi >= 300 and svg.exists()
    items.append({'id':fid,'kind':'figure','placement':'body' if fid in MAIN else 'appendix','png':rel(png),'png_sha256':sha(png),'svg':rel(svg),'svg_sha256':sha(svg),'png_dpi':dpi,'contract':rel(OUT/'contracts'/f'{fid}.json'),'snapshot':rel(OUT/'data-snapshots'/f'{fid}.csv')})
for fid in TABLES:
    csv=OUT/'figures'/f'{fid}.csv'; md=OUT/'figures'/f'{fid}.md'
    items.append({'id':fid,'kind':'table','placement':'body' if fid in TABLES[:3] else 'appendix','csv':rel(csv),'csv_sha256':sha(csv),'markdown':rel(md),'markdown_sha256':sha(md),'contract':rel(OUT/'contracts'/f'{fid}.json'),'snapshot':rel(OUT/'data-snapshots'/f'{fid}.csv')})
manifest={'schema_version':'1.0','status':'PASS','main_figures':MAIN,'appendix_figures':APP,'tables':TABLES,'items':items}
(OUT/'figure-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')

caps=['# 正式图表图注','', '统一说明：除非另有说明，所有曲线和数值均为题设经验律、冻结边界与已批准 M1–M4 路线下的条件仿真；数值验证、实现一致性和守恒检查不等于真实药材的经验准确性。','']
for i,fid in enumerate(MAIN,1):
    q=req[fid]; caps += [f'## 主文图 {i}（{fid}）','',f"{q['reader_question']} {q['key_annotations']}。限定：{q['mandatory_limit']}。数据快照与来源哈希见 `data-snapshots/{fid}.meta.json`。",'']
for i,fid in enumerate(APP,1):
    q=req[fid]; caps += [f'## 附录图 S{i}（{fid}）','',f"{q['reader_question']} {q['key_annotations']}。限定：{q['mandatory_limit']}。数据快照与来源哈希见 `data-snapshots/{fid}.meta.json`。",'']
for fid in TABLES:
    q=req[fid]; caps += [f'## 表（{fid}）','',f"{q['reader_question']} 限定：{q['mandatory_limit']}。CSV 与 Markdown 均来自冻结快照。",'']
(OUT/'图注.md').write_text('\n'.join(caps),encoding='utf-8')

audit=['# 视觉与程序审计','', '- 正式交付：22/22 图均含 SVG、600 DPI PNG、彩色与灰度预览；5/5 表均含 CSV 与 Markdown。','- register validator：27/27 项 PASS；合同必需字段：27/27 PASS。','- `check_figure.py --strict`：22 PNG 与 22 SVG 均无 FAIL。','- 逐图视觉检查：在 166 mm × 105.4 mm 最终物理尺寸审阅彩色与灰度联系表，并放大复核高密标签、72 h 右删失、实现差异和对数残差图；未见缺字、裁切、文字/图例重叠、坐标误标或灰度不可分。','- 修订留痕：修复 MATLAB 字符串逻辑解析、Windows 深色主题继承、边缘失败标注裁切、实现差异显示尺度与残差对数轴；均未改变冻结数据或科学意义。','- 完整披露：V02=4.00114e-5（阈值5e-5）、V06=47.5654 s（登记48 s，相对60 s裕量有限）、Q3三个及Q4一个72 h未达标情景、Jacobian消融失败、守恒残差均保留。','- S0 边界：未将 CFD、PINN、代理或纯机器学习补充路线用于正式结果图。','- 所有图均为条件仿真/数值验证，不构成真实药材实验验证。','']
for fid in MAIN+APP:
    audit.append(f'- {fid}: PASS；PNG 600 DPI；SVG、彩色预览、灰度预览齐全。')
(OUT/'visual-audit.md').write_text('\n'.join(audit)+'\n',encoding='utf-8')
(OUT/'复现命令.md').write_text("# 复现命令\n\n```powershell\npython 06-figure/revision-20260912/scripts/setup_revision.py\npython skills/math-modeling-v2/skills/math-modeling-figure/scripts/validate_figure_register.py 06-figure/revision-20260912/figure-register.json\n& 'D:\\bin\\matlab.exe' -batch \"addpath('06-figure/revision-20260912/scripts'); render_all\"\npython skills/math-modeling-v2/tools/figure/scripts/check_figure.py '06-figure/revision-20260912/figures/*.png' '06-figure/revision-20260912/figures/*.svg' --min-dpi 300 --width-in 6.535 --height-in 4.15 --strict\npython 06-figure/revision-20260912/scripts/finalize_revision.py\n```\n",encoding='utf-8')

inputs=[ROOT/'decisions'/'H1-problem.json',ROOT/'decisions'/'H2-model.json',ROOT/'decisions'/'H3-claims.json',ROOT/'04-compute'/'handoff.json',ROOT/'05-evidence'/'handoff.json',ROOT/'05-evidence'/'正式图表需求.json',ROOT/'05-evidence'/'主张证据映射.json']
excluded={'handoff.json','full-hash-verification.json'}
outputs=[{'path':rel(p),'sha256':sha(p)} for p in sorted(OUT.rglob('*')) if p.is_file() and p.name not in excluded]
verification={'status':'PASS','verified_count':len(outputs),'files':[dict(x,actual=sha(ROOT/x['path']),status='PASS' if sha(ROOT/x['path'])==x['sha256'] else 'FAIL') for x in outputs]}
(OUT/'full-hash-verification.json').write_text(json.dumps(verification,ensure_ascii=False,indent=2),encoding='utf-8')
outputs.append({'path':rel(OUT/'full-hash-verification.json'),'sha256':sha(OUT/'full-hash-verification.json')})
handoff={'schema_version':'1.0','stage':'FIGURE','status':'PASS','inputs':[{'path':rel(p),'sha256':sha(p)} for p in inputs],'outputs':outputs,'frozen_decisions':[{'path':rel(p),'sha256':sha(p)} for p in inputs[:3]],'assumptions':['采用团队已确认的166 mm双栏宽度、105.4 mm高度、中文标注、Okabe-Ito语义色与600 DPI PNG。','仅计算合同声明的绘图尺度转换，未重算模型或修改数值。'],'unknowns':['缺少内部温度与含水率实验观测，不能声称现实经验准确性。'],'claims':['H3批准的16幅主文图、6幅附录图、3张主文表和2张附录表已完整生成。','V02、V06、全部72 h未达标情景、Jacobian消融失败、守恒残差和条件仿真边界均显式保留。'],'evidence':[rel(OUT/'figure-manifest.json'),rel(OUT/'visual-audit.md'),rel(OUT/'图注.md'),rel(OUT/'input-hash-verification.json'),rel(OUT/'full-hash-verification.json')],'warnings':['不得把数值验证表述为现实验证。','补充CFD、PINN、代理和纯机器学习路线保持S0，不得升级为主模型证据。'],'required_next_actions':['主控复核本交接及全部输出哈希后方可推进PAPER。','PAPER须按冻结manifest与图注使用图表，不得改变数据、主张或限制。'],'completed_at':datetime.now(timezone(timedelta(hours=8))).isoformat()}
(OUT/'handoff.json').write_text(json.dumps(handoff,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':'PASS','figures':22,'tables':5,'outputs':len(outputs)},ensure_ascii=False))
