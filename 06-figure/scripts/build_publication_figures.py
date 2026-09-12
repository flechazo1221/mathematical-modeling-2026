from __future__ import annotations

import hashlib, json, shutil
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "06-figure"
RES = ROOT / "04-compute" / "results"
EVI = ROOT / "05-evidence"
for d in ("contracts", "data-snapshots", "figures", "previews"):
    (OUT / d).mkdir(parents=True, exist_ok=True)

plt.rcParams.update({"font.family":"Microsoft YaHei", "font.size":8, "axes.labelsize":8,
                     "xtick.labelsize":7, "ytick.labelsize":7, "legend.fontsize":7,
                     "svg.fonttype":"none", "axes.unicode_minus":False})
COL = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9", "#D55E00"]
LS = ["-", "--", "-.", ":"]
MK = ["o", "s", "^", "D"]
THR = 0.149999

REQ = json.loads((EVI / "正式图表需求.json").read_text(encoding="utf-8"))["requirements"]
REQ = {x["figure_id"]: x for x in REQ}
MAIN = ["FIG-Q1-C-FIELD","FIG-Q1-END-EFFECT","FIG-Q2-C-PROFILES","FIG-Q2-MODEL-ABLATION","FIG-Q2-GRID-CONV","FIG-Q3-THRESHOLD-TRAJECTORY","FIG-Q3-BRACKET-ZOOM","FIG-Q3-TIME-CONV","FIG-Q3-SENS-ONEFACTOR","FIG-Q3-COMBINED-BOUNDARY","FIG-Q4-RADIUS-TIME","FIG-Q4-THRESHOLD-TRAJECTORY","FIG-Q4-JACOBIAN-ABLATION","FIG-Q4-COMBINED-BOUNDARY"]
APP = ["FIG-Q1-GRID-CONV","FIG-Q3-SPACE-CONV","FIG-Q4-BRACKET-ZOOM","FIG-Q4-SPACE-CONV"]
TABLES = ["TAB-Q2-MODEL-CONTRACT","TAB-APPLICABILITY-FAILURE","TAB-STRATEGY-ASSUMPTION","TAB-VAL-V01-V12","TAB-CLAIM-LIMIT","TAB-Q4-DRY-SOLID-CONTINUITY"]

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rel(p): return Path(p).relative_to(ROOT).as_posix()
def snap_csv(fid, df, sources):
    p=OUT/"data-snapshots"/f"{fid}.csv"; df.to_csv(p,index=False,encoding="utf-8-sig")
    meta={"figure_id":fid,"snapshot":rel(p),"snapshot_sha256":sha(p),"sources":[{"path":rel(s),"sha256":sha(s)} for s in sources],"rows":len(df),"columns":list(df.columns)}
    m=p.with_suffix(".meta.json"); m.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
    return p,meta
def snap_json(fid, obj, sources):
    p=OUT/"data-snapshots"/f"{fid}.json"; p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding="utf-8")
    meta={"figure_id":fid,"snapshot":rel(p),"snapshot_sha256":sha(p),"sources":[{"path":rel(s),"sha256":sha(s)} for s in sources]}
    m=p.with_suffix(".meta.json"); m.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8"); return p,meta
def save(fid, fig):
    fig.set_size_inches(6.7,4.2)
    fig.savefig(OUT/"figures"/f"{fid}.svg",bbox_inches="tight")
    fig.savefig(OUT/"figures"/f"{fid}.png",dpi=600,bbox_inches="tight")
    fig.savefig(OUT/"previews"/f"{fid}-color.png",dpi=150,bbox_inches="tight")
    plt.close(fig)
    im=Image.open(OUT/"previews"/f"{fid}-color.png").convert("RGB")
    ImageOps.grayscale(im).save(OUT/"previews"/f"{fid}-grayscale.png")
def style(ax,x,y):
    ax.set_xlabel(x); ax.set_ylabel(y); ax.grid(axis="y",color="#dddddd",lw=.5); ax.spines[["top","right"]].set_visible(False)
def contract(fid, meta):
    q=REQ.get(fid,{"question_claim":"H3 / strategy","reader_question":"模型策略与假设如何被检验？","chart_type":"策略假设表","mandatory_limit":"不新增优越性判断","placement":"主文"})
    claims=[c.strip() for c in q["question_claim"].split("/")[-1].split(",") if c.strip()]
    obj={"figure_id":fid,"claim_ids":claims or ["H3"],"question":q["reader_question"],"source_files":meta["sources"],"x":None,"y":None,"groups":[],"uncertainty":None,"required_comparisons":[q["chart_type"]],"must_show_failures":fid in {"FIG-Q3-SENS-ONEFACTOR","FIG-Q3-COMBINED-BOUNDARY","FIG-Q4-COMBINED-BOUNDARY","FIG-Q4-JACOBIAN-ABLATION","TAB-VAL-V01-V12"},"prohibited_operations":["recompute model","change metric","omit failures","present conditional simulation as observation"],"target_formats":["svg","png"] if fid.startswith("FIG") else ["svg"],"minimum_dpi":600,"placement":q["placement"],"mandatory_limit":q["mandatory_limit"],"snapshot":meta["snapshot"],"snapshot_sha256":meta["snapshot_sha256"]}
    (OUT/"contracts"/f"{fid}.json").write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding="utf-8")

km=json.loads((RES/"key-metrics.json").read_text(encoding="utf-8")); run=pd.read_csv(RES/"run-summary.csv"); conv=pd.read_csv(RES/"convergence.csv"); grid=pd.read_csv(RES/"field-grid-convergence.csv"); tg=pd.read_csv(RES/"threshold-grid-convergence.csv"); sens=pd.read_csv(RES/"sensitivity.csv"); val=pd.read_csv(RES/"validation-register.csv")

def profiles(fid,file):
    s=RES/file; d=pd.read_csv(s)[["time_s","radius_cm","C_kg_per_kg"]]; _,m=snap_csv(fid,d,[s]); contract(fid,m)
    fig,ax=plt.subplots();
    for i,(t,g) in enumerate(d.groupby("time_s")): ax.plot(g.radius_cm,g.C_kg_per_kg,color=COL[i%6],ls=LS[i%4],marker=MK[i%4],ms=3,label=f"{t/3600:g} h")
    style(ax,"半径 r (cm)","干基含水率 C (kg/kg)"); ax.legend(ncol=2,frameon=False); ax.text(.01,.02,"条件仿真，非实测",transform=ax.transAxes,color="#555555"); save(fid,fig)
profiles("FIG-Q1-C-FIELD","q1-samples.csv"); profiles("FIG-Q2-C-PROFILES","q2-samples.csv")

fid="FIG-Q1-END-EFFECT"; s1=RES/"run-summary.csv"; s2=RES/"convergence.csv"; d=run[run.label.isin(["Q1-M1-base","Q1-M2-base"])][["label","final_mean_C"]]; _,m=snap_csv(fid,d,[s1,s2]); contract(fid,m); fig,ax=plt.subplots(); x=d.final_mean_C.to_numpy(); ax.plot(x,[0,0],color="#777777"); ax.scatter(x,[0,0],c=COL[:2],s=55); ax.set_yticks([]); style(ax,"1800 s 平均干基含水率 (kg/kg)",""); ax.annotate(f"差值 {abs(x[0]-x[1]):.10f}",(x.mean(),0),xytext=(0,18),textcoords="offset points",ha="center"); ax.text(x[0],-.035,"M1",ha="center"); ax.text(x[1],-.035,"M2",ha="center"); save(fid,fig)

fid="FIG-Q2-MODEL-ABLATION"; d=pd.DataFrame({"model":["M2 常物性","M3 主路线","M4 消融"],"final_max_C":[km["q2_m2_constant_final_max_C"],km["q2_m3_final_max_C"],km["q2_m4_final_max_C"]]}); _,m=snap_csv(fid,d,[RES/"key-metrics.json"]); contract(fid,m); fig,ax=plt.subplots(); ax.scatter(d.model,d.final_max_C,c=COL[:3],s=55); style(ax,"模型角色","3 h 最大干基含水率 (kg/kg)"); ax.text(.01,.02,"模型差异不代表现实准确率排序",transform=ax.transAxes); save(fid,fig)

fid="FIG-Q2-GRID-CONV"; d=grid[(grid.scope=="Q2")&(grid.family=="M3")&(grid.metric=="final_max_C")].copy(); _,m=snap_csv(fid,d,[RES/"field-grid-convergence.csv"]); contract(fid,m); fig,ax=plt.subplots(); ax.plot(d.nr,d.value,marker="o",color=COL[0]); style(ax,"径向网格数 nr","3 h 最大干基含水率 (kg/kg)"); ax.annotate("最细相邻变化 4.00114e-5\n验收线 5e-5（窄裕量）",(d.nr.iloc[-1],d.value.iloc[-1]),xytext=(-115,25),textcoords="offset points",arrowprops={"arrowstyle":"->"}); save(fid,fig)

def trajectory(fid,file,event):
    s=RES/file; d=pd.read_csv(s)[["time_s","max_C","mean_C","center_C","surface_C"]]; _,m=snap_csv(fid,d,[s]); contract(fid,m); fig,ax=plt.subplots();
    for i,c in enumerate(["max_C","mean_C","center_C","surface_C"]): ax.plot(d.time_s/3600,d[c],color=COL[i],ls=LS[i],label=c.replace("_C",""))
    ax.axhline(THR,color="#555555",ls="--",lw=.8,label="阈值 0.149999"); ax.axvline(event/3600,color=COL[5],ls=":",lw=.8); style(ax,"时间 (h)","干基含水率 C (kg/kg)"); ax.legend(ncol=3,frameon=False); ax.text(.01,.02,"条件仿真；报告时刻不表示物理秒级精度",transform=ax.transAxes); save(fid,fig)
trajectory("FIG-Q3-THRESHOLD-TRAJECTORY","q3-threshold-trajectory.csv",206820); trajectory("FIG-Q4-THRESHOLD-TRAJECTORY","q4-threshold-trajectory.csv",183840)

def bracket(fid,file,interp,reported):
    s=RES/file; a=pd.read_csv(s); d=a.iloc[(a.max_C-THR).abs().argsort()[:6]].sort_values("time_s")[["time_s","max_C"]]; _,m=snap_csv(fid,d,[s,RES/"run-summary.csv"]); contract(fid,m); fig,ax=plt.subplots(); ax.plot(d.time_s,d.max_C,"o-",color=COL[0]); ax.axhline(THR,color="#555",ls="--"); ax.axvline(interp,color=COL[1],ls="--",label=f"插值 {interp:.4f} s"); ax.axvline(reported,color=COL[2],ls=":",label=f"报告 {reported:.0f} s"); style(ax,"时间 (s)","最大干基含水率 (kg/kg)"); ax.legend(frameon=False); ax.text(.01,.02,"局部夹逼与取整规则；非额外实验精度",transform=ax.transAxes); save(fid,fig)
bracket("FIG-Q3-BRACKET-ZOOM","q3-threshold-trajectory.csv",206818.7114,206820); bracket("FIG-Q4-BRACKET-ZOOM","q4-threshold-trajectory.csv",183789.3317,183840)

fid="FIG-Q3-TIME-CONV"; d=conv[(conv.scope=="Q3")&(conv.metric.str.contains("t_star",na=False))].copy(); _,m=snap_csv(fid,d,[RES/"convergence.csv",RES/"validation-register.csv"]); contract(fid,m); fig,ax=plt.subplots(); v=float(d.absolute_change.max()); ax.scatter([0],[v],s=60,color=COL[1]); ax.axhline(60,color="#555",ls="--"); ax.set_xticks([0],["登记时间步细化"]); style(ax,"时间步对","事件时刻变化 (s)"); ax.annotate(f"精确变化 {v:.4f} s；登记 48 s\n目标 60 s，裕量有限",(0,v),xytext=(25,20),textcoords="offset points",arrowprops={"arrowstyle":"->"}); save(fid,fig)

def censored(fid,scope,factor=None):
    d=sens[sens.scope.eq(scope)].copy();
    if factor: d=d[d.factor.eq(factor)]
    else: d=d[~d.factor.eq("combined_boundary_empirical")]
    d["scenario"]=d.factor+"-"+d.level; d["time_h"]=d.t_star_s/3600; d["display_h"]=d.time_h.fillna(72); d["crossed"]=d.t_star_s.notna(); _,m=snap_csv(fid,d, [RES/"sensitivity.csv"]); contract(fid,m); fig,ax=plt.subplots();
    for i,row in d.reset_index(drop=True).iterrows():
        ax.scatter(i,row.display_h,marker="o" if row.crossed else "x",s=55,color=COL[0] if row.crossed else COL[5]);
        if not row.crossed: ax.annotate("72 h内未达标",(i,72),xytext=(0,-14),textcoords="offset points",ha="center",color=COL[5])
    ax.axhline(72,color="#555",ls="--"); ax.set_xticks(range(len(d)),d.scenario,rotation=25,ha="right"); style(ax,"压力测试情景","达标时间 (h；×为72 h右删失)"); ax.text(.01,.02,"有界压力测试，不是概率分布或置信区间",transform=ax.transAxes); save(fid,fig)
censored("FIG-Q3-SENS-ONEFACTOR","Q3"); censored("FIG-Q3-COMBINED-BOUNDARY","Q3","combined_boundary_empirical"); censored("FIG-Q4-COMBINED-BOUNDARY","Q4","combined_boundary_empirical")

fid="FIG-Q4-RADIUS-TIME"; s=RES/"q4-threshold-trajectory.csv"; d=pd.read_csv(s)[["time_s","radius_m"]]; _,m=snap_csv(fid,d,[s]); contract(fid,m); fig,ax=plt.subplots(); ax.plot(d.time_s/3600,d.radius_m*100,color=COL[0]); style(ax,"时间 (h)","半径 R(t) (cm)"); ax.text(.01,.02,"冻结收缩律的条件仿真，非尺寸实测",transform=ax.transAxes); save(fid,fig)

fid="FIG-Q4-JACOBIAN-ABLATION"; d=pd.DataFrame({"route":["批准路线","Jacobian 消融"],"balance_error":[km["maximum_approved_route_balance_error"],km["jacobian_ablation_balance_error"]]}); _,m=snap_csv(fid,d,[RES/"key-metrics.json",RES/"validation-register.csv"]); contract(fid,m); fig,ax=plt.subplots(); ax.scatter(d.route,d.balance_error,c=[COL[0],COL[5]],s=65); ax.set_yscale("log"); style(ax,"路线","归一化平衡误差（对数轴）"); ax.text(.01,.02,"消融失败必须保留；守恒诊断不是现实准确性",transform=ax.transAxes); save(fid,fig)

def space(fid,scope):
    d=tg[tg.scope.eq(scope)].copy(); _,m=snap_csv(fid,d,[RES/"threshold-grid-convergence.csv"]); contract(fid,m); fig,ax=plt.subplots(); ax.plot(d.nr,d.interpolated_event_time_s/3600,"o-",color=COL[0]); style(ax,"径向网格数 nr","插值事件时刻 (h)"); ax.text(.01,.02,"仅表明空间离散稳定性",transform=ax.transAxes); save(fid,fig)
space("FIG-Q3-SPACE-CONV","Q3"); space("FIG-Q4-SPACE-CONV","Q4")

fid="FIG-Q1-GRID-CONV"; d=grid[grid.scope.eq("Q1")].copy(); _,m=snap_csv(fid,d,[RES/"field-grid-convergence.csv"]); contract(fid,m); fig,axs=plt.subplots(1,2); 
for j,metric in enumerate(["final_max_C","final_mean_C"]):
    for i,(fam,g) in enumerate(d[d.metric.eq(metric)].groupby("family")): axs[j].plot(g.nr,g.value,marker=MK[i],ls=LS[i],color=COL[i],label=fam)
    style(axs[j],"径向网格数 nr",metric); axs[j].legend(frameon=False)
save(fid,fig)

claims=json.loads((EVI/"主张证据映射.json").read_text(encoding="utf-8"))["claims"]
tables={
"TAB-Q2-MODEL-CONTRACT":pd.DataFrame([{"模型":"M2","作用":"二维基础主干/常物性对照","当前指标":"3 h max C=2.1599687487","支持边界":"模型差异，非准确率"},{"模型":"M3","作用":"状态相关物性主路线","当前指标":"3 h max C=1.7278463920","支持边界":"条件仿真"},{"模型":"M4","作用":"内部温度耦合消融","当前指标":"3 h max C=1.7645199232","支持边界":"消融路线，不升级"}]),
"TAB-STRATEGY-ASSUMPTION":pd.DataFrame([
{"策略/假设":"一维降阶","考虑原因":"低成本基线并隔离端面效应","检验方式":"Q1 M1/M2公平对照与各自网格收敛","当前结论":"1800 s均值差0.0185457085","适用边界":"模型差异非精度提升"},
{"策略/假设":"状态相关物性","考虑原因":"描述干燥尾段与场非均匀性","检验方式":"M2/M3终值对照与M3网格验证","当前结论":"M3 3 h max C=1.7278463920","适用边界":"无内部观测，不宣称更真实"},
{"策略/假设":"内部温度耦合","考虑原因":"检验耦合机制的增量作用","检验方式":"M3/M4消融对照","当前结论":"M4 3 h max C=1.7645199232","适用边界":"机制消融非因果识别"},
{"策略/假设":"移动边界","考虑原因":"Q4收缩改变扩散距离与控制体积","检验方式":"双实现一致性、半径再现、V12","当前结论":"Q4报告183840 s；双实现差5.82e-10 s","适用边界":"冻结收缩律，非尺寸实测"},
{"策略/假设":"经验参数与4 h后延拓","考虑原因":"题面参数有限且需完成阈值计算","检验方式":"单因素与组合压力测试","当前结论":"Q3三种、Q4一种情景72 h未达标","适用边界":"条件仿真，不作概率或无条件外推"}]),
"TAB-APPLICABILITY-FAILURE":pd.DataFrame([{"条件":"题设经验律和冻结边界内","可支持":"Q1-Q4条件仿真与数值比较","失败/降级":"越出材料、设备或工况","禁外推":"普适规律或因果结论","新增证据":"真实内部温湿观测"},{"条件":"4 h后末段稳健延拓","可支持":"登记压力测试","失败/降级":"Q3/Q4组合低情景72 h未达标","禁外推":"把259200 s画成达标","新增证据":"长期烘房边界测量"},{"条件":"数值验证通过","可支持":"实现稳定与守恒","失败/降级":"Jacobian消融平衡误差0.5936","禁外推":"现实准确率","新增证据":"独立实验校准/验证"},{"条件":"M1-M4正式路线","可支持":"冻结层级内比较","失败/降级":"CFD/PINN/代理/纯ML未升级","禁外推":"补充路线替代主证据","新增证据":"独立保留门槛与真实数据"}]),
"TAB-VAL-V01-V12":val.copy(),
"TAB-CLAIM-LIMIT":pd.DataFrame([{"id":c["id"],"class":c["class"],"claim":c["candidate_claim"],"support":c["support_level"],"limits":c["limits"]} for c in claims if c["id"] not in {"SUP-OBS-01","SUP-INF-01"}]),
"TAB-Q4-DRY-SOLID-CONTINUITY":pd.DataFrame([{"metric":"干固体存量误差","value":4.441e-16,"interpretation":"收缩前后干固体总量的相对差异","conclusion":"近似守恒"},{"metric":"局部连续性残差","value":2.384e-13,"interpretation":"各控制体连续性方程的最大残差","conclusion":"近似满足连续性"},{"metric":"几何误差","value":0.0,"interpretation":"计算区域体积与给定半径关系的相对差异","conclusion":"几何关系一致"}])}
for fid,df in tables.items():
    sources=[RES/"validation-register.csv",RES/"run-summary.csv"] if fid=="TAB-Q4-DRY-SOLID-CONTINUITY" else ( [RES/"validation-register.csv"] if fid=="TAB-VAL-V01-V12" else ([EVI/"主张证据映射.json"] if fid=="TAB-CLAIM-LIMIT" else [ROOT/"decisions"/"H3-claims.json",RES/"key-metrics.json"]))
    p,m=snap_csv(fid,df,sources); contract(fid,m); shutil.copy2(p,OUT/"figures"/f"{fid}.csv"); (OUT/"figures"/f"{fid}.md").write_text(df.to_markdown(index=False),encoding="utf-8")

manifest={"schema_version":"1.0","status":"PASS","n_figures":len(MAIN)+len(APP),"n_tables":len(TABLES),"main_figures":MAIN,"appendix_figures":APP,"tables":TABLES,"items":[]}
for fid in MAIN+APP:
    manifest["items"].append({"id":fid,"contract":rel(OUT/"contracts"/f"{fid}.json"),"snapshot":rel(OUT/"data-snapshots"/f"{fid}.csv"),"svg":rel(OUT/"figures"/f"{fid}.svg"),"png":rel(OUT/"figures"/f"{fid}.png"),"png_sha256":sha(OUT/"figures"/f"{fid}.png"),"svg_sha256":sha(OUT/"figures"/f"{fid}.svg")})
for fid in TABLES: manifest["items"].append({"id":fid,"contract":rel(OUT/"contracts"/f"{fid}.json"),"csv":rel(OUT/"figures"/f"{fid}.csv"),"markdown":rel(OUT/"figures"/f"{fid}.md")})
(OUT/"figure-manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({"figures":len(MAIN)+len(APP),"tables":len(TABLES)},ensure_ascii=False))
