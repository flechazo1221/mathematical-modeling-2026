from pathlib import Path
import csv
import numpy as np
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
HERE.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
    "axes.unicode_minus": False,
    "font.size": 8,
    "axes.titlesize": 9,
    "axes.labelsize": 8.4,
    "xtick.labelsize": 7.4,
    "ytick.labelsize": 7.4,
    "legend.fontsize": 7.1,
    "svg.fonttype": "none",
})

PALETTE = ["#FC8D62", "#A6A6A6", "#8DA0CB", "#78C6A3"]


def rows(name):
    with (ROOT / "04-compute/results" / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def polish(ax, grid=True):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="both", pad=1.5)
    if grid:
        ax.grid(axis="y", color="#D9D9D9", linewidth=.55, linestyle="--")
    ax.set_axisbelow(True)


def save(fig, name):
    for ext, kw in (("png", {"dpi": 360}), ("svg", {}), ("pdf", {})):
        fig.savefig(HERE / f"{name}.{ext}", bbox_inches="tight", pad_inches=.04, facecolor="white", **kw)
    plt.close(fig)


def sample_q():
    data=[r for r in rows("observed_all_models.csv") if r["model"]=="F"]
    fig,axs=plt.subplots(1,2,figsize=(7.0,2.75),constrained_layout=False)
    styles=[("10","raw","10° 原始","o"),("10","reasoned","10° 掩码","s"),("15","raw","15° 原始","^"),("15","reasoned","15° 掩码","D")]
    for j,mat in enumerate(("SiC","Si")):
        ax=axs[j]; x=np.arange(3)
        for k,(ang,mask,label,marker) in enumerate(styles):
            sub=sorted([r for r in data if r["material"]==mat and r["angle_deg"]==ang and r["mask"]==mask],key=lambda r:r["window"])
            y=[float(r["q_um"]) for r in sub]; e=[float(r["q_bin_resolution_um"]) for r in sub]
            ax.errorbar(x+(k-1.5)*.09,y,yerr=e,fmt=marker,color=PALETTE[k],markeredgecolor="#333333",markeredgewidth=.4,capsize=2.2,linestyle="none",label=label,zorder=3)
        ax.set_xticks(x,["W1","W2","W3"]); ax.set_title(mat,fontweight="normal",pad=2)
        ax.set_xlabel("固定窗口"); polish(ax); ax.text(.03,.95,f"({chr(97+j)})",transform=ax.transAxes,va="top")
    axs[0].set_ylabel("条件光学厚度 q (μm)")
    handles,labels=axs[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc="upper center",ncol=4,frameon=False,bbox_to_anchor=(.5,.995),columnspacing=.7,handletextpad=.25)
    fig.suptitle("紧凑分面：全部窗口、双角与两种口径",y=.86,fontsize=9)
    fig.subplots_adjust(left=.08,right=.99,bottom=.18,top=.70,wspace=.22)
    save(fig,"sample-1-compact-q")


def sample_robust():
    data=rows("fft_pressure_test.csv")
    variants=[("hann_n_approved","批准F","o","#A6A6A6"),("hann_zp8_diagnostic","Hann+零填充","s","#8DA0CB"),("rectangular_zp8","矩形窗+零填充","^","#FC8D62")]
    fig,axs=plt.subplots(1,2,figsize=(7.0,2.65),sharey=True)
    for j,mat in enumerate(("SiC","Si")):
        ax=axs[j]; base=[r for r in data if r["material"]==mat and r["variant"]=="hann_n_approved"]
        keys=sorted([(r["window"],r["angle_deg"],r["mask"]) for r in base],key=lambda k:(k[0],float(k[1]),k[2]))
        x=np.arange(len(keys))
        for v,label,mk,c in variants:
            lookup={(r["window"],r["angle_deg"],r["mask"]):100*float(r["relative_change_vs_approved_F"]) for r in data if r["material"]==mat and r["variant"]==v}
            ax.plot(x,[lookup[k] for k in keys],color=c,marker=mk,markeredgecolor="#333333",markeredgewidth=.35,linestyle="--" if v!="hann_n_approved" else "none",linewidth=1.25,markersize=3.7,label=label,zorder=3)
        ax.set_xticks(x,[f"{a}{'R' if m=='raw' else 'M'}" for w,a,m in keys],rotation=45,ha="right"); ax.set_title(mat,fontweight="normal",pad=2); ax.set_xlabel("每窗口依次为 10R、10M、15R、15M")
        for xpos,w in ((1.5,"W1"),(5.5,"W2"),(9.5,"W3")):
            ax.text(xpos,-.27,w,transform=ax.get_xaxis_transform(),ha="center",fontsize=7)
        ax.axvline(3.5,color="#E6E6E6",lw=.7); ax.axvline(7.5,color="#E6E6E6",lw=.7)
        ax.set_ylim(-.8,20); polish(ax); ax.text(.03,.95,f"({chr(97+j)})",transform=ax.transAxes,va="top")
    axs[0].set_ylabel("相对q变化 (%)")
    axs[1].annotate("最大 18.75%",xy=(9,18.75),xytext=(6.7,15.2),fontsize=7,arrowprops={"arrowstyle":"->","lw":.7,"color":"#555555"})
    handles,labels=axs[0].get_legend_handles_labels(); fig.legend(handles,labels,loc="upper center",ncol=3,frameon=False,bbox_to_anchor=(.5,.995),columnspacing=.7,handletextpad=.25)
    fig.suptitle("轻量化共享图例：FFT压力测试（变体非主模型）",y=.86,fontsize=9)
    fig.subplots_adjust(left=.08,right=.99,bottom=.29,top=.70,wspace=.12)
    save(fig,"sample-2-compact-robustness")


def sample_synth():
    data=rows("synthetic_recovery.csv")
    colors={"B":"#A6A6A6","F":"#FC8D62","P":"#8DA0CB"}; marks={"B":"o","F":"s","P":"^"}; lines={"B":"-","F":"--","P":":"}
    fig,(ax,side)=plt.subplots(1,2,figsize=(7.0,2.75),gridspec_kw={"width_ratios":[1.65,1]})
    stats={}
    for m in ("B","F","P"):
        rr=[r for r in data if r["model"]==m]; vals=sorted(float(r["relative_error"]) for r in rr if r["relative_error"])
        fail=sum(not r["relative_error"] for r in rr); passed=sum(r["pass_recovery"]=="True" for r in rr)
        stats[m]=(passed,fail,float(np.median(vals)),max(vals))
        ax.step(vals,np.arange(1,len(vals)+1)/len(vals),where="post",color=colors[m],linestyle=lines[m],linewidth=1.5,label=f"{m} (成功 n={len(vals)})")
    ax.axvline(2,color="#555555",lw=.9,ls="--",label="通过阈值 2.0")
    ax.set_xlim(0,max(v[3] for v in stats.values())*1.02); ax.set_ylim(0,1.02); ax.set_xlabel("相对误差（线性全范围）"); ax.set_ylabel("经验累积分布")
    polish(ax); ax.legend(frameon=False,loc="lower right"); ax.text(.03,.95,"(a)",transform=ax.transAxes,va="top")
    side.set_xlim(0,1); side.set_ylim(0,1); side.axis("off"); side.text(.02,.94,"(b)  全量结果",va="top",fontsize=8,transform=side.transAxes)
    y=.78
    for m in ("B","F","P"):
        p,f,med,mx=stats[m]
        side.text(.05,y,{"B":"●","F":"■","P":"▲"}[m],color=colors[m],ha="center",va="center",fontsize=9,transform=side.transAxes)
        side.text(.12,y,f"{m}：通过 {p}/144；失败 {f}/144\n中位误差 {med:.4g}；最大 {mx:.4g}",transform=side.transAxes,va="center",fontsize=7.3,linespacing=1.35)
        y-=.23
    side.text(.02,.08,"F最大误差约100.018%；\n结构可行性不等于观测真实准确度。",transform=side.transAxes,fontsize=7.2,va="bottom")
    fig.suptitle("证据卡式布局：分布与失败信息并列",y=.98,fontsize=9)
    fig.subplots_adjust(left=.08,right=.99,bottom=.18,top=.86,wspace=.15)
    save(fig,"sample-3-evidence-card")


if __name__ == "__main__":
    sample_q(); sample_robust(); sample_synth()
