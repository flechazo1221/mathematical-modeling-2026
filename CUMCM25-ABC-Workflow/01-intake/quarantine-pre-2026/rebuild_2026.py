from pathlib import Path
import ast,json,hashlib,math,statistics,zipfile,datetime
import openpyxl
from pypdf import PdfReader
OUT=Path(__file__).resolve().parent; ROOT=OUT.parent
old=(OUT/'build_intake.py').read_text(encoding='utf-8')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p): return {'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p)}
def write(n,s): (OUT/n).write_text(s,encoding='utf-8')
def dump(n,o): write(n,json.dumps(o,ensure_ascii=False,indent=2)+'\n')
# Old content is diagnostic only. Reuse reviewed decomposition and profiling logic, not old state or rules.
history=OUT/'quarantine-pre-2026'; history.mkdir(exist_ok=True)
for p in list(OUT.iterdir()):
 if p.is_file() and p.name not in ['rebuild_2026.py']:
  dest=history/p.name
  if not dest.exists(): p.replace(dest)
old=(history/'build_intake.py').read_text(encoding='utf-8')
inputs=[ROOT/'decisions/H0-selection.json',ROOT/'.workflow/config.json']+sorted((ROOT/'00-selection').glob('*'))+[ROOT/'input/B题/B题.pdf']+sorted((ROOT/'input/B题/附件').glob('*.xlsx'))
assert len(inputs)==12
h0=json.loads(inputs[0].read_text(encoding='utf-8-sig')); assert h0['status']=='TEAM_APPROVED' and h0['selected_options']==['B'] and h0['confirmed_by']==['队长']
up=json.loads((ROOT/'00-selection/handoff.json').read_text(encoding='utf-8-sig'))
for x in up['outputs']: assert sha(ROOT/x['path'])==x['sha256']
# Fresh read of original PDF and spreadsheets. No inherited data conclusions.
exec(old[old.index('pages=PdfReader'):old.index("inventory={'schema_version'")])
inventory={'schema_version':'1.0','inputs':[{**ref(p),'size_bytes':p.stat().st_size,'type':p.suffix} for p in inputs],'pdf_pages':len(pages),'profiles':profiles,'all_four_wavenumber_grids_identical':True,'upstream_output_hashes_verified':True,'raw_inputs_modified':False,'independent_wafer_count':{'SiC':1,'Si':1},'quarantine':'quarantine-pre-2026 excluded from current handoff; not approved input'}
dump('附件清单.json',inventory)
exec(old[old.index('specs=['):old.index("('C12','official'")]+']\n')
cons += [
('C12','official','R2条1–11','2026格式及提交要求','A4; margins_cm>=2.5; abstract_pages<=1 in_principle; body_pages<=30; no_TOC; appendix_complete_code; anonymous; electronic_first_page=abstract; single_PDF_or_Word; paper_bytes<=20000000; support_ZIP_or_RAR_bytes<=20000000','hard','已核验；20MB按20,000,000字节保守验收，摘要超页需人工确认；附录不限页'),
('C13','official','R3条2–6','团队主导核心建模分析；AI逐项人工核验、声明、详情','declaration_before_references; support contains AI工具使用详情.pdf; details has model,purpose,prompt_process,adoption,manual_modification,verification; human_review_each_item','hard','规则已核验；人工复核待完成，不能由机器PASS替代'),
('C14','official','R1条3–6；R2条8','赛时独立完成与交流平台禁令；学校赛区未知','during_contest: no_external_guidance and no_browse_publish_discuss_problem_on_communication_platforms; regional_school_requirements=UNVERIFIED','hard','全国规则明确；赛区学校附加要求未形式化，待队长核验')]
exec(old[old.index('constraints=[]'):old.index("for id,content,rule,acceptance in")])
for id,content,rule,check in [
('S1','匿名电子论文：摘要专页原则一页，正文无目录且不超过30页；附录不限页，完整可运行代码与材料列表','C12','单PDF或Word，建议PDF，<=20MB；不含承诺书/编号页；与纸本一致'),
('S2','匿名支撑ZIP/RAR：代码、外部数据及必要中间材料，原题数据可不重复','C12','<=20MB；清单进入附录；不含承诺书/编号页'),
('S3','纸质A4论文及专用页','C12','四边距至少2.5cm；承诺书/编号页另按纸质顺序；摘要起页脚中部连续页码'),
('S4','参考文献之前的AI工具使用声明及支撑材料AI工具使用详情.pdf','C13','工具/模型、用途环节、主要提示与过程、采纳/人工修改/核验可追溯'),
('S5','赛区/学校附加要求及正式专用页核验记录','C14','队长提交明确来源；当前未核验')]:
 deliverables.append(dict(id=id,question_ids=[],official_rule=rule,content=content,format=content,limit=check,acceptance=check,conditional=False))
exec(old[old.index('known=['):old.index("dump('赛题结构化说明.json',structure)")])
known[3]['statement']='12项指定输入的大小、类型、SHA-256和重新审计字段详见附件清单；旧材料隔离，不是已批准阶段产物。'
known[4].update(source='官方规则与AI合规.md:R1/R2/R3',evidence_type='2026全国官方网页直接核验',statement='2025题目+2026规则；参赛、格式、AI三项全国规定适用，赛区学校未知。')
structure['compliance_year']=2026
structure['precedence']='最新用户基线覆盖config.year及00-selection中的旧合规推断；H0只批准B题。'
structure['problem']['decomposition_note']='3主问：Q1.1；Q2.1–Q2.3；Q3.1–Q3.9（其中Q3.7隐式触发判断、Q3.8–Q3.9条件显式）；I1–I2为跨问支持，共15项。'
structure['rule_sources']=[{'id':'R1','url':'https://www.mcm.edu.cn/html_cn/node/9d8e511fe7a1447b35f53a82c908e2e0.html','published':'2026-03-03','effective':'2026-03-01'},{'id':'R2','url':'https://www.mcm.edu.cn/html_cn/node/4cd596519c9eb9fbd866398f6df0caa3.html','published':'2026-03-03','effective':'2026-03-03'},{'id':'R3','url':'https://www.mcm.edu.cn/html_cn/node/fef94648f2836ab6cc81586f4c38512b.html','published':'2026-08-03','effective':'2026-09-01'}]
for r in structure['rule_sources']: r.update(verified_on='2026-09-05',applicability='APPLICABLE_BY_USER_BASELINE')
dump('赛题结构化说明.json',structure)
exec(old[old.index("lines=['# B题数据审计报告'"):old.index("write('官方规则与AI合规.md'")])
p=OUT/'数据审计报告.md'; s=p.read_text(encoding='utf-8'); s=s[:s.index('复现：')]+ '复核由本目录rebuild_2026.py重读原题附件执行；当前已完成数据审计与输入输出哈希检查。旧规则结论未继承。\n'; p.write_text(s,encoding='utf-8')
write('官方规则与AI合规.md','''# 2025题目 + 2026全国规则

核验日期：2026-09-05。适用状态：按用户明确要求统一执行2026全国组委会规定。config.year=2025仅保留为题目年份；00-selection旧合规判断排除，不修改上游文件。旧01-intake产物在quarantine-pre-2026隔离，不进入PASS交接。

R1：[参赛规则（2026年修订稿）](https://www.mcm.edu.cn/html_cn/node/9d8e511fe7a1447b35f53a82c908e2e0.html)，2026-03-03发布，2026-03-01试行。直接核验条3–6、10：赛时不得接受队外指导或讨论，不得在交流平台浏览、发布或讨论赛题；引用公开成果须规范标注。AI可以辅助，队伍承担原创性、真实性、准确性责任。

R2：[论文格式规范（2026年修订稿）](https://www.mcm.edu.cn/html_cn/node/4cd596519c9eb9fbd866398f6df0caa3.html)，2026-03-03发布并试行。条1–11已核验：A4，四边距至少2.5cm；摘要专用页含标题关键词原则一页，从摘要起连续阿拉伯页码居页脚中部；正文无目录且不超过30页，附录页数不限。附录须有全部完整可运行代码及支撑材料列表。电子论文单一PDF或Word，建议PDF，不压缩且不超过20MB，第一页为摘要，不含承诺书/编号页。支撑材料为单一ZIP/RAR且不超过20MB，含代码、自查外部数据及必要中间材料（题目原始数据除外），不含承诺书/编号页。摘要正文附录及支撑文件匿名；电子内容格式与纸本一致。纸本按规范保留承诺书、编号页。字号字体行距颜色全国未统一规定。机器验收文件大小采用不超过20,000,000字节的保守界限。

R3：[人工智能工具使用规定（2026年试行）中文官方全文](https://www.mcm.edu.cn/html_cn/node/fef94648f2836ab6cc81586f4c38512b.html)，2026-08-03发布，2026-09-01试行；已从全国官网章程及规则栏目确认其入口，并与[英文官方全文](https://www.mcm.edu.cn/html_en/node/532f38e63cfa84145697e2678575ba0a.html)核对。条2–6要求核心建模与分析由队伍主导，AI参与内容逐项人工审查核实；参考文献之前设置“AI工具使用声明”。使用AI时支撑材料必须含“AI工具使用详情.pdf”，记录名称版本或模型、目的环节、主要提示方式与过程，以及采纳、人工修改和核验情况（语言润色例外依原文执行）。不得隐瞒或虚假声明。中文提交采用中文官方文件名；英文名称为相应译名，未发现实质冲突。2026规定替代与其不一致的旧规定；不沿用旧的逐处AI标注和工具参考文献作为2026新增硬要求。

赛区、学校、校内期限、提交平台细节及专用页下载版本未知，待队长核验。全国正式网页含附件入口，当前未下载模板，不宣称模板已验证。以上PASS仅指INTAKE资料准备，不表示论文已提交合规或人工核验已完成。

实际AI记录：Codex执行规则核验、题面提取、附件描述审计、问题拆解、方法筛选及交接检查；没有厚度求解或专业文献搜索。使用日期2026-09-05。模型精确标识由主控依任务元数据补记，不猜测。主要提示要求为固定B题、2026规则、仅写01-intake、H1停止；AI生成了本交付包。采纳、人工修改、逐项核验尚待队长记录。主控在其写入权限内更新真实AI日志，本任务未写.workflow。
''')
write('H1-选择包.md','''# H1中立选择包（待队长决定）

已冻结：2025 B题，2026全国规则；不得换题。INTAKE准备完成，不是团队批准。三主问细分15项，完整输出/约束/双向对应见结构化JSON与矩阵。没有求厚度或选择最终算法。

目标：以一次反射透射的两束干涉作为可解释比较基线；回答SiC厚度与可靠性，再回答多光束必要条件、精度影响、Si诊断/模型/算法/结果，以及SiC存在且影响精度时的修正和结果。不能用Si结果替代SiC验证。

请队长逐项批准、修改或退回以下问题定义；可组合选项，不涉及最终模型冻结。

|决策项|选项及取舍|AI非约束性建议|
|---|---|---|
|子问题边界|保留15项验收；或合并写作小节但保留每项验收|保留独立验收避免遗漏第3问条件任务|
|异常测量|原样保留加标记；或原样基线与有依据掩码成对敏感性|后者有利于发现异常影响，但须保留原值且暂不删点|
|折射率缺口|后续取得适用材料/波段参数后报告物理厚度；或先保留符号/参数区间分析|两者可顺序衔接；光学厚度仅中间量，不替代最终题目结果|
|多光束结论|存在/未获支持/证据不足三态；或二态但明确无法判定出口|三态，避免把证据不足说成不存在|
|可靠性口径|跨角/跨窗口/参数敏感性+合成恢复；若有独立真值再评准确度|先区分内部一致性与真实准确度；共享厚度拟合不作为独立跨角证明|
|修正触发|机制证据且厚度影响得到支持才修正；否则说明不触发或证据不足|遵循题面条件句；不保证消除所有误差|
|增量改进|按明确物理缺陷逐步改进；或先比较多个可识别机理候选|均保留简单基线并以可验证增益筛选，最终路线待H2|

最低可信基线是未来的受限两束相位/条纹间距方案，n保留符号或经核验外部约束，先独立角度分析。若相位/吸收/色散不可忽略，基线应标示失效域；不能任取常数折射率或挑选漂亮波段。详细推导、峰算法、参数界与阈值留DESIGN/原型/H2。

错误成本尚无数值：误报多光束会增加冗余参数；漏报会留下系统误差；强制删点会损失真实结构；把残差改善称为真实精度提升会形成不可信测试结论。队长需确认相对优先级，量化容忍差异、证据阈值与参数边界应在比较前固定，不从最终结果倒推。未确认的硬物理界已在矩阵标记，不能当作已满足。

后续验证/失败：检查量纲与退化极限，已知参数合成恢复，连续波段与双角稳定性，异常处理成对对照，参数可识别性及结构残差。若等价参数族、缺失必要光学参数、条纹不足或替代解释不能排除，返回条件范围/不可识别，不强行唯一值。没有真值时不得报告认证准确度、泛化准确率或确定偏差方向。

拒绝无标签监督学习、无时间目标预测、无排名需求综合评价、以聚类直接识别物理机制等不匹配方法。色散修正、复杂传播、稳健反演均为候选，必须说明解决的缺陷及可证伪增益，不能为复杂而复杂。

队长还需核验赛区学校附加规则并逐项审查AI产物；本次未代签或记录人工核验完成。H1批准由团队在其权限内记录；H1批准后主控进入等待用户文献阶段，不能直接进入DESIGN。本任务在H1停止。
''')
# Validate contracts, mapping, hashes and boundaries without fitting any thickness model.
qs={q['id'] for q in questions}; ds={d['id']:d for d in deliverables}; cs={c['id'] for c in constraints}
assert len(qs)==15 and {q['parent'] for q in questions}=={'1','2','3','cross'}
for q in questions:
 assert all(c in cs for c in q['constraint_ids'])
 assert all(q['id'] in ds[d]['question_ids'] for d in q['deliverable_ids'])
 assert all(r['question_id'] in qs for r in q['relationships'])
 assert all(q[k] for k in ['data_basis','baseline','validation_path','failure_condition','rejected_families'])
for d in deliverables: assert d.get('question_ids') or d.get('official_rule') in cs
for c in constraints: assert c['formal_check'] or '未形式化' in c['status']
required=['赛题结构化说明.json','附件清单.json','数据审计报告.md','问题方法约束矩阵.md','官方规则与AI合规.md','H1-选择包.md']
outputs=[OUT/n for n in required]+[OUT/'题面文本.txt',OUT/'rebuild_2026.py']
h={'schema_version':'1.0','stage':'INTAKE','status':'PASS','inputs':[ref(p) for p in inputs],'outputs':[ref(p) for p in outputs],'frozen_decisions':[ref(inputs[0])],'assumptions':['2025题目+2026全国规则，最新用户指令覆盖旧规则推断。','旧01-intake产物仅诊断，已隔离且不在当前outputs中。'],'unknowns':['材料适用折射率、吸收、掺杂、温度、仪器校准与真值缺失。','数值容忍度及赛区学校附加要求待队长核验。','AI逐项人工核验与采纳决定待完成。'],'claims':['15项问题及支持任务双向映射通过。','四工作簿重新只读审计完成，未进行厚度求解。','2026全国三项官方规则已直接核验，未发现实质冲突。'],'evidence':['附件清单.json记录原始输入SHA-256与逐行异常。','问题方法约束矩阵.md记录基线、证据、约束、验证与失败条件。'],'warnings':['PASS仅表示INTAKE准备通过，不是H1批准或提交合规完成。','无厚度真值，内部一致性不能替代真实准确度。','上游选择材料旧合规结论排除；config年份只解释为题目年份。'],'required_next_actions':['在H1由队长审查并记录选择；本任务停止。','H1批准后主控等待用户提供文献，再进入LITERATURE；不得跳入DESIGN。','主控依真实任务元数据补记AI日志并组织逐项人工核验。'],'completed_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()}
for x in h['inputs']+h['outputs']+h['frozen_decisions']:
 p=(ROOT/x['path']).resolve(); assert p.is_relative_to(ROOT.resolve()) and p.is_file() and sha(p)==x['sha256']
assert set(h)=={'schema_version','stage','status','inputs','outputs','frozen_decisions','assumptions','unknowns','claims','evidence','warnings','required_next_actions','completed_at'}
dump('handoff.json',h)
print(json.dumps({'status':'PASS','questions':len(questions),'profiles':[(p['path'],p['data_rows'],p['above_100_count'],p['zero_count']) for p in profiles],'outputs':len(outputs),'hashes_verified':True},ensure_ascii=False))
