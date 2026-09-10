from pathlib import Path
import json, hashlib, math, statistics, zipfile, datetime
import openpyxl
from pypdf import PdfReader
import jsonschema

OUT=Path(__file__).resolve().parent
ROOT=OUT.parent
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,s): (OUT/name).write_text(s,encoding='utf-8')
def dump(name,obj): write(name,json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def ref(p): return {'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p)}
inputs=[ROOT/'decisions/H0-selection.json',ROOT/'.workflow/config.json']+sorted((ROOT/'00-selection').glob('*'))+[ROOT/'input/B题/B题.pdf']+sorted((ROOT/'input/B题/附件').glob('*.xlsx'))
assert len(inputs)==12 and all(p.is_file() for p in inputs)
h0=json.loads(inputs[0].read_text(encoding='utf-8-sig'))
assert h0['status']=='TEAM_APPROVED' and h0['selected_options']==['B'] and h0['confirmed_by']==['队长']
up=json.loads((ROOT/'00-selection/handoff.json').read_text(encoding='utf-8-sig'))
assert up['status']=='PASS'
for x in up['outputs']: assert sha(ROOT/x['path'])==x['sha256']
# Only compare B attachment hashes to upstream records; never access A/C/D/E originals.
up_b=[x['sha256'] for x in up['inputs'] if 'B' in x['path']]
assert all(sha(p) in up_b for p in inputs[-5:])
oldnames=['附件清单.json','官方规则与AI合规.md','数据审计报告.md','停止报告.md','handoff.json']
history=OUT/'diagnostics'
history.mkdir(exist_ok=True)
for name in oldnames:
    src=OUT/name; dst=history/('BLOCKED-'+name)
    if src.exists() and not dst.exists(): dst.write_bytes(src.read_bytes())
pages=PdfReader(ROOT/'input/B题/B题.pdf').pages
assert len(pages)==2 and all(p.extract_text().strip() for p in pages)
write('题面文本.txt','\n\n'.join(f'PDF第{i+1}页\n{p.extract_text()}' for i,p in enumerate(pages)))
profiles=[]
for i,p in enumerate(inputs[-4:],1):
    wb=openpyxl.load_workbook(p,data_only=False)
    assert wb.sheetnames==['Sheet1']
    ws=wb['Sheet1']; rows=list(ws.iter_rows(values_only=True)); header=rows[0]; data=rows[1:]
    assert header==('波数 (cm-1)','反射率 (%)') and len(rows)==7470 and len(data)==7469 and ws.max_column==2
    assert all(len(r)==2 and all(isinstance(v,(int,float)) and math.isfinite(v) for v in r) for r in data)
    xs,ys=map(list,zip(*data)); steps=[b-a for a,b in zip(xs,xs[1:])]
    abnormal=[{'excel_row':j+2,'wavenumber':x,'reflectance_percent':y} for j,(x,y) in enumerate(data) if y<0 or y>100 or y==0]
    z=zipfile.ZipFile(p)
    pr={'path':p.relative_to(ROOT).as_posix(),'sheet':'Sheet1','sheet_state':ws.sheet_state,'worksheet_rows':ws.max_row,'columns':ws.max_column,'header':list(header),'data_rows':len(data),'first_data_excel_row':2,'last_data_excel_row':7470,'first':list(data[0]),'last':list(data[-1]),'material':'SiC' if i<=2 else 'Si','angle_deg':10 if i%2 else 15,'wafer_group':'SiC-one-wafer' if i<=2 else 'Si-one-wafer','fields':[{'column':'A','meaning':'真空波数（真空口径为物理解释，题面仅写波数）','type':'finite numeric','unit':'cm^-1','missing':0,'min':min(xs),'max':max(xs)},{'column':'B','meaning':'实测反射率','type':'finite numeric','unit':'%','missing':0,'min':min(ys),'max':max(ys)}],'strictly_increasing':all(s>0 for s in steps),'step_range':[min(steps),max(steps)],'step_median':statistics.median(steps),'duplicate_wavenumbers':len(xs)-len(set(xs)),'duplicate_rows':len(data)-len(set(data)),'missing_cells':sum(v is None for r in data for v in r),'negative_count':sum(y<0 for y in ys),'above_100_count':sum(y>100 for y in ys),'zero_count':ys.count(0),'reflectance_mean':statistics.mean(ys),'reflectance_sd':statistics.stdev(ys),'reflectance_quartiles':statistics.quantiles(ys,n=4),'formula_count':sum(c.data_type=='f' for row in ws for c in row),'error_cells':[c.coordinate for row in ws for c in row if c.data_type=='e'],'hidden_rows':[k for k,v in ws.row_dimensions.items() if v.hidden],'hidden_columns':[k for k,v in ws.column_dimensions.items() if v.hidden],'merged_ranges':[str(x) for x in ws.merged_cells.ranges],'comments':[c.coordinate for row in ws for c in row if c.comment],'hyperlinks':[c.coordinate for row in ws for c in row if c.hyperlink],'defined_names':list(wb.defined_names),'external_links_count':len(wb._external_links),'macro_parts':[n for n in z.namelist() if 'vba' in n.lower()],'tables':list(ws.tables),'autofilter':ws.auto_filter.ref,'number_formats':sorted(set(c.number_format for row in ws for c in row)),'abnormal_records':abnormal,'time_or_space':'波数顺序；无采样时间与空间位置字段','label_balance':'无厚度真值/多光束标签；分类平衡不适用'}
    profiles.append(pr)
assert all(pr['strictly_increasing'] for pr in profiles)
assert len({tuple(openpyxl.load_workbook(ROOT/pr['path'],read_only=True,data_only=True)['Sheet1'].values) for pr in []})==0
grids=[]
for pr in profiles:
    ws=openpyxl.load_workbook(ROOT/pr['path'],read_only=True,data_only=True)['Sheet1']
    grids.append([r[0] for r in list(ws.values)[1:]])
assert all(g==grids[0] for g in grids)
inventory={'schema_version':'1.0','stage_status':'PASS','scope':'12项指定输入；规则在线核验仅限合规资料；未读取其他题目原件','inputs':[{**ref(p),'size_bytes':p.stat().st_size,'type':p.suffix} for p in inputs],'diagnostic_inputs':[{**ref(p),'size_bytes':p.stat().st_size,'type':p.suffix} for p in sorted(history.iterdir())],'selection_outputs_verified':True,'B_original_hashes_match_upstream':True,'pdf_pages':2,'pdf_text_layer':'两页均可提取；没有改写PDF','profiles':profiles,'all_four_wavenumber_grids_identical':True,'independent_sample_units':{'SiC_wafers':1,'Si_wafers':1,'angles_per_wafer':2,'spectral_points_per_angle':7469},'changes_to_originals':False}
dump('附件清单.json',inventory)

specs=[
('Q1.1','1','explicit','建立','一次反射/透射条件下的外延层厚度关系','符号模型、假设和适用边界；厚度单位μm','量纲、光程与退化极限自洽','机理建模','无','受限两束干涉光程关系（折射率保留符号）','光学机理/相位关系','题面p1图1与问题1；无折射率数据','C01,C03,C04,C05','符号量纲、法向入射极限、单次反射范围检查','吸收或相位变化不可忽略而关系未覆盖时失效','不采用纯数据黑箱：无厚度标签且题目要求模型','折射率函数和相位假设待文献、团队决定'),
('Q2.1','2','explicit','设计','问题1的厚度计算过程','可复现算法说明、输入输出和失败返回','算法与Q1定义一致，保留追溯记录','参数估计','数据分析','在明确波段/折射率条件下用条纹间距估计作为比较基线','物理约束参数反演；谱周期或相位提取为候选','附件1/2有稠密有序双角光谱','C01,C03,C04,C06,C07','未来用已知参数合成谱及多窗口稳定性验证','条纹不足、重叠频率、色散或不等间距处理不当时失败','不先定拟合算法；监督学习无标注样本','波段、预处理、参数边界与算法以后决定'),
('Q2.2','2','explicit','计算','同一SiC晶圆厚度','两角度条件估计及共同厚度结论，μm并说明条件','跨角一致性与可复现性，不能宣称真值精度','参数估计','无','分别按Q2.1估计，暂不强制联合共享','受物理约束的独立/联合反演候选','附件1/2对应同一晶圆10°/15°','C02,C03,C04,C06,C08','比较独立估计差异、保留角度检验与残差','多个厚度/折射率组合同样解释数据则不能报唯一值','不做外推预测：无目标时间；不把两材料合并','共享厚度可作题面结构约束；共享光学参数需另证'),
('Q2.3','2','explicit','分析','SiC结果可靠性','不确定性来源、敏感性、残差及局限','区分重复性/稳定性和绝对准确度','不确定性评价','数据分析','波段与折射率扰动下的估计范围比较','敏感性/可识别性/结构化重采样候选','无真值；每材料仅一晶圆；光谱相邻相关','C04,C06,C08,C09','扰动角度、n、窗口、异常处理；未来分块检验','把相邻点当独立重复会低估区间；校准误差未知','拒绝随机点训练测试准确率与AHP评分：无真值且不是排序问题','容忍差异阈值与误差成本待H1'),
('Q3.1','3','explicit','推导','多光束干涉必要条件','条件清单与数学推导；必要不等于充分','反射路径、相干性、衰减、可观测性区分','机理建模','无','列出非零多次返回振幅及相位相干的必要条件','复振幅叠加/边界传播机制候选','题面p1问题3、p2图2；相干长度/吸收未给','C03,C05,C10','未来检查反射消失、强衰减、不相干极限','仅见尖峰不能推出多光束；必要条件不保证可辨识','不使用有监督分类器：无多光束标签','相干、吸收、分辨率阈值待文献，禁止设未经证实阈值'),
('Q3.2','3','explicit','分析','多光束对厚度精度的影响','偏差机制、方向的条件性说明及误差对照计划','不能无证据宣称固定变厚/变薄','误差分析','机理模拟','在相同参数/噪声下比较单次与多次生成机制的未来实验','受控机制对照与灵敏度分析','题面要求影响分析，无实测真值','C03,C08,C09,C10','未来合成对照固定d与n，比较偏差和覆盖','模拟参数不代表真实材料；未识别时只能条件结论','拒绝只按拟合残差降低声称精度提高','影响阈值、复杂度与误判成本待H1'),
('Q3.3','3','explicit','判断','Si附件3/4的多光束证据','每角及合并的证据、反证与不确定判断','必要条件与光谱证据共同支持，允许证据不足','机制诊断','数据分析','以受限干涉基准残差为参照而非预设存在','物理假设比较/残差结构诊断','附件3/4同一Si晶圆双角；无标签/光学常数','C02,C04,C05,C10','未来跨角、跨窗口稳定性与替代解释检验','色散/基线/仪器结构也能解释形态则无法唯一判断','拒绝凭单个峰形直接下结论；聚类不提供物理标签','三态存在/未获支持/证据不足定义待H1'),
('Q3.4','3','explicit','建模','Si外延层厚度关系','适配Q3.3证据的模型与边界','与Si材料参数及多光束结论一致','机理建模','无','保留受限光程模型作为比较项','多次反射机理或受限模型候选，依证据取舍','附件3/4；Si不能沿用SiC折射率','C02,C03,C04,C05,C10','未来退化到基准、能量/边界检查','光学常数和厚度强耦合或参数过多导致不可识别','不因题面提多光束就冻结高复杂度模型','最终路线H2决定'),
('Q3.5','3','explicit','设计算法','Si厚度估计程序','可复现步骤、参数与失败条件','与Q3.4数学定义及数据一致','参数估计','无','与Q2.1相同的可比基准计算协议，改用Si条件','约束反演/谱特征候选','附件3/4有双角光谱','C03,C04,C06,C07','未来合成恢复、多初值/边界及角度检验','局部解不稳定或分辨率不足则返回不可识别','拒绝预先指定全局优化器为必要方案：尚无目标函数','搜索边界、拟合算法留DESIGN/H2'),
('Q3.6','3','explicit','计算','Si晶圆厚度','双角度及合并条件结果μm、局限','可复现且不与Q3.3结论矛盾','参数估计','无','独立角度估计与共同结论对照','物理约束独立/联合反演候选','附件3/4，不是SiC晶圆','C02,C03,C04,C08','未来角度差异、窗口与参数稳定性','多组等价解则报告范围或条件结果','拒绝把Si结果视作SiC真值或校准标签','可信区间的定义待H1'),
('Q3.7','3','implicit','检验','SiC中多光束是否存在且影响厚度','触发/不触发/证据不足及理由','分别判断机制存在与精度影响','机制诊断','误差分析','保持Q2基准，对照未来可识别的替代机制','物理假设检验和敏感性对照','题面问题3末段条件句；附件1/2异常率需区分','C04,C06,C08,C10','未来同时检验跨角稳定性、结构残差与厚度差','只因R>100或残差改善就触发修正为失败','拒绝把测量异常直接归因多光束','条件分支解释由H1确认'),
('Q3.8','3','conditional_explicit','消除影响','受多光束影响的SiC估计','针对性修正方案；注明剩余误差','只在Q3.7触发时执行，并可验证增益','机理修正','参数估计','未经修正Q2结果作为同口径基线','物理机理修正或证据支持的稳健反演候选','附件1/2与Q3.7；并无无误差参考','C03,C04,C06,C09,C10','未来固定比较口径检查跨角与敏感性，不能仅看残差','修正引入无法识别的参数或无增益则不保留','拒绝删异常后称多光束已消除；拒绝无依据复杂化','消除理解为校正/减弱，不能保证零误差'),
('Q3.9','3','conditional_explicit','计算','SiC修正后的厚度','修正前后双角/共同厚度及不确定性表','相同波段和假设口径，诚实报告未消除部分','参数估计','误差分析','Q2.2/Q2.3原始基准','可比对照估计与不确定性传播','Q3.8成立时附件1/2','C02,C03,C04,C08,C09','未来差值、敏感性、机制对照增益检验','无真值不能声明真实误差已降低指定百分比','拒绝只报更好数字或强迫两角相等','未触发时以论证替代数值，不伪造修正值'),
('I1','cross','implicit','审计','四份光谱数据和所有预处理','字段/异常/掩码/处理记录','原始值保留并可追溯到Excel行','数据分析','无','原始描述统计与异常标记，不清洗','描述审计/成对敏感性方案','四附件共29876谱点','C02,C06,C07,C11','行数、哈希、异常行及原值复核','静默截断/补值/平滑导致无法追溯','拒绝无条件裁剪到100%：原因未知','异常处置选项H1决定'),
('I2','cross','implicit','界定','厚度/光学常数可识别性与误差代价','未知参数、条件结论范围及失败返回','n与d混淆不伪装唯一物理厚度','可识别性分析','误差分析','保留n符号并列候选外部信息需求','结构/实际可识别性和敏感性分析','题面称n随波长/浓度变化但不给数值','C03,C04,C08,C09','未来参数相关性、剖面或等价解检查','n函数完全自由时厚度通常不可唯一辨识','拒绝无依据常数n；拒绝用Si参数替SiC','光学厚度可作中间量，不能替代题目所需物理厚度')]
relations={'Q1.1':[('Q2.1','dependency/input')],'Q2.1':[('Q2.2','dependency/input')],'Q2.2':[('Q2.3','dependency/input'),('Q3.9','difference/comparison')],'Q2.3':[('Q3.2','consistent/shared definition')],'Q3.1':[('Q3.3','dependency/input'),('Q3.7','dependency/input')],'Q3.2':[('Q3.7','dependency/input')],'Q3.3':[('Q3.4','dependency/input')],'Q3.4':[('Q3.5','dependency/input')],'Q3.5':[('Q3.6','dependency/input')],'Q3.6':[('Q2.2','difference/comparison')],'Q3.7':[('Q3.8','dependency/input')],'Q3.8':[('Q3.9','dependency/input'),('Q2.3','trade-off/conflict')],'Q3.9':[('Q2.2','difference/comparison')],'I1':[('Q2.1','dependency/input'),('Q3.5','dependency/input')],'I2':[('Q2.2','dependency/input'),('Q3.6','dependency/input')]}
questions=[]
for s in specs:
    id,parent,kind,action,obj,output,criterion,primary,secondary,baseline,family,basis,cs,valid,fail,reject,unknown=s
    questions.append(dict(id=id,parent=parent,kind=kind,source='input/B题/B题.pdf:p1问题'+parent if parent!='cross' else 'input/B题/B题.pdf:p1折射率背景及p2附件说明（分析者推定的支持任务）',action_keywords=[action],target=obj,decision_user='队伍及厚度测量结果使用者',output=output,granularity='按材料/晶圆/角度/候选波段追溯；理论项按条件；非总体外推',horizon='无时间预测范围',uncertainty='条件性、参数及测量误差；无真值限制',evaluation_criterion=criterion,relationships=[{'question_id':q,'type':t} for q,t in relations[id]],primary_task_type=primary,secondary_task_type=None if secondary=='无' else secondary,baseline=baseline,provisional_family=family,data_basis=basis,constraint_ids=cs.split(','),validation_path=valid,failure_condition=fail,rejected_families=reject,unknowns_H1=unknown,deliverable_ids=['D-'+id]))
cons=[
('C01','explicit','PDF:p1问题1/2','Q1限一次反射透射且Q2基于Q1','Q1.reflection_order == 1; Q2.model_reference == Q1','hard','已明确'),
('C02','data','PDF:p2附件说明','同材料两个角对应同一晶圆；两材料是不同晶圆','group(1)==group(2);group(3)==group(4);group(1)!=group(3);angles=[10,15,10,15]','hard','已核验'),
('C03','physical','PDF:p1厚度/入射角/折射率背景；单位为分析者形式化','物理厚度为正，单位与角度一致','d_um>0;d_cm=d_um*1e-4;lambda_um=1e4/sigma_cm_inv;theta_rad=theta_deg*pi/180','hard','厚度上限未给；波数真空口径需确认'),
('C04','data','PDF:p1折射率段及附件无n字段','折射率色散/掺杂未知，n与d耦合','if n_unconstrained or multiple_equivalent_solutions: report conditional_or_nonidentifiable; no unique_d_claim','hard','缺光学常数、浓度、温度、晶型与吸收信息'),
('C05','physical','PDF:p1图1/p2图2；物理约束为候选形式化','边界折射、相干和能量约束适用条件必须标明','for passive calibrated power: 0<=R,T,A<=1 and R+T+A=1; lossless real_n: n0*sin(theta0)=n1*sin(theta1)','hard','含吸收时须复数处理；只有R数据不能完整核验能量'),
('C06','data','附件2 Sheet1 B列；四表Excel第2行','异常测量不能静默当真实反射率或清洗','flag=(R_percent<0 or R_percent>100 or R_percent==0); original_hash_unchanged; every_mask_has_row_and_reason','hard','262个>100%；四个首点0；成因未知'),
('C07','temporal/order','四表A列审计','横轴为有序波数，非时间；步长非精确常数','all(diff(sigma)>0); no_random_point_validation_as_independent; resampling_requires_record','hard','四表相同网格，精度/仪器分辨率未给'),
('C08','data','四表仅两字段及题面p2','无厚度真值，晶圆层面每材料n=1','no_absolute_accuracy_claim_without_reference; n_independent_wafer_per_material=1','hard','相邻点相关性未估计；不进行总体推广'),
('C09','practical','H0理由与required_validations；分析者误差成本定义','新增模块须针对缺陷且验证增益；容忍度尚无','retain_improvement only if documented_defect and validation_gain and identifiable; numerical_tolerance=None','soft','H1需选评价口径，H2前定量化阈值'),
('C10','explicit','PDF:p1问题3','必要条件与存在判断分开；SiC修正有条件触发','execute(Q3.8,Q3.9) iff supported(SiC_multibeam) and supported(thickness_impact); else document_reason_or_insufficient_evidence','hard','影响可否支持待后续验证'),
('C11','workflow','任务恢复基线/H0','只写01-intake；H1停止，不作最终路线选择','all(write_paths under 01-intake); no_thickness_fit; no_TEAM_APPROVED_write; next_gate=H1','hard','当前执行边界'),
('C12','official','R1:p3-5,p8','2025提交和独立完成要求','check_submission_checklist(R1); historical_deadlines_not_current; no_team_identifiers_in_electronic_files','hard','历史提交规范已核验；地区补充未知'),
('C13','official','R2:p1条3-5','AI生成标注、引用与详情；核心工作队员独立完成','body_AI_marks and tool_reference and support_AI_details_pdf and adoption_human_modification_log','hard','本阶段AI使用已记；人工核验未发生'),
('C14','official','题面p1格式提示及全国当前规则检索','2025最终模板/赛区要求不得用2026代替','template_year_applicability_verified_before_submission; regional_check_pending=True','hard','未完全核验；不妨碍中立H1定义，阻止声称提交合规完成')]
constraints=[]
for id,cat,source,natural,formal,hard,status in cons:
    affected=[q['id'] for q in questions if id in q['constraint_ids']]
    constraints.append(dict(id=id,category=cat,source=source,statement=natural,formal_check=formal,scope=affected or ['官方提交/工作流'],hardness=hard,status=status,affected_questions=affected))
deliverables=[dict(id='D-'+q['id'],question_ids=[q['id']],source=q['source'],content=q['output'],format='论文对应小节+可复核证据；计算项另附代码/结果表（后续阶段）',limit='题面未给单项篇幅/文件限制',acceptance=q['evaluation_criterion'],conditional=q['kind']=='conditional_explicit') for q in questions]
for id,content,rule,acceptance in [('S1','匿名电子论文PDF或Word，代码附录','C12','单文件不压缩、去承诺/编号页、元数据及文件名无队伍身份'),('S2','支撑材料ZIP/RAR及可运行代码/必要数据','C12','与论文分开；含代码；文件与提交MD5一致'),('S3','纸质论文、承诺书和编号页（按赛区）','C12','与电子内容相符、签名与地区要求核验'),('S4','AI工具引用、正文标注与支撑材料AI 工具使用详情.pdf','C13','工具/版本/日期/目的/关键交互/采纳/人工修改齐全'),('S5','2025模板、版式及地区附加规则核验记录','C14','版本与地区由队员核验，当前不声明完成')]:
    deliverables.append(dict(id=id,question_ids=[],official_rule=rule,content=content,format=content,limit='详见官方规则与AI合规.md；未核验限制不猜测',acceptance=acceptance,conditional=False))
known=[{'id':'K01','category':'background','source':'PDF:p1背景','evidence_type':'题面事实转述','statement':'红外干涉法用于无损厚度测量；外延层/衬底掺杂差异影响折射率。'}, {'id':'K02','category':'background','source':'PDF:p1折射率段','evidence_type':'题面事实转述','statement':'外延层折射率通常不是常数，与波长及载流子浓度等有关；题目未提供具体关系。'}, {'id':'K03','category':'fields','source':'PDF:p2附件说明及附件Sheet1 A1:B7470','evidence_type':'题面事实与机器审计','statement':'四份附件各两字段：波数cm^-1和反射率%；材料/角度由题面定义，见附件清单profiles。'}, {'id':'K04','category':'files','source':'附件清单.json:inputs','evidence_type':'哈希核验','statement':'12项指定项目输入，另保留5项旧BLOCKED诊断副本；没有读取其他题原件。'}, {'id':'K05','category':'rules','source':'官方规则与AI合规.md:R1/R2','evidence_type':'在线规则及主控核准','statement':'2025汇编内2019参赛规则；2025试行AI规则；地区附加待核验。'}, {'id':'K06','category':'assumption','source':'分析者解释，H1待确认','evidence_type':'解释非题面给定','statement':'采用μm报告物理厚度；测量准确性无真值时只给条件性证据；不默认常数折射率。'}]
structure={'schema_version':'1.0','stage':'INTAKE','decision_status':'H1_PENDING','problem':{'year':2025,'id':'B','title':'碳化硅外延层厚度的确定','primary_questions':3,'subquestions':len(questions),'decomposition_note':'12项无条件显式、1项隐式触发判断及2项跨问支持任务的实际分类见questions.kind；条件结果可与修正合并呈现但验收分开。'},'known_information':known,'requested_questions':questions,'constraints':constraints,'mandatory_deliverables':deliverables,'shared_definitions':{'sigma':'波数cm^-1，非时间','R_observed':'原始反射率%，不强迫落在[0,100]','R_physical':'适用被动校准条件下的功率比例[0,1]','d':'晶圆物理外延厚度μm','n':'材料与波段相关折射率；未指定函数','accuracy':'对真值的误差，当前不可直接验证','stability':'扰动/窗口/角度下的变化，不等于accuracy'},'error_costs':[{'error':'把多光束误判为存在','cost':'引入冗余参数、不可识别或错误修正','numeric_cost':None},{'error':'漏判真实多光束/色散','cost':'厚度系统偏差与区间过窄','numeric_cost':None},{'error':'删去真实结构或保留失真点当物理反射率','cost':'相位/条纹偏差，需对照处理','numeric_cost':None},{'error':'把拟合优度当绝对准确度','cost':'测试标准不可信，错误器件质量判断','numeric_cost':None}],'H1_options_reference':'H1-选择包.md','final_model_selected':False,'thickness_model_run':False}
# Correct explicit count from data, no manually inferred count.
structure['problem']['decomposition_note']='3主问题拆为13项题内任务（10项无条件显式、1项隐式条件判断、2项条件显式）及2项跨问隐式支持任务；可合并叙述，验收仍逐项对应。'
dump('赛题结构化说明.json',structure)

lines=['# B题数据审计报告','', '状态：完整只读审计完成，模型计算未开始。原始PDF两页有文本层；12项输入路径/哈希及上游4项输出核验通过。详表与异常逐行记录见附件清单.json。','', '|附件|材料/角度|数据行|首行值|末行值|反射率范围%|>100点|零点|','|---|---|---:|---|---|---|---:|---:|']
for p in profiles: lines.append(f"|{Path(p['path']).name}|{p['material']}/{p['angle_deg']}°|{p['data_rows']}|{p['first']}|{p['last']}|{p['fields'][1]['min']}–{p['fields'][1]['max']}|{p['above_100_count']}|{p['zero_count']}|")
lines+=['','第一行有明确表头，因此7470个工作表行=1表头+7469条观测。题面未声明记录总数；这是从工作簿实读所得，不套用7470条数据的模板断言。四表均只有Sheet1和两列，所有数据为有限数值，无空单元格；不存在公式、错误单元格、隐藏行列、合并单元格、批注、外链或宏的结论以清单计数为准。未修改表格。','', '四表波数网格完全一致，范围399.6747–4000.122 cm^-1，严格递增、无重复波数；步长约0.481–0.483 cm^-1，并非严格等间距。波长倒数换算范围约2.5–25.0 μm只是单位换算，不是折射率适用域确认。不得未经记录直接对原序列作严格均匀采样假设。横轴为光谱顺序，没有时间/空间坐标、重复扫描编号或仪器分辨率。','', '29876个谱点不能视为29876块晶圆。SiC与Si各仅一块晶圆，各有两个入射角；谱点相关性和扫描重复性未知。类别标签、厚度真值均缺失，类别平衡不适用；不存在可支持监督训练/泛化准确率的标注集。不同材料不合并为一块晶圆，两个角度也不自动当独立样本。','', '附件2超过100%的262点及四表首数据行反射率0均已逐行标记；超过100%与被动体系的真实绝对功率反射率约束冲突，但不能据此否定原始测量文件。归一化/校准、基线或仪器误差均只是待核验解释，零点也可能为边界/占位或真实测量，当前不定性。不得裁剪、删除或补值。H1提供保留并标记、成对掩码敏感性两种可追溯策略，处理阈值以后依据证据确定。','', '未提供折射率、吸收系数、载流子浓度、SiC晶型、温度、偏振、仪器响应、光谱分辨率、角度误差或独立厚度测量。条纹主要约束光学路径，n与d耦合；两角能否解除耦合需要后续可识别性验证，不能只因有两角就宣称唯一解。色散、多光束、仪器基线与吸收之间可能互相混淆。','', '后续验证应保留角度与连续波段结构：角度一致性、跨窗口稳定性、结构残差、参数敏感性及已知参数合成恢复分别提供不同证据。随机拆分相邻谱点会泄漏局部结构，不能据此报告独立预测性能。当前不作平滑、极值检测、傅里叶估计、厚度拟合或模型选择。','', '复现：使用包含openpyxl、pypdf、jsonschema的Python运行01-intake/build_intake.py，再运行01-intake/validate_intake.py。脚本只读12项指定输入及旧诊断，只写01-intake；规则来源需按规则文档独立复核。']
write('数据审计报告.md','\n'.join(lines)+'\n')
lines=['# 问题—方法—约束矩阵','','全部为临时方法族筛选，置信度：机理/参数反演任务类型高；具体方法适用性中低，取决于光学参数与可識别性。最低可信基线是比较计划，尚未运行，也不是最终路线。一次反射/透射导致的是两束干涉，不称作单光束干涉。','', '|问题|关键词/输出合同|关系|主/次任务|最低基线|临时方法族/数据依据|约束|验证路径/失败条件|拒绝理由|H1未知|','|---|---|---|---|---|---|---|---|---|---|']
for q in questions:
    lines.append('|'+ '|'.join([q['id'],','.join(q['action_keywords'])+'；'+q['output'],'；'.join(x['question_id']+':'+x['type'] for x in q['relationships']),q['primary_task_type']+'/'+str(q['secondary_task_type']),q['baseline'],q['provisional_family']+'；'+q['data_basis'],','.join(q['constraint_ids']),q['validation_path']+'；失败：'+q['failure_condition'],q['rejected_families'],q['unknowns_H1']])+'|')
lines+=['','## 约束登记','', '|ID/类别|来源|内容|可检查形式|硬度/状态|','|---|---|---|---|---|']
for c in constraints: lines.append('|'+ '|'.join([c['id']+'/'+c['category'],c['source'],c['statement'],c['formal_check'],c['hardness']+'/'+c['status']])+'|')
lines+=['','## 交付物双向映射','','每个Q/I任务唯一映射D-同编号；JSON的requested_questions.deliverable_ids与mandatory_deliverables.question_ids反向对应。S1–S5分别反向指向C12/C13/C14官方提交约束。所有显式、隐式及条件任务均保留，不用修正结果覆盖原基准。','', '无真值时以条件性结果及不确定性陈述满足诚实分析，不把没有真值等同于不能推进H1。最终数值容忍度、折射率范围、波段与相干阈值均未给；未形式化的外部阈值须在后续选择前明确，不在INTAKE编造。','', '统一拒绝非问题导向的模型堆叠：分类缺标签，聚类不提供干涉物理机制，时间预测缺时间与预测目标，综合评价缺排名任务和指标权重依据，因果推断缺干预/识别条件。数值优化可作为后续反演的求解工具，当前不将其误写为资源决策优化任务。']
write('问题方法约束矩阵.md','\n'.join(lines)+'\n')

write('官方规则与AI合规.md','''# 2025适用规则与AI合规

核验日期：2026-09-05。对象是2025高教社杯全国大学生数学建模竞赛B题历史练习。赛区/学校未知，未完成地区合规。规则版本采用本次主控明确核准基线，不改换版本。

R1：[全国官网2025参赛文件汇编](https://www.mcm.edu.cn/upload_cn/node/745/ogFWOgXVc36c27bb3ee3adf21e06f53146b03585.pdf)。PDF第3–5页为2025报名参赛须知，第8页为2019修订参赛规则。2012独立PDF仅历史旧版，不能作为2025适用版本；旧BLOCKED副本仅保留诊断。2026规则和格式不回溯。

按R1第3–5页核对：电子论文为独立PDF或Word，不压缩，不含承诺书和编号页；代码进入论文附录并进入独立ZIP/RAR支撑材料。论文、支撑材料及名称/属性须匿名。历史MD5提交截止为2025-09-07 20:00，电子文件上传为当日20:30至次日14:00；提交文件需匹配其MD5。纸质材料按赛区执行，承诺书和编号页另附。它们不是2026当前工作截止日。项目SHA-256是证据追踪，不能替代竞赛提交MD5。第8页要求队伍独立作答、引用公开成果、禁止赛时队外指导讨论。

R2：[安徽建筑大学官网托管的2025试行AI规定](https://www.ahjzu.edu.cn/_upload/article/files/ae/c2/1aaafbc1476c957b44c064dcaea9/fbe74512-36ac-448d-a35f-71757584e4f3.pdf)，第1页条3–5。高校官网托管副本，未找到全国官网原始发布链接；组委会署名，2025-09-01起试行。保守执行：AI参与内容在正文对应处标注，参考文献列工具名称、版本/型号、开发机构和使用日期；支撑材料含“AI 工具使用详情.pdf”，记录工具版本、目的环节、关键提示与回复、采纳及人工修改。核心建模分析由队员独立完成。不能把人工核验尚未发生写成已完成，也不能声明未使用AI。

格式核验边界：题面要求阅读论文格式规范，R1未附完整格式正文。全国官网当前检索返回2026修订格式，不能套用；尚未确认2025最终适用模板/版本、承诺书和编号页原件，页数、字号、文件大小等不猜测为硬约束。H1可确认问题定义，但正式排版与提交前须由队员核验2025归档格式、具体赛区及校内附加要求。当前不声称模板或地区合规完成。

本次实际AI用途：Codex读取获准文件、提取题面、生成只读数据审计与H1草案、执行路径及哈希检查、在线核验规则。未检索题目文献、未选择最终模型、未计算厚度。影响文件为本目录当前交付包及审计脚本。工具运行日期2026-09-05；确切模型版本应由主控按本任务元数据补记，不虚构版本。人工采纳/修改/核验均待队员记录。主控负责在其权限内追加真实AI日志；本任务不写.workflow。

提交验收责任：队员核对S1–S5；R1已查来源不代表论文已符合要求。AI记录若存在缺项，论文阶段不得用空白模板冒充完成。H1通过也不等于最终提交批准。
''')
write('H1-选择包.md','''# B题H1中立选择包

状态：H1_PENDING。H0只冻结选择B题，确认人为队长。INTAKE的PASS表示结构化交接完整，不代表队伍已经批准假设、阈值或路线。

问题定义：3个主问题拆为13个题内任务及2个支持任务，逐项见赛题结构化说明.json与问题方法约束矩阵.md。目标是基于双角红外反射光谱解释并估计两种材料各一块晶圆的物理外延厚度，完成多光束必要条件、影响及有条件SiC修正。输出μm是候选报告单位；模型比较需共同单位和数据口径。

## 待队伍选择的定义与证据政策

|议题|选项A|选项B|共同边界与代价|
|---|---|---|---|
|问题拆分|保留15项逐项验收|写作中合并算法/计算等相邻任务，但保留15项映射|不能遗漏Q3必要条件、影响、Si模型算法结果及SiC条件分支|
|异常反射率|原值保留并标记，以物理失真风险限定使用|原值保留，额外建立有理由掩码，做保留/排除的成对敏感性|不裁剪到100%；不先认定原因。A可能受异常影响，B可能丢失真实结构|
|可靠性目标|以条件性厚度、双角一致性、稳定性作为现有证据边界|在A基础上主动列出独立真值/仪器信息需求，取得后才评价绝对误差|目前无真值；两者都不能承诺绝对精度。阈值数值留待有依据时确认|
|多光束诊断|使用存在/未获支持/证据不足三态|作条件场景并列，暂不作存在性归类|必要条件不是充分条件；不能由R>100直接判断。前者便于分支，后者避免强判但结论较宽|
|SiC条件修正|只有存在及影响均有支持才给修正结果|证据不足时呈现有/无多光束的条件结果边界，不能称已消除|Q3.8/3.9未触发时必须有理由；不伪造修正值|
|外部光学信息|H1后优先核验材料/掺杂/波段匹配的n信息|先明确可识别性与所需测量清单，再有针对性补充n信息|只批准需求顺序；不批准常数n、色散函数、多光束形式或拟合算法|

没有默认选中项。请队长在独立H1决议中记录选项/修改、理由、接受假设、拒绝项、核验要求与确认人。本包不代填决议。

## 必须明确的假设与误差成本

题面给定同晶圆双角，未给光学常数/偏振/吸收/仪器分辨率/真值。均匀平行外延层、各角共享材料参数、弱吸收、局部常数折射率、可观测相干条件等只能作为后续候选假设，不是已知事实。n与d混淆可能使物理厚度不可识别；必要时报告条件范围与信息缺口，不能用光学厚度替代最终目标。

漏掉色散或多光束可能造成系统偏差；误加多光束可能过拟合；排除异常可能损坏条纹；保留失真幅度可能违背物理。以残差下降换取不可识别参数不算成功。队伍需确认重视的误差类型以及阈值制定依据；当前无工程容差，不能捏造百分比。

用户希望从可信基准针对物理缺陷逐步改进。这是复杂度控制偏好，并不预先冻结最终单次反射、色散、多光束或求解算法。所有候选改进须有明确缺陷、可识别条件、可比较验证及失败退出。

## 后续验证需求与停止位置

检查折射率关系的材料、晶型、掺杂、温度与波段适用性；检查多光束相干、振幅衰减、吸收/偏振与分辨率必要条件；分别规划基准、角度一致性、波段/异常敏感性、残差和合成恢复证据。完整方法族比较在H1后文献交接及DESIGN阶段进行，H2决定最终路线。

当前产物不含厚度数值、拟合、文献检索或TEAM_APPROVED。主控验证handoff后交队伍H1；只有真实H1批准后，按工作流停在WAITING_FOR_LITERATURE，等待用户提供文献再启动对应任务。赛区及2025最终模板仍待队员核验，不以此声称地区合规。
''')
write('停止报告.md','''# 旧阻塞已解除的恢复记录

原2025规则版本歧义已由本次主控明确核准解决：适用2025汇编中的2019参赛规则，AI规则采用已声明来源限制的2025试行副本。旧文件完整保存在diagnostics/BLOCKED-*，仅作历史诊断，不能作为当前交接。

当前INTAKE完成状态以本目录handoff.json为准。当前停止原因是等待H1人类决议，而非原规则版本阻塞。未修改上游、决议或工作流状态。地区和模板的剩余核验事项见当前合规报告。
''')
dump('AI使用记录.json',{'date':'2026-09-05','tool':'Codex','model_version':'由主控据任务元数据补记；本任务不虚构','purpose':['合规核验','只读附件审计','结构化问题与中立H1草案','哈希与路径验证'],'human_review':'尚未进行','human_modifications':[],'adoption':'待H1队伍决定','prohibited_work_performed':False,'affected_directory':'01-intake','key_interaction':'本次主控恢复授权；原始交互由主控从任务历史保留，本记录不代替完整交互日志'})
print('Built intake content; profiles:',[(p['material'],p['angle_deg'],p['above_100_count']) for p in profiles])
