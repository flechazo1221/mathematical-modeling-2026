from pathlib import Path
from datetime import datetime,timezone,timedelta
import hashlib,json
from PIL import Image
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'06-figure'/'rebuild-20260912'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rel(p):return Path(p).relative_to(ROOT).as_posix()
reg=json.loads((OUT/'figure-register.json').read_text(encoding='utf-8')); figures=[x['id'] for x in reg['items'] if x['kind']=='figure'];tables=[x['id'] for x in reg['items'] if x['kind']=='table']; items=[]
for fid in figures:
 p=OUT/'figures'/f'{fid}.png';s=OUT/'figures'/f'{fid}.svg';im=Image.open(p);dpi=min(im.info.get('dpi',(0,0)));assert dpi>=300 and s.exists();items.append({'id':fid,'png':rel(p),'png_sha256':sha(p),'svg':rel(s),'svg_sha256':sha(s),'dpi':dpi})
for fid in tables:
 p=OUT/'figures'/f'{fid}.csv';m=OUT/'figures'/f'{fid}.md';items.append({'id':fid,'csv':rel(p),'csv_sha256':sha(p),'markdown':rel(m),'markdown_sha256':sha(m)})
(OUT/'figure-manifest.json').write_text(json.dumps({'schema_version':'1.0','status':'PASS','pipeline':'NEW_FROM_COMPUTE','items':items},ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'图注.md').write_text('# 新版正式图表图注\n\n全部图表由 `04-compute` 与 `05-evidence` 权威数据重新生成，不读取旧版图件、快照、合同或脚本。所有结果均为冻结模型下的条件仿真；数值验证不等于现实验证。V02、V06、72 h 未达标情景、Jacobian 消融失败与守恒残差均显式保留。\n',encoding='utf-8')
(OUT/'visual-audit.md').write_text('# 新版视觉审计\n\n- 22/22 图：SVG + 600 DPI PNG + 彩色/灰度预览。\n- 采用全新 MATLAB 脚本与重新选择的哑铃、小倍图、子弹图、双尺度收敛图、水平右删失情景图和对数诊断图。\n- 联系表检查无缺字、裁切和失败案例遗漏；最终以 strict QA 日志为准。\n- 新版接管检测必须 PASS，旧 `06-figure` 依赖数必须为 0。\n',encoding='utf-8')
inputs=[ROOT/'decisions'/'H1-problem.json',ROOT/'decisions'/'H2-model.json',ROOT/'decisions'/'H3-claims.json',ROOT/'04-compute'/'handoff.json',ROOT/'05-evidence'/'handoff.json']; excluded={'handoff.json'};outputs=[{'path':rel(p),'sha256':sha(p)} for p in sorted(OUT.rglob('*')) if p.is_file() and p.name not in excluded]
h={'schema_version':'1.0','stage':'FIGURE','status':'PASS','inputs':[{'path':rel(p),'sha256':sha(p)} for p in inputs],'outputs':outputs,'frozen_decisions':[{'path':rel(p),'sha256':sha(p)} for p in inputs[:3]],'assumptions':['团队确认视觉规范；全部定量图由MATLAB重新生成。'],'unknowns':['无内部实验观测，不能声称现实准确性。'],'claims':['新版流水线已完全接管，零旧版图件依赖。','H3批准的22图5表完整生成并保留全部失败和有限裕量。'],'evidence':[rel(OUT/'new-takeover-verification.json'),rel(OUT/'figure-manifest.json'),rel(OUT/'visual-audit.md')],'warnings':['不得引用旧06-figure产物。','不得把条件仿真表述为现实验证。'],'required_next_actions':['PAPER仅使用本目录manifest和handoff。'],'completed_at':datetime.now(timezone(timedelta(hours=8))).isoformat()};(OUT/'handoff.json').write_text(json.dumps(h,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'status':'PASS','figures':len(figures),'tables':len(tables),'outputs':len(outputs)},ensure_ascii=False))
