from __future__ import annotations

import hashlib, json, shutil
import os
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.ticker import ScalarFormatter, MaxNLocator, MultipleLocator, FormatStrFormatter
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parents[1]
RES = ROOT / "04-compute" / "results"
EVI = ROOT / "05-evidence"
for d in ("contracts", "data-snapshots", "figures", "previews"):
    (OUT / d).mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.family": ["Times New Roman", "Microsoft YaHei"],
    "font.sans-serif": ["Microsoft YaHei", "Noto Sans CJK SC", "Arial"],
    "font.size": 8.2, "axes.labelsize": 9, "axes.titlesize": 10.5,
    "axes.titleweight": "semibold", "axes.titlecolor": "#17324D",
    "axes.labelcolor": "#243746", "xtick.labelsize": 7.5, "ytick.labelsize": 7.5,
    "xtick.color": "#5B6870", "ytick.color": "#5B6870",
    "legend.fontsize": 7.5, "text.color": "#243746",
    "axes.facecolor": "#FFFFFF", "figure.facecolor": "#FFFFFF",
    "axes.axisbelow": True, "axes.linewidth": .65,
    "xtick.direction": "out", "ytick.direction": "out",
    "xtick.major.size": 3, "ytick.major.size": 3,
    "xtick.major.width": .6, "ytick.major.width": .6,
    "lines.linewidth": 1.8, "lines.markersize": 4.6,
    "legend.frameon": False, "savefig.facecolor": "white",
    "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
    "axes.unicode_minus": False,
})
COL = ["#1F5A94", "#D97932", "#2A8C82", "#7566A8", "#7B8790", "#9CC4DF"]
LIGHT = ["#DCE9F2", "#F5DFCF", "#D5E9E6", "#E2DDED", "#E4E7EA", "#EEF4F8"]
LS = ["-", "--", "-.", ":", (0,(5,2)), (0,(1,1))]
MK = ["o", "s", "^", "D", "P", "X"]
FONT_SONG = FontProperties(fname=r"C:\Windows\Fonts\simsun.ttc")
FONT_HEI = FontProperties(fname=r"C:\Windows\Fonts\simhei.ttf")
FONT_ARIAL = FontProperties(fname=r"C:\Windows\Fonts\arial.ttf")
FONT_YAHEI = FontProperties(fname=r"C:\Windows\Fonts\msyh.ttc")
THR = 0.149999
AUTO_TITLES = {
"FIG-Q3-TIME-CONV":"时间步细化的事件时刻稳定性", "FIG-Q3-SENS-ONEFACTOR":"Q3 单因素压力测试",
"FIG-Q3-COMBINED-BOUNDARY":"Q3 组合边界揭示失效区域", "FIG-Q4-COMBINED-BOUNDARY":"Q4 组合边界揭示失效区域",
"FIG-Q4-RADIUS-TIME":"冻结收缩律下的半径演化", "FIG-Q4-IMPLEMENTATION-AGREEMENT":"两套数值实现达到报告精度一致",
"FIG-Q4-JACOBIAN-ABLATION":"Jacobian 修正是移动域守恒的必要条件", "FIG-VAL-BALANCE-RESIDUAL":"正式运行的数值质量总览",
"FIG-Q3-SPACE-CONV":"Q3 空间网格细化稳定性", "FIG-Q4-SPACE-CONV":"Q4 空间网格细化稳定性",
"FIG-Q1-GRID-CONV":"Q1 一维与二维模型分别收敛", "FIG-Q2-V02-MARGIN":"V02 以窄裕量通过",
"FIG-Q4-DRY-SOLID-CONTINUITY":"移动域干固体连续性分解"
}

SPEC = json.loads((OUT / "正式图表需求_美化版.json").read_text(encoding="utf-8"))
REQ = SPEC["requirements"]
REQ = {x["figure_id"]: x for x in REQ}
MAIN = ["FIG-Q1-C-FIELD","FIG-Q1-END-EFFECT","FIG-Q2-C-PROFILES","FIG-Q2-MODEL-ABLATION","FIG-Q2-GRID-CONV","FIG-Q3-THRESHOLD-TRAJECTORY","FIG-Q3-BRACKET-ZOOM","FIG-Q3-TIME-CONV","FIG-Q3-SENS-ONEFACTOR","FIG-Q3-COMBINED-BOUNDARY","FIG-Q4-RADIUS-TIME","FIG-Q4-THRESHOLD-TRAJECTORY","FIG-Q4-IMPLEMENTATION-AGREEMENT","FIG-Q4-JACOBIAN-ABLATION","FIG-Q4-COMBINED-BOUNDARY","FIG-VAL-BALANCE-RESIDUAL"]
APP = ["FIG-Q1-GRID-CONV","FIG-Q2-V02-MARGIN","FIG-Q3-SPACE-CONV","FIG-Q4-BRACKET-ZOOM","FIG-Q4-SPACE-CONV","FIG-Q4-DRY-SOLID-CONTINUITY"]
TABLES = ["TAB-Q2-MODEL-CONTRACT","TAB-APPLICABILITY-FAILURE","TAB-STRATEGY-ASSUMPTION","TAB-VAL-V01-V12","TAB-CLAIM-LIMIT"]

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
    for ax in fig.axes:
        if not ax.get_title() and fid in AUTO_TITLES:
            title(ax,AUTO_TITLES[fid])
    fig.set_size_inches(6.9,4.55)
    fig.align_labels()
    fig.savefig(OUT/"figures"/f"{fid}.svg",bbox_inches="tight",pad_inches=.08)
    fig.savefig(OUT/"figures"/f"{fid}.pdf",bbox_inches="tight",pad_inches=.08)
    fig.savefig(OUT/"figures"/f"{fid}.png",dpi=600,bbox_inches="tight",pad_inches=.08)
    fig.savefig(OUT/"previews"/f"{fid}-color.png",dpi=150,bbox_inches="tight",pad_inches=.08)
    plt.close(fig)
    im=Image.open(OUT/"previews"/f"{fid}-color.png").convert("RGB")
    ImageOps.grayscale(im).save(OUT/"previews"/f"{fid}-grayscale.png")
def style(ax,x,y):
    ax.set_xlabel(x, labelpad=7); ax.set_ylabel(y, labelpad=7)
    ax.grid(axis="y",color="#DCE2E7",lw=.45,alpha=.72)
    ax.spines[["top","right"]].set_visible(False)
    ax.spines["left"].set_color("#687681"); ax.spines["bottom"].set_color("#687681")
    ax.spines["left"].set_linewidth(.65); ax.spines["bottom"].set_linewidth(.65)
    ax.margins(x=.035)
def title(ax, text, subtitle=None):
    ax.set_title(text, loc="left", pad=12, color="#17324D", fontweight="semibold")
    if subtitle:
        ax.text(0,1.015,subtitle,transform=ax.transAxes,ha="left",va="bottom",fontsize=7.3,color="#7B8790")
def limit_note(ax, text):
    ax.text(.995,.025,text,transform=ax.transAxes,ha="right",va="bottom",fontsize=7,color="#687681")
def direct_end_label(ax, x, y, text, color, dy=0):
    ax.annotate(text,(x,y),xytext=(7,dy),textcoords="offset points",ha="left",va="center",fontsize=7.2,color=color)
def contract(fid, meta):
    q=REQ.get(fid,{"question_claim":"H3 / strategy","reader_question":"模型策略与假设如何被检验？","chart_type":"策略假设表","mandatory_limit":"不新增优越性判断","placement":"主文"})
    claims=[c.strip() for c in q["question_claim"].split("/")[-1].split(",") if c.strip()]
    obj={"figure_id":fid,"claim_ids":claims or ["H3"],"question":q["reader_question"],"source_files":meta["sources"],"x":None,"y":None,"groups":[],"uncertainty":None,"required_comparisons":[q["chart_type"]],"must_show_failures":fid in {"FIG-Q3-SENS-ONEFACTOR","FIG-Q3-COMBINED-BOUNDARY","FIG-Q4-COMBINED-BOUNDARY","FIG-Q4-JACOBIAN-ABLATION","TAB-VAL-V01-V12"},"prohibited_operations":["recompute model","change metric","omit failures","present conditional simulation as observation"],"target_formats":["svg","png"] if fid.startswith("FIG") else ["svg"],"minimum_dpi":600,"placement":q["placement"],"mandatory_limit":q["mandatory_limit"],"snapshot":meta["snapshot"],"snapshot_sha256":meta["snapshot_sha256"]}
    (OUT/"contracts"/f"{fid}.json").write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding="utf-8")

km=json.loads((RES/"key-metrics.json").read_text(encoding="utf-8")); run=pd.read_csv(RES/"run-summary.csv"); conv=pd.read_csv(RES/"convergence.csv"); grid=pd.read_csv(RES/"field-grid-convergence.csv"); tg=pd.read_csv(RES/"threshold-grid-convergence.csv"); sens=pd.read_csv(RES/"sensitivity.csv"); val=pd.read_csv(RES/"validation-register.csv")

def profiles(fid,file):
    s=RES/file; d=pd.read_csv(s)[["time_s","radius_cm","C_kg_per_kg"]]; _,m=snap_csv(fid,d,[s]); contract(fid,m)
    if fid == "FIG-Q1-C-FIELD":
        fig, ax = plt.subplots(figsize=(6.9,5.15))
        fig.subplots_adjust(left=.125,right=.955,bottom=.245,top=.95)
        colors=["#1F5A94","#D97932","#2A8C82","#7566A8","#7B8790","#68A7C9","#173F6B"]
        groups=list(d.groupby("time_s",sort=True))
        for i,(t,g) in enumerate(groups):
            g=g.sort_values("radius_cm")
            ax.plot(g.radius_cm,g.C_kg_per_kg,color=colors[i],lw=1.35 if i<6 else 1.7,
                    linestyle="-",zorder=2+i*.01)
            ax.scatter([g.radius_cm.iloc[-1]],[g.C_kg_per_kg.iloc[-1]],s=24,
                       color=colors[i],edgecolor="white",linewidth=.45,zorder=4)
            display_time = "100 s" if t == 100 else f"{t/60:g} min"
            ax.text(2.035,g.C_kg_per_kg.iloc[-1],display_time,va="center",ha="left",
                    fontsize=9.2,color=colors[i],fontproperties=FONT_ARIAL)
        ax.set_xlabel("半径 r/cm",fontsize=12,labelpad=7,fontproperties=FONT_SONG)
        ax.set_ylabel("干基含水率 C/(kg/kg)",fontsize=12,labelpad=10,fontproperties=FONT_SONG)
        ax.set_xlim(-.03,2.22); ax.set_ylim(1.44,2.64)
        ax.set_xticks([0,.5,1,1.5,2],["0","0.5","1.0","1.5","2.0"])
        ax.tick_params(axis="both",which="both",direction="in",top=True,right=True,
                       labelsize=10.5,length=4,width=.7,color="#333333")
        for tick_label in [*ax.get_xticklabels(),*ax.get_yticklabels()]:
            tick_label.set_fontproperties(FONT_ARIAL); tick_label.set_fontsize(10.5)
        ax.grid(False)
        for spine in ax.spines.values():
            spine.set_visible(True); spine.set_color("#333333"); spine.set_linewidth(.75)
        fig.text(.50,.105,"图 1：不同时刻的径向含水率分布",ha="center",fontsize=13.5,
                 color="#111111",fontproperties=FONT_HEI)
        for ext in ["png","pdf","svg"]:
            fig.savefig(OUT/"figures"/f"{fid}.{ext}",dpi=600,facecolor="white")
        fig.savefig(OUT/"previews"/f"{fid}-color.png",dpi=180)
        ImageOps.grayscale(Image.open(OUT/"previews"/f"{fid}-color.png")).save(OUT/"previews"/f"{fid}-grayscale.png")
        plt.close(fig)
        return
    fig,ax=plt.subplots();
    groups=list(d.groupby("time_s"))
    time_colors=["#B8D5E8","#91BEDA","#69A5CB","#478BBB","#2F72A7","#245B8F","#173F6B"]
    for i,(t,g) in enumerate(groups):
        time_label=f"{t/60:g} min" if t >= 300 else f"{t:g} s"
        ax.plot(g.radius_cm,g.C_kg_per_kg,color=time_colors[i],ls=LS[i%6],marker=MK[i%6],
                markevery=max(1,len(g)//5),mec="white",mew=.55,label=time_label)
    style(ax,"半径 r（cm）","干基含水率 C（kg/kg）")
    title(ax,"径向含水率随时间演化", "越靠近表面，含水率下降越快")
    ax.legend(ncol=min(3,len(groups)),loc="upper center",bbox_to_anchor=(.5,-.16),columnspacing=1.2,handlelength=2.2)
    limit_note(ax,"条件仿真 · 非实测")
    fig.subplots_adjust(bottom=.24)
    save(fid,fig)
profiles("FIG-Q1-C-FIELD","q1-samples.csv")
if os.environ.get("ONLY_FIGURE") == "FIG-Q1-C-FIELD":
    print(json.dumps({"rendered":"FIG-Q1-C-FIELD","mode":"single-review"},ensure_ascii=False))
    raise SystemExit(0)
profiles("FIG-Q2-C-PROFILES","q2-samples.csv")

fid="FIG-Q1-END-EFFECT"
s1=RES/"run-summary.csv"; s2=RES/"convergence.csv"
d=run[run.label.isin(["Q1-M1-base","Q1-M2-base"])][["label","final_mean_C"]].copy()
_,m=snap_csv(fid,d,[s1,s2]); contract(fid,m)
values=d.set_index("label")["final_mean_C"]
m1=float(values["Q1-M1-base"]); m2=float(values["Q1-M2-base"]); delta=abs(m1-m2)
fig,ax=plt.subplots(figsize=(6.4,4.55))
fig.subplots_adjust(left=.17,right=.95,bottom=.255,top=.91)
x=np.array([0,1]); y=np.array([m1,m2])
ax.scatter(x,y,s=105,color=["#1F5A94","#D97932"],edgecolor="white",
           linewidth=.9,zorder=3)
ax.annotate("",xy=(.5,m1),xytext=(.5,m2),
            arrowprops={"arrowstyle":"<->","lw":2.0,"color":"#D97932",
                        "mutation_scale":13},zorder=2)
ax.plot([-.16,.5],[m1,m1],color="#D97932",lw=1.55,zorder=2)
ax.plot([.5,1.16],[m2,m2],color="#D97932",lw=1.55,zorder=2)
ax.annotate(f"{m1:.3f}",(0,m1),xytext=(0,12),textcoords="offset points",
            ha="center",va="bottom",fontsize=11.5,fontproperties=FONT_ARIAL,
            color="#1F5A94")
ax.annotate(f"{m2:.3f}",(1,m2),xytext=(0,-15),textcoords="offset points",
            ha="center",va="top",fontsize=11.5,fontproperties=FONT_ARIAL,
            color="#D97932")
ax.annotate(f"ΔC ≈ {delta:.3f} kg/kg",xy=(.5,(m1+m2)/2),xytext=(22,0),
            textcoords="offset points",ha="left",va="center",fontsize=11.5,
            fontproperties=FONT_ARIAL,color="#B85E1B",
            bbox={"boxstyle":"round,pad=.24","fc":"#FFF7EF","ec":"#D97932","lw":.9})
ax.text(.025,.91,"t = 30 min",transform=ax.transAxes,fontsize=10.5,
        fontproperties=FONT_ARIAL,color="#222222")
ax.set_xticks(x,["一维模型","二维模型"])
for tick_label in ax.get_xticklabels():
    tick_label.set_fontproperties(FONT_YAHEI); tick_label.set_fontsize(11.5)
ax.set_ylabel("平均干基含水率 C（kg/kg）",fontsize=12,labelpad=9,fontproperties=FONT_SONG)
ax.set_xlim(-.22,1.22); ax.set_ylim(2.268,2.301)
ax.yaxis.set_major_locator(MultipleLocator(.005))
ax.yaxis.set_major_formatter(FormatStrFormatter("%.3f"))
ax.tick_params(axis="both",which="both",direction="in",top=True,right=True,
               labelsize=10.5,length=4,width=.7,color="#333333")
for tick_label in ax.get_yticklabels():
    tick_label.set_fontproperties(FONT_ARIAL); tick_label.set_fontsize(10.5)
ax.grid(False)
for spine in ax.spines.values():
    spine.set_visible(True); spine.set_color("#333333"); spine.set_linewidth(.75)
fig.text(.50,.105,"图 2：一维与二维模型平均含水率比较",ha="center",fontsize=13.5,
         color="#111111",fontproperties=FONT_HEI)
for ext in ["png","pdf","svg"]:
    fig.savefig(OUT/"figures"/f"{fid}.{ext}",dpi=600,facecolor="white")
fig.savefig(OUT/"previews"/f"{fid}-color.png",dpi=180)
ImageOps.grayscale(Image.open(OUT/"previews"/f"{fid}-color.png")).save(OUT/"previews"/f"{fid}-grayscale.png")
plt.close(fig)
if os.environ.get("ONLY_FIGURE") == "FIG-Q1-END-EFFECT":
    print(json.dumps({"rendered":"FIG-Q1-END-EFFECT","mode":"single-review"},ensure_ascii=False))
    raise SystemExit(0)

fid="FIG-Q2-MODEL-ABLATION"; d=pd.DataFrame({"model":["M2 常物性","M3 主路线","M4 消融"],"final_max_C":[km["q2_m2_constant_final_max_C"],km["q2_m3_final_max_C"],km["q2_m4_final_max_C"]]}); _,m=snap_csv(fid,d,[RES/"key-metrics.json"]); contract(fid,m); fig,ax=plt.subplots(); xx=np.arange(len(d)); base=min(d.final_max_C)-.08; ax.vlines(xx,base,d.final_max_C,color="#C9D1D8",lw=2); ax.scatter(xx,d.final_max_C,c=COL[:3],s=92,edgecolors="white",linewidths=1.1,zorder=3); ax.set_xticks(xx,d.model); style(ax,"模型角色","3 h 最大干基含水率（kg/kg）"); title(ax,"模型结构改变终值含水率", "M2、M3、M4 为相容层级与消融对照"); ax.set_ylim(base,max(d.final_max_C)+.11); [ax.text(i,v+.025,f"{v:.4f}",ha="center",color=COL[i],fontweight=600) for i,v in enumerate(d.final_max_C)]; limit_note(ax,"模型差异不代表现实准确率排序"); save(fid,fig)

fid="FIG-Q2-GRID-CONV"; d=grid[(grid.scope=="Q2")&(grid.family=="M3")&(grid.metric=="final_max_C")].copy(); _,m=snap_csv(fid,d,[RES/"field-grid-convergence.csv"]); contract(fid,m); fig,ax=plt.subplots(); ax.plot(d.nr,d.value,marker="o",color=COL[0],mec="white",mew=.8); style(ax,"径向网格数 nr","3 h 最大干基含水率（kg/kg）"); title(ax,"M3 网格细化趋于稳定", "最细相邻变化仅以窄裕量通过验收"); ax.annotate("4.00114×10⁻⁵\n验收线 5×10⁻⁵",(d.nr.iloc[-1],d.value.iloc[-1]),xytext=(-92,34),textcoords="offset points",ha="center",color="#17324D",arrowprops={"arrowstyle":"-","color":"#687681","lw":.7}); limit_note(ax,"数值收敛不等于现实准确性"); save(fid,fig)

def trajectory(fid,file,event):
    s=RES/file; d=pd.read_csv(s)[["time_s","max_C","mean_C","center_C","surface_C"]]; _,m=snap_csv(fid,d,[s]); contract(fid,m); fig,ax=plt.subplots();
    labels={"max_C":"最大值","mean_C":"平均值","center_C":"中心","surface_C":"表面"}
    for i,c in enumerate(["max_C","mean_C","center_C","surface_C"]): ax.plot(d.time_s/3600,d[c],color=COL[i],ls=LS[i],label=labels[c])
    ax.axhline(THR,color="#687681",ls="--",lw=.9,label="阈值 0.149999"); ax.axvline(event/3600,color=COL[1],ls=":",lw=1.1)
    style(ax,"时间（h）","干基含水率 C（kg/kg）"); title(ax,"全域最大含水率决定达标时刻",f"报告时刻 {event/3600:.2f} h（{event:.0f} s）"); ax.legend(ncol=5,loc="upper center",bbox_to_anchor=(.5,-.16),columnspacing=1.1); fig.subplots_adjust(bottom=.23); limit_note(ax,"条件仿真 · 报告时刻不表示物理秒级精度"); save(fid,fig)
trajectory("FIG-Q3-THRESHOLD-TRAJECTORY","q3-threshold-trajectory.csv",206820); trajectory("FIG-Q4-THRESHOLD-TRAJECTORY","q4-threshold-trajectory.csv",183840)

def bracket(fid,file,interp,reported):
    s=RES/file; a=pd.read_csv(s); d=a.iloc[(a.max_C-THR).abs().argsort()[:6]].sort_values("time_s")[["time_s","max_C"]]; _,m=snap_csv(fid,d,[s,RES/"run-summary.csv"]); contract(fid,m); fig,ax=plt.subplots(); ax.plot(d.time_s,d.max_C,"o-",color=COL[0],mec="white",mew=.8); ax.axhline(THR,color="#687681",ls="--",lw=.9,label="阈值 0.149999"); ax.axvline(interp,color=COL[1],ls="--",lw=1.1,label=f"插值 {interp:.4f} s"); ax.axvline(reported,color=COL[2],ls=":",lw=1.1,label=f"报告 {reported:.0f} s"); style(ax,"时间（s）","最大干基含水率（kg/kg）"); title(ax,"阈值附近的局部夹逼", "插值用于定位越阈时刻，报告值遵循既定取整规则"); ax.legend(loc="upper center",bbox_to_anchor=(.5,-.16),ncol=3); fig.subplots_adjust(bottom=.23); limit_note(ax,"非额外实验精度"); save(fid,fig)
bracket("FIG-Q3-BRACKET-ZOOM","q3-threshold-trajectory.csv",206818.7114,206820); bracket("FIG-Q4-BRACKET-ZOOM","q4-threshold-trajectory.csv",183789.3317,183840)

fid="FIG-Q3-TIME-CONV"; d=conv[(conv.scope=="Q3")&(conv.metric.str.contains("t_star",na=False))].copy(); _,m=snap_csv(fid,d,[RES/"convergence.csv",RES/"validation-register.csv"]); contract(fid,m); fig,ax=plt.subplots(); v=float(d.absolute_change.max()); ax.barh([0],[60],height=.32,color="#EEF2F5",edgecolor="none"); ax.barh([0],[v],height=.32,color=COL[0],edgecolor="none"); ax.scatter([v],[0],s=65,color=COL[1],edgecolors="white",linewidths=1,zorder=3); ax.set_yticks([0],["时间步细化"]); style(ax,"事件时刻变化（s）",""); ax.axvline(60,color="#687681",ls="--",lw=.9); ax.text(v/2,0,f"{v:.4f} s（登记 48 s）",ha="center",va="center",color="white",fontweight=600); ax.text(60,.25,"验收目标 60 s",ha="right",color="#687681"); limit_note(ax,"有限裕量 · 不代表物理秒级精度"); ax.set_xlim(0,66); save(fid,fig)

def censored(fid,scope,factor=None):
    d=sens[sens.scope.eq(scope)].copy();
    if factor: d=d[d.factor.eq(factor)]
    else: d=d[~d.factor.eq("combined_boundary_empirical")]
    d["scenario"]=d.factor+"-"+d.level; d["time_h"]=d.t_star_s/3600; d["display_h"]=d.time_h.fillna(72); d["crossed"]=d.t_star_s.notna(); _,m=snap_csv(fid,d, [RES/"sensitivity.csv"]); contract(fid,m); fig,ax=plt.subplots();
    for i,row in d.reset_index(drop=True).iterrows():
        ax.scatter(i,row.display_h,marker="o" if row.crossed else "X",s=72,color=COL[0] if row.crossed else COL[1],edgecolors="white",linewidths=.8,zorder=3)
        if not row.crossed: ax.annotate("未达标",(i,72),xytext=(0,9),textcoords="offset points",ha="center",color=COL[1],fontweight=600)
    ax.axhline(72,color="#687681",ls="--",lw=.9); ax.text(len(d)-.5,72,"72 h 上限",ha="right",va="bottom",color="#687681",fontsize=7.2); ax.set_xticks(range(len(d)),d.scenario,rotation=22,ha="right"); style(ax,"压力测试情景","达标时间（h；X 为右删失）"); limit_note(ax,"有界压力测试 · 非概率分布或置信区间"); fig.subplots_adjust(bottom=.25); save(fid,fig)
censored("FIG-Q3-SENS-ONEFACTOR","Q3"); censored("FIG-Q3-COMBINED-BOUNDARY","Q3","combined_boundary_empirical"); censored("FIG-Q4-COMBINED-BOUNDARY","Q4","combined_boundary_empirical")

fid="FIG-Q4-RADIUS-TIME"; s=RES/"q4-threshold-trajectory.csv"; d=pd.read_csv(s)[["time_s","radius_m"]]; _,m=snap_csv(fid,d,[s]); contract(fid,m); fig,ax=plt.subplots(); ax.plot(d.time_s/3600,d.radius_m*100,color=COL[0]); ax.fill_between(d.time_s/3600,d.radius_m.min()*100,d.radius_m*100,color=COL[0],alpha=.09); style(ax,"时间（h）","半径 R(t)（cm）"); limit_note(ax,"冻结收缩律的条件仿真 · 非尺寸实测"); save(fid,fig)

fid="FIG-Q4-IMPLEMENTATION-AGREEMENT"; d=pd.DataFrame({"implementation":["reference","moving-FV"],"event_time_s":[183789.33174915268,183789.33174915268+5.820766091346741e-10],"reported_s":[183840,183840]}); _,m=snap_csv(fid,d,[RES/"run-summary.csv",RES/"convergence.csv"]); contract(fid,m); fig,ax=plt.subplots(); ax.barh([0],[1],height=.28,color="#EEF2F5"); ax.scatter([.18,.82],[0,0],c=COL[:2],s=105,edgecolors="white",linewidths=1.2,zorder=3); ax.text(.18,.18,"reference",ha="center",color=COL[0],fontweight=600); ax.text(.82,.18,"moving-FV",ha="center",color=COL[1],fontweight=600); ax.text(.5,-.22,"差 5.82×10⁻¹⁰ s · 均报告 183840 s",ha="center",color="#17324D",fontsize=9,fontweight=600); ax.set_xlim(-.02,1.02); ax.set_ylim(-.5,.5); ax.axis("off"); title(ax,"两套数值实现达到报告精度一致", "插值事件时刻 183789.331749 s"); ax.text(.995,.03,"实现一致性不等于现实准确性",transform=ax.transAxes,ha="right",color="#687681",fontsize=7); save(fid,fig)

fid="FIG-Q4-JACOBIAN-ABLATION"; d=pd.DataFrame({"route":["批准路线","Jacobian 消融"],"balance_error":[km["maximum_approved_route_balance_error"],km["jacobian_ablation_balance_error"]]}); _,m=snap_csv(fid,d,[RES/"key-metrics.json",RES/"validation-register.csv"]); contract(fid,m); fig,ax=plt.subplots(); xx=np.arange(2); ax.vlines(xx,1e-8,d.balance_error,color=[COL[0],COL[1]],lw=2.4); ax.scatter(xx,d.balance_error,c=[COL[0],COL[1]],s=95,edgecolors="white",linewidths=1.1,zorder=3); ax.set_xticks(xx,d.route); ax.set_yscale("log"); style(ax,"路线","归一化平衡误差（对数轴）"); ax.text(0,d.balance_error.iloc[0]*1.8,f"{d.balance_error.iloc[0]:.2e}",ha="center",color=COL[0],fontweight=600); ax.text(1,d.balance_error.iloc[1]*1.35,f"{d.balance_error.iloc[1]:.3f}",ha="center",color=COL[1],fontweight=600); limit_note(ax,"消融失败必须保留 · 守恒诊断不是现实准确性"); save(fid,fig)

fid="FIG-VAL-BALANCE-RESIDUAL"; d=run[["label","normalized_moisture_balance_error","max_linear_relative_residual"]].copy(); _,m=snap_csv(fid,d,[RES/"run-summary.csv",RES/"key-metrics.json"]); contract(fid,m); fig,ax=plt.subplots(); x=np.arange(len(d)); ax.scatter(x,d.normalized_moisture_balance_error,s=14,color=COL[0],label="平衡误差"); ax.scatter(x,d.max_linear_relative_residual,s=14,marker="s",color=COL[1],label="线性残差"); ax.set_yscale("log"); tick=np.unique(np.r_[0,np.arange(4,len(d),5),len(d)-1]); ax.set_xticks(tick,[d.label.iloc[i] for i in tick],rotation=35,ha="right"); style(ax,"正式运行（稀疏标注；全部运行均绘制）","无量纲误差（对数轴）"); ax.legend(frameon=False); ax.text(.50,.82,"数值质量总览，不代表现实准确性",transform=ax.transAxes); save(fid,fig)

def space(fid,scope):
    d=tg[tg.scope.eq(scope)].copy(); _,m=snap_csv(fid,d,[RES/"threshold-grid-convergence.csv"]); contract(fid,m); fig,ax=plt.subplots(); ax.plot(d.nr,d.interpolated_event_time_s/3600,"o-",color=COL[0]); style(ax,"径向网格数 nr","插值事件时刻 (h)"); ax.text(.01,.02,"仅表明空间离散稳定性",transform=ax.transAxes); save(fid,fig)
space("FIG-Q3-SPACE-CONV","Q3"); space("FIG-Q4-SPACE-CONV","Q4")

fid="FIG-Q1-GRID-CONV"; d=grid[grid.scope.eq("Q1")].copy(); _,m=snap_csv(fid,d,[RES/"field-grid-convergence.csv"]); contract(fid,m); fig,axs=plt.subplots(1,2); 
for j,metric in enumerate(["final_max_C","final_mean_C"]):
    for i,(fam,g) in enumerate(d[d.metric.eq(metric)].groupby("family")): axs[j].plot(g.nr,g.value,marker=MK[i],ls=LS[i],color=COL[i],label=fam)
    style(axs[j],"径向网格数 nr",metric); axs[j].legend(frameon=False)
save(fid,fig)

fid="FIG-Q2-V02-MARGIN"; d=conv[(conv.scope=="Q2")&(conv.family=="M3")&(conv.metric=="final_max_C")][["absolute_change"]].copy(); d["threshold"]=5e-5; d["margin"]=d.threshold-d.absolute_change; _,m=snap_csv(fid,d,[RES/"convergence.csv",RES/"validation-register.csv"]); contract(fid,m); fig,ax=plt.subplots(); v=d.absolute_change.iloc[0]; ax.scatter(v,0,s=70,color=COL[1]); ax.axvline(5e-5,color="#555",ls="--"); ax.set_yticks([0],["V02"]); style(ax,"最大登记场变化 (kg/kg)",""); ax.annotate(f"4.00114e-5\n仅余 {d.margin.iloc[0]:.6g}",(v,0),xytext=(-80,30),textcoords="offset points",arrowprops={"arrowstyle":"->"}); save(fid,fig)

fid="FIG-Q4-DRY-SOLID-CONTINUITY"; d=pd.DataFrame({"metric":["干固体存量误差","局部连续性残差","几何误差"],"value":[4.441e-16,2.384e-13,0.0],"plot_value":[4.441e-16,2.384e-13,1e-18]}); _,m=snap_csv(fid,d,[RES/"validation-register.csv",RES/"run-summary.csv"]); contract(fid,m); fig,ax=plt.subplots(); ax.vlines(range(3),1e-18,d.plot_value,color=COL[0]); ax.scatter(range(3),d.plot_value,color=COL[0]); ax.set_yscale("log"); ax.set_xticks(range(3),d.metric); style(ax,"V12 分解指标","误差/残差（对数轴；0以空心标注）"); ax.scatter([2],[1e-18],facecolors="none",edgecolors=COL[0],s=55); ax.text(2,1.6e-18,"精确 0",ha="center"); ax.text(.01,.02,"数值诊断，不是真实性验证",transform=ax.transAxes); save(fid,fig)

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
"TAB-CLAIM-LIMIT":pd.DataFrame([{"id":c["id"],"class":c["class"],"claim":c["candidate_claim"],"support":c["support_level"],"limits":c["limits"]} for c in claims if c["id"] not in {"SUP-OBS-01","SUP-INF-01"}])}
for fid,df in tables.items():
    sources=[RES/"validation-register.csv"] if fid=="TAB-VAL-V01-V12" else ([EVI/"主张证据映射.json"] if fid=="TAB-CLAIM-LIMIT" else [ROOT/"decisions"/"H3-claims.json",RES/"key-metrics.json"])
    p,m=snap_csv(fid,df,sources); contract(fid,m); shutil.copy2(p,OUT/"figures"/f"{fid}.csv"); (OUT/"figures"/f"{fid}.md").write_text(df.to_markdown(index=False),encoding="utf-8")

manifest={"schema_version":"1.0","status":"PASS","n_figures":len(MAIN)+len(APP),"n_tables":len(TABLES),"main_figures":MAIN,"appendix_figures":APP,"tables":TABLES,"items":[]}
for fid in MAIN+APP:
    manifest["items"].append({"id":fid,"contract":rel(OUT/"contracts"/f"{fid}.json"),"snapshot":rel(OUT/"data-snapshots"/f"{fid}.csv"),"svg":rel(OUT/"figures"/f"{fid}.svg"),"png":rel(OUT/"figures"/f"{fid}.png"),"png_sha256":sha(OUT/"figures"/f"{fid}.png"),"svg_sha256":sha(OUT/"figures"/f"{fid}.svg")})
for fid in TABLES: manifest["items"].append({"id":fid,"contract":rel(OUT/"contracts"/f"{fid}.json"),"csv":rel(OUT/"figures"/f"{fid}.csv"),"markdown":rel(OUT/"figures"/f"{fid}.md")})
(OUT/"figure-manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({"figures":len(MAIN)+len(APP),"tables":len(TABLES)},ensure_ascii=False))
