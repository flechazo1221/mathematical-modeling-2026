from pathlib import Path
import csv, json, sys
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
TOOL = Path(r"C:\Users\Lenovo\.codex\skills\math-modeling-v2\tools\figure\scripts")
sys.path.insert(0, str(TOOL))
from layout_tools import (apply_compact_paper_style, style_compact_axis,
                          add_shared_legend_safe, set_grouped_category_ticks,
                          finalize_compact_figure, add_panel_labels)
from visual_qa import audit_layout

apply_compact_paper_style(lang="zh")
COL = {"B":"#A6A6A6", "F":"#FC8D62", "P":"#8DA0CB",
       "raw":"#0072B2", "reasoned":"#E69F00"}
MARK = {"B":"o", "F":"s", "P":"^", "raw":"o", "reasoned":"s"}
audit = {}


def read(name):
    with (ROOT/"04-compute/results"/name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def save(fig, name):
    issues = audit_layout(fig)
    audit[name] = [{"severity":s,"message":m} for s,m in issues]
    if any(s == "FAIL" for s,_ in issues):
        raise RuntimeError(f"{name}: {issues}")
    png=OUT/f"{name}.png"; svg=OUT/f"{name}.svg"
    fig.savefig(png,dpi=360,bbox_inches="tight",pad_inches=.04,facecolor="white")
    fig.savefig(svg,bbox_inches="tight",pad_inches=.04)
    prev=OUT/f"{name}-gray.png"
    Image.open(png).convert("L").save(prev,dpi=(360,360))
    plt.close(fig)


def recovery_summary():
    data=read("synthetic_recovery.csv"); stats={}
    for m in ("B","F","P"):
        rr=[r for r in data if r["model"]==m]; vals=[float(r["relative_error"]) for r in rr if r["relative_error"]]
        stats[m]={"pass":sum(r["pass_recovery"]=="True" for r in rr),"fail":sum(not r["relative_error"] for r in rr),"median":float(np.median(vals)),"max":max(vals)}
    fig,axs=plt.subplots(1,2,figsize=(7.2,3.0))
    x=np.arange(3); models=["B","F","P"]
    axs[0].bar(x-.18,[stats[m]["pass"]/144*100 for m in models],.36,color=[COL[m] for m in models],edgecolor="#444",linewidth=.45,label="通过率")
    axs[0].bar(x+.18,[stats[m]["fail"]/144*100 for m in models],.36,color="white",edgecolor=[COL[m] for m in models],linewidth=1.2,hatch="///",label="失败率")
    axs[0].set_xticks(x,models); axs[0].set_ylim(0,108); axs[0].set_ylabel("占全部144次运行的比例 (%)"); axs[0].set_xlabel("模型")
    for i,m in enumerate(models):
        axs[0].text(i-.18,stats[m]["pass"]/1.44+2,f"{stats[m]['pass']}/144",ha="center",fontsize=7)
        if stats[m]["fail"]: axs[0].text(i+.18,stats[m]["fail"]/1.44+2,f"{stats[m]['fail']}/144",ha="center",fontsize=7)
    style_compact_axis(axs[0])
    axs[1].axis("off")
    lines=[("B","中位误差 57.21\n最大误差 803.6"),("F","中位误差 0.02088\n最大误差 1.00018（约100.018%）"),("P",r"中位误差 $9.019\times10^{-5}$"+"\n成功结果最大误差 0.001051")]
    y=.84
    for m,t in lines:
        axs[1].text(.06,y,{"B":"●","F":"■","P":"▲"}[m],color=COL[m],fontsize=10,va="center",transform=axs[1].transAxes)
        axs[1].text(.14,y,f"{m}\n{t}",fontsize=7.6,va="center",linespacing=1.25,transform=axs[1].transAxes); y-=.25
    axs[1].text(.05,.015,"阈值：相对误差 ≤ 2.0；结构可行性 ≠ 真实准确度",fontsize=7.0,transform=axs[1].transAxes)
    add_shared_legend_safe(fig,[axs[0]],ncol=2,y=.99)
    fig.suptitle("合成恢复总览：通过、失败与极端值同时呈现",y=.88)
    finalize_compact_figure(fig,top=.72,bottom=.18,left=.09,wspace=.18)
    add_panel_labels(fig,axs,style="paren",x_offset_pt=-8,y_offset_pt=0,ha="right")
    save(fig,"sample-4-recovery-summary")


def sensitivity_matrix():
    data=[r for r in read("validation_metrics.csv") if r["validation"]=="raw_reasoned_pair"]
    models=["B","F","P"]
    keys=sorted({(r["material"],r["window"],r["angle_deg"]) for r in data},key=lambda k:(k[0],k[1],float(k[2])))
    z=np.array([[100*float(next(r["relative_difference"] for r in data if r["model"]==m and (r["material"],r["window"],r["angle_deg"])==k) or 0) for k in keys] for m in models])
    fig,ax=plt.subplots(figsize=(7.2,2.8))
    im=ax.pcolormesh(np.arange(z.shape[1]+1)-.5,np.arange(z.shape[0]+1)-.5,z,cmap="cividis",vmin=0,vmax=max(5,z.max()),shading="flat",edgecolors="white",linewidth=.35)
    ax.set_xlim(-.5,z.shape[1]-.5); ax.set_ylim(z.shape[0]-.5,-.5)
    for i in range(z.shape[0]):
        for j in range(z.shape[1]): ax.text(j,i,f"{z[i,j]:.3g}",ha="center",va="center",fontsize=6.3,color="white" if z[i,j]>2.6 else "black")
    set_grouped_category_ticks(ax,[f"{a}°" for mat,w,a in keys],[("Si",0,5),("SiC",6,11)],rotation=0,group_y=-.20)
    ax.set_yticks(range(3),models); ax.set_ylabel("模型"); ax.set_xlabel("每个材料内依次为 W1、W2、W3",labelpad=27)
    cb=fig.colorbar(im,ax=ax,pad=.02,shrink=.82); cb.set_label("raw/reasoned相对差 (%)")
    if getattr(cb, "solids", None) is not None:
        cb.solids.set_rasterized(False)
    fig.suptitle("掩码敏感性矩阵：全部模型与组合，不重复长标签",y=.95)
    finalize_compact_figure(fig,top=.82,bottom=.29,left=.10,right=.94)
    save(fig,"sample-5-mask-sensitivity-matrix")


def anomaly_evidence():
    data=read("mask_exclusions.csv"); high=[r for r in data if r["reason"]=="R_GT_100"]; zero=[r for r in data if r["reason"]=="FIRST_ROW_ZERO"]
    fig,axs=plt.subplots(1,2,figsize=(7.2,2.85),gridspec_kw={"width_ratios":[1.65,1]})
    axs[0].scatter([float(r["sigma_cm_inv"]) for r in high],[float(r["R_percent"]) for r in high],s=12,facecolors="none",edgecolors="#FC8D62",linewidth=.8,label="附件2：R>100%")
    axs[0].scatter([float(r["sigma_cm_inv"]) for r in zero],[float(r["R_percent"]) for r in zero],s=28,marker="x",color="#8DA0CB",linewidth=1.2,label="四附件首零值")
    axs[0].set_xlabel(r"波数 $\sigma$ (cm$^{-1}$)"); axs[0].set_ylabel("原始反射率 R (%)"); style_compact_axis(axs[0])
    axs[1].axis("off"); axs[1].text(.05,.78,"262",color="#FC8D62",fontsize=20,weight="bold",transform=axs[1].transAxes); axs[1].text(.38,.80,"个 R>100% 原值\n全部保留，未裁剪到100%",fontsize=8,va="center",transform=axs[1].transAxes)
    axs[1].text(.05,.48,"4",color="#8DA0CB",fontsize=20,weight="bold",transform=axs[1].transAxes); axs[1].text(.24,.50,"个附件首零值\n与超100%点分开编码",fontsize=8,va="center",transform=axs[1].transAxes)
    axs[1].text(.08,.16,"异常成因未知；不直接归因于多光束。",fontsize=7.5,transform=axs[1].transAxes)
    add_shared_legend_safe(fig,[axs[0]],ncol=2,y=.99)
    fig.suptitle("异常数据证据卡：位置、原值与计数并列",y=.88)
    finalize_compact_figure(fig,top=.72,bottom=.18,left=.09,wspace=.16)
    add_panel_labels(fig,axs,style="paren",x_offset_pt=-8,y_offset_pt=0,ha="right")
    save(fig,"sample-6-anomaly-evidence-card")


def conditional_formula():
    data=[r for r in read("conditional_sensitivity.csv") if r["mask"]=="raw" and not r["note"]]
    fig,axs=plt.subplots(1,2,figsize=(7.2,2.9),gridspec_kw={"width_ratios":[1.2,1]})
    ax=axs[0]; x=np.arange(3)
    for j,(mat,mk) in enumerate((("SiC","o"),("Si","s"))):
        for ang,ls,off in (("10","-",-.07),("15","--",.07)):
            sub=sorted([r for r in data if r["material"]==mat and r["angle_deg"]==ang],key=lambda r:r["window"])
            ax.scatter(x+off,[float(r["q_um"]) for r in sub],marker=mk,facecolor=COL["raw"] if mat=="SiC" else COL["reasoned"],edgecolor="#333",linewidth=.4,label=f"{mat}, {ang}°")
    ax.set_xticks(x,["W1","W2","W3"]); ax.set_xlabel("固定窗口"); ax.set_ylabel("光学厚度 q (μm)"); style_compact_axis(ax)
    axs[1].axis("off")
    axs[1].text(.5,.80,r"$d(n)=\dfrac{q}{\sqrt{n^2-\sin^2\theta_0}}$",ha="center",fontsize=15,transform=axs[1].transAxes)
    axs[1].text(.5,.45,r"有效域：$n>\sin\theta_0$",ha="center",fontsize=9,transform=axs[1].transAxes)
    axs[1].text(.5,.18,"折射率数值边界尚未批准\n因此不报告唯一真实厚度",ha="center",fontsize=8,linespacing=1.5,transform=axs[1].transAxes)
    add_shared_legend_safe(fig,[ax],ncol=4,y=.99)
    fig.suptitle("条件厚度表达：观测q与公式边界分区呈现",y=.88)
    finalize_compact_figure(fig,top=.72,bottom=.18,left=.09,wspace=.18)
    add_panel_labels(fig,axs,style="paren",x_offset_pt=-8,y_offset_pt=0,ha="right")
    save(fig,"sample-7-conditional-formula-card")


if __name__ == "__main__":
    recovery_summary(); sensitivity_matrix(); anomaly_evidence(); conditional_formula()
    (OUT/"layout-audit.json").write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding="utf-8")
