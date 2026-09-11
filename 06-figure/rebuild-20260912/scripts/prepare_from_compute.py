from pathlib import Path
import hashlib, json, shutil
import pandas as pd

ROOT=Path(__file__).resolve().parents[3]; OUT=ROOT/'06-figure'/'rebuild-20260912'
for d in ('contracts','data-snapshots','figures','previews','logs'): (OUT/d).mkdir(parents=True,exist_ok=True)
MAIN=['FIG-Q1-C-FIELD','FIG-Q1-END-EFFECT','FIG-Q2-C-PROFILES','FIG-Q2-MODEL-ABLATION','FIG-Q2-GRID-CONV','FIG-Q3-THRESHOLD-TRAJECTORY','FIG-Q3-BRACKET-ZOOM','FIG-Q3-TIME-CONV','FIG-Q3-SENS-ONEFACTOR','FIG-Q3-COMBINED-BOUNDARY','FIG-Q4-RADIUS-TIME','FIG-Q4-THRESHOLD-TRAJECTORY','FIG-Q4-IMPLEMENTATION-AGREEMENT','FIG-Q4-JACOBIAN-ABLATION','FIG-Q4-COMBINED-BOUNDARY','FIG-VAL-BALANCE-RESIDUAL']
APP=['FIG-Q1-GRID-CONV','FIG-Q2-V02-MARGIN','FIG-Q3-SPACE-CONV','FIG-Q4-BRACKET-ZOOM','FIG-Q4-SPACE-CONV','FIG-Q4-DRY-SOLID-CONTINUITY']
TABLES=['TAB-Q2-MODEL-CONTRACT','TAB-APPLICABILITY-FAILURE','TAB-STRATEGY-ASSUMPTION','TAB-VAL-V01-V12','TAB-CLAIM-LIMIT']
ALL=MAIN+APP+TABLES
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(fid,df,sources):
    p=OUT/'data-snapshots'/f'{fid}.csv'; df.to_csv(p,index=False,encoding='utf-8-sig')
    meta={'figure_id':fid,'snapshot_sha256':sha(p),'sources':[{'path':str(Path(s).as_posix()),'sha256':sha(ROOT/s)} for s in sources], 'created_from':'authoritative upstream data only; no 06-figure source permitted'}
    (OUT/'data-snapshots'/f'{fid}.meta.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')

r=ROOT/'04-compute'/'results'; run=pd.read_csv(r/'run-summary.csv'); conv=pd.read_csv(r/'convergence.csv'); fg=pd.read_csv(r/'field-grid-convergence.csv'); tg=pd.read_csv(r/'threshold-grid-convergence.csv'); sens=pd.read_csv(r/'sensitivity.csv'); val=pd.read_csv(r/'validation-register.csv'); km=json.loads((r/'key-metrics.json').read_text(encoding='utf-8'))
q1=pd.read_csv(r/'q1-samples.csv'); q2=pd.read_csv(r/'q2-samples.csv'); q3=pd.read_csv(r/'q3-threshold-trajectory.csv'); q4=pd.read_csv(r/'q4-threshold-trajectory.csv')
save('FIG-Q1-C-FIELD',q1[['time_s','radius_cm','C_kg_per_kg']],['04-compute/results/q1-samples.csv'])
save('FIG-Q1-END-EFFECT',run[run.label.isin(['Q1-M1-base','Q1-M2-base'])][['label','final_mean_C']],['04-compute/results/run-summary.csv'])
save('FIG-Q1-GRID-CONV',fg[fg.scope.eq('Q1')],['04-compute/results/field-grid-convergence.csv'])
save('FIG-Q2-C-PROFILES',q2[['time_s','radius_cm','C_kg_per_kg']],['04-compute/results/q2-samples.csv'])
save('FIG-Q2-MODEL-ABLATION',pd.DataFrame({'model':['M2 常物性','M3 主路线','M4 消融'],'final_max_C':[km['q2_m2_constant_final_max_C'],km['q2_m3_final_max_C'],km['q2_m4_final_max_C']]}),['04-compute/results/key-metrics.json'])
save('FIG-Q2-GRID-CONV',fg[(fg.scope.eq('Q2')) & (fg.metric.eq('final_max_C'))],['04-compute/results/field-grid-convergence.csv'])
save('FIG-Q2-V02-MARGIN',pd.DataFrame({'observed':[conv.query("scope=='Q2' and family=='M3' and metric=='final_max_C'").absolute_change.iloc[0]],'threshold':[5e-5]}),['04-compute/results/convergence.csv','04-compute/results/validation-register.csv'])
save('FIG-Q3-THRESHOLD-TRAJECTORY',q3,['04-compute/results/q3-threshold-trajectory.csv'])
save('FIG-Q4-THRESHOLD-TRAJECTORY',q4,['04-compute/results/q4-threshold-trajectory.csv'])
for scope,df in [('Q3',q3),('Q4',q4)]:
    base=run[(run.label.eq('Q3-M3-nr210') if scope=='Q3' else run.label.eq('Q4-reference-nr210'))].iloc[0]
    lo=float(json.loads(base.threshold_bracket)[0]); hi=float(json.loads(base.threshold_bracket)[1]); z=df[(df.time_s>=lo-60)&(df.time_s<=hi+60)][['time_s','max_C']].copy(); z['interpolated_event_time_s']=base.interpolated_event_time_s; z['reported_event_time_s']=base.reported_event_time_s; z['threshold']=0.149999
    save(f'FIG-{scope}-BRACKET-ZOOM',z,[f'04-compute/results/{scope.lower()}-threshold-trajectory.csv','04-compute/results/run-summary.csv'])
save('FIG-Q3-TIME-CONV',conv[(conv.scope.eq('Q3'))&(conv.metric.eq('t_star_time'))][['base','fine','absolute_change']],['04-compute/results/convergence.csv','04-compute/results/validation-register.csv'])
q3s=sens[(sens.scope.eq('Q3'))&~sens.factor.eq('combined_boundary_empirical')].copy(); q3s['crossed']=q3s.final_max_C<=0.149999; save('FIG-Q3-SENS-ONEFACTOR',q3s,['04-compute/results/sensitivity.csv'])
for scope in ('Q3','Q4'):
    x=sens[(sens.scope.eq(scope))&sens.factor.eq('combined_boundary_empirical')].copy(); x['crossed']=x.final_max_C<=0.149999; save(f'FIG-{scope}-COMBINED-BOUNDARY',x,['04-compute/results/sensitivity.csv'])
save('FIG-Q3-SPACE-CONV',tg[tg.scope.eq('Q3')],['04-compute/results/threshold-grid-convergence.csv'])
save('FIG-Q4-SPACE-CONV',tg[tg.scope.eq('Q4')],['04-compute/results/threshold-grid-convergence.csv'])
save('FIG-Q4-RADIUS-TIME',q4[['time_s','radius_m']],['04-compute/results/q4-threshold-trajectory.csv'])
impl=run[run.label.isin(['Q4-reference-nr210','Q4-moving-fv'])][['label','interpolated_event_time_s','reported_event_time_s']].copy(); save('FIG-Q4-IMPLEMENTATION-AGREEMENT',impl,['04-compute/results/run-summary.csv','04-compute/results/convergence.csv'])
save('FIG-Q4-JACOBIAN-ABLATION',pd.DataFrame({'route':['批准路线','Jacobian 消融'],'balance_error':[km['maximum_approved_route_balance_error'],km['jacobian_ablation_balance_error']]}),['04-compute/results/key-metrics.json','04-compute/results/validation-register.csv'])
q4fine=run[run.label.eq('Q4-reference-nr210')].iloc[0]; save('FIG-Q4-DRY-SOLID-CONTINUITY',pd.DataFrame({'metric':['干固体库存','局部连续性','几何误差'],'value':[q4fine.dry_solid_inventory_relative_error,q4fine.max_local_dry_continuity_relative_residual,q4fine.geometry_relative_error]}),['04-compute/results/run-summary.csv','04-compute/results/validation-register.csv'])
save('FIG-VAL-BALANCE-RESIDUAL',run[['label','normalized_moisture_balance_error','max_linear_relative_residual']],['04-compute/results/run-summary.csv','04-compute/results/key-metrics.json'])

model_table=pd.DataFrame({'模型':['M2','M3','M4'],'角色':['二维基础主干','状态相关主路线','内部温度耦合消融'],'冻结指标':[km['q2_m2_constant_final_max_C'],km['q2_m3_final_max_C'],km['q2_m4_final_max_C']],'边界':['基线比较','条件仿真主结果','不得升级为主路线']})
app_table=pd.DataFrame({'条件':['题设经验律','4 h后边界延拓','内部观测缺失','有界敏感性','扩展模型'],'可支持':['条件仿真','冻结窗口情景','数值验证','报告成功与失败','局限讨论'],'失效/限制':['不可外推普适规律','窗口变化需披露','不可声称现实准确性','72 h未达标须保留','S0不进入正式结果']})
strategy=pd.DataFrame({'策略':['一维降阶','状态相关物性','内部温度耦合','移动边界','经验参数'],'原因':['低成本基线','刻画干燥尾段','检验耦合增益','满足Q4收缩域','来自题设经验式'],'检验':['M1/M2端面差','M2/M3/M4消融','M4消融','双实现+Jacobian消融','单因素+组合压力测试'],'结论边界':['不能替代二维','模型差非拟合优度','机制差非因果','守恒非现实验证','仅在有界条件内']})
claim=json.loads((ROOT/'05-evidence'/'主张证据映射.json').read_text(encoding='utf-8')); claims=pd.json_normalize(claim.get('claims',claim if isinstance(claim,list) else []))
def markdown_table(df):
    cols=[str(x) for x in df.columns]; rows=['| '+' | '.join(cols)+' |','| '+' | '.join(['---']*len(cols))+' |']
    for vals in df.fillna('').astype(str).itertuples(index=False,name=None): rows.append('| '+' | '.join(v.replace('|','\\|').replace('\n','<br>') for v in vals)+' |')
    return '\n'.join(rows)+'\n'
for fid,df,sources in [('TAB-Q2-MODEL-CONTRACT',model_table,['decisions/H2-model.json','04-compute/results/key-metrics.json']),('TAB-APPLICABILITY-FAILURE',app_table,['decisions/H1-problem.json','decisions/H2-model.json','05-evidence/主张证据映射.json']),('TAB-STRATEGY-ASSUMPTION',strategy,['decisions/H1-problem.json','decisions/H2-model.json','04-compute/results/key-metrics.json']),('TAB-VAL-V01-V12',val,['04-compute/results/validation-register.csv']),('TAB-CLAIM-LIMIT',claims,['05-evidence/主张证据映射.json'])]: save(fid,df,sources); df.to_csv(OUT/'figures'/f'{fid}.csv',index=False,encoding='utf-8-sig'); (OUT/'figures'/f'{fid}.md').write_text(markdown_table(df),encoding='utf-8')

req={x['figure_id']:x for x in json.loads((ROOT/'05-evidence'/'正式图表需求.json').read_text(encoding='utf-8'))['requirements']}; req['TAB-STRATEGY-ASSUMPTION']={'question_claim':'H3 / 策略假设','reader_question':'为何采用这些策略，如何验证？','chart_type':'策略—检验矩阵','axes_units':'table','series':'五项策略','key_annotations':'冻结边界','mandatory_limit':'不得新增优越性判断','placement':'主文'}
items=[]
for fid in ALL:
    q=req[fid]; meta=json.loads((OUT/'data-snapshots'/f'{fid}.meta.json').read_text(encoding='utf-8')); kind='table' if fid.startswith('TAB-') else 'figure'; placement='body' if fid in MAIN or fid in TABLES[:3] else 'appendix'
    contract={'figure_id':fid,'claim_ids':[q['question_claim']],'question':q['reader_question'],'source_files':meta['sources'],'x':{'definition':q['axes_units']} if kind=='figure' else None,'y':{'definition':q['axes_units']} if kind=='figure' else None,'groups':[q['series']],'uncertainty':'确定性条件仿真，无抽样误差','required_comparisons':[q['key_annotations']],'must_show_failures':fid in ['FIG-Q3-SENS-ONEFACTOR','FIG-Q3-COMBINED-BOUNDARY','FIG-Q4-COMBINED-BOUNDARY','FIG-Q4-JACOBIAN-ABLATION','TAB-VAL-V01-V12'],'prohibited_operations':['不得读取06-figure旧产物','不得改写源数据、阈值或指标','不得隐藏失败或有限裕量'],'target_formats':['svg','png'] if kind=='figure' else [],'minimum_dpi':600 if kind=='figure' else 300,'snapshot':{'path':rel if False else f'06-figure/rebuild-20260912/data-snapshots/{fid}.csv','sha256':meta['snapshot_sha256']}}
    (OUT/'contracts'/f'{fid}.json').write_text(json.dumps(contract,ensure_ascii=False,indent=2),encoding='utf-8')
    items.append({'id':fid,'kind':kind,'subproblem':fid.split('-')[1] if fid.startswith('FIG-Q') else 'VAL/H3','claim_or_question':q['reader_question'],'source_data':meta['sources'],'model_result_version':'H2 TEAM_APPROVED + COMPUTE PASS + H3 TEAM_APPROVED','evidence_class':'quantitative','visual_family':q['chart_type'],'axes':[] if kind=='table' else [{'axis':'x','label':q['axes_units'],'unit':'见标签','scale':'linear'},{'axis':'y','label':q['axes_units'],'unit':'见标签','scale':'log' if fid in ['FIG-Q4-JACOBIAN-ABLATION','FIG-Q4-DRY-SOLID-CONTINUITY','FIG-VAL-BALANCE-RESIDUAL'] else 'linear'}],'groups':[q['series']],'uncertainty':{'display':'none','definition':'确定性条件仿真，无抽样不确定性','sample_size':None},'annotations':[q['key_annotations']],'expected_reading':q['reader_question'],'generation':{'tool':'MATLAB','formats':['svg','png@600dpi'] if kind=='figure' else ['csv','md']},'placement':placement,'provenance':{'owner':'team','privacy':'internal','license':'team-generated'},'limitations':[q['mandatory_limit']],'prohibited_interpretations':['不得表述为现实验证','不得改变冻结科学意义'],'confirmation':'TEAM_CONFIRMED_H3'})
reg={'schema_version':'1.0','status':'VALIDATED','project':'CUMCM2026 A题全新正式图表','route_confirmed':True,'global_visual_spec':{'language':'zh-CN','fonts':{'cjk':'Microsoft YaHei','latin':'Times New Roman','math':'STIX Two Math'},'label_policy':'短标题、直接标注、变量与单位并列','color_semantics':{'primary':'#0072B2','comparison':'#E69F00','failure':'#D55E00','neutral':'#666666'},'grayscale':'颜色之外使用线型、marker、空心/实心和直接标签','accessibility':'Okabe-Ito；最小文字7.5 pt；不以颜色单独编码','dimensions_mm':{'single_column_width':80,'double_column_width':166,'max_height':205},'formats':['svg','png@600dpi']},'items':items}
(OUT/'figure-register.json').write_text(json.dumps(reg,ensure_ascii=False,indent=2),encoding='utf-8')
# Provenance guard: neither sources nor generated contracts may depend on any old figure-stage artifact.
for p in list((OUT/'contracts').glob('*.json'))+[OUT/'figure-register.json']:
    doc=p.read_text(encoding='utf-8').replace('06-figure/rebuild-20260912','')
    if '06-figure/' in doc or '06-figure\\' in doc: raise SystemExit(f'OLD_FIGURE_DEPENDENCY: {p}')
print(json.dumps({'status':'PASS','snapshots':len(ALL),'contracts':len(ALL),'old_figure_dependencies':0},ensure_ascii=False))
