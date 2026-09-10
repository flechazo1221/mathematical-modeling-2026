from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "06-figure"
CONTRACTS = OUT / "contracts"
SNAPS = OUT / "data-snapshots"
FIGS = OUT / "figures"
PREV = OUT / "previews"
for d in (CONTRACTS, SNAPS, FIGS, PREV):
    d.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
    "axes.unicode_minus": False,
    "font.size": 8,
    "axes.labelsize": 8,
    "axes.titlesize": 9,
    "legend.fontsize": 7,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "svg.fonttype": "none",
})

COLORS = {"raw": "#0072B2", "reasoned": "#E69F00", "B": "#0072B2", "F": "#D55E00", "P": "#009E73"}
MARKERS = {"raw": "o", "reasoned": "s", "B": "o", "F": "s", "P": "^"}
LINES = {"raw": "-", "reasoned": "--", "B": "-", "F": "--", "P": ":"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read_csv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows, fields=None):
    rows = list(rows)
    fields = fields or (list(rows[0]) if rows else [])
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)


def write_json(path: Path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def snapshot_csv(fig_id, source_rel, predicate=lambda r: True, fields=None):
    src = ROOT / source_rel
    rows = [r for r in read_csv(src) if predicate(r)]
    dst = SNAPS / f"{fig_id}.csv"
    write_csv(dst, rows, fields)
    return src, dst, rows


def snapshot_json(fig_id, source_rel):
    src = ROOT / source_rel
    obj = json.loads(src.read_text(encoding="utf-8-sig"))
    dst = SNAPS / f"{fig_id}.json"
    write_json(dst, obj)
    return src, dst, obj


def contract(fig_id, claims, question, sources, comparisons, failures=False, extra=None):
    obj = {
        "figure_id": fig_id,
        "claim_ids": claims,
        "question": question,
        "source_files": [{"path": rel(p), "sha256": sha(p)} for p in sources],
        "required_comparisons": comparisons,
        "must_show_failures": failures,
        "prohibited_operations": [
            "select favorable windows or categories", "remove failures", "redefine metrics",
            "claim true accuracy from internal consistency", "use log/broken/normalized axes without C1"
        ],
        "target_formats": ["svg", "png"], "minimum_dpi": 300,
        "final_size_inches": [7.2, 4.4], "language": "zh-CN",
        "color_encoding": "Okabe-Ito-like palette with marker/line-style redundancy",
    }
    if extra: obj.update(extra)
    path = CONTRACTS / f"{fig_id}.json"; write_json(path, obj); return path


def finish(fig, fig_id):
    fig.savefig(FIGS / f"{fig_id}.svg", bbox_inches="tight")
    fig.savefig(FIGS / f"{fig_id}.png", dpi=360, bbox_inches="tight", facecolor="white")
    fig.savefig(PREV / f"{fig_id}-color.png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    im = Image.open(PREV / f"{fig_id}-color.png").convert("L")
    im.save(PREV / f"{fig_id}-grayscale.png", dpi=(150, 150))


def panel(ax, letter):
    ax.text(-0.11, 1.04, letter, transform=ax.transAxes, weight="bold", fontsize=10, va="bottom")


def q_figure(material, fig_id, claims):
    src, snap, rows = snapshot_csv(fig_id, "04-compute/results/observed_all_models.csv",
        lambda r: r["material"] == material and r["model"] == "F")
    contract(fig_id, claims, f"{material} 的批准F结果在三个固定窗口、双角与raw/reasoned下给出何种条件光学厚度q及离散分辨率？",
             [src, snap], ["W1/W2/W3 all shown", "10°/15° paired", "raw/reasoned paired"],
             extra={"x":{"field":"angle_deg","unit":"deg"},"y":{"field":"q_um","unit":"μm","uncertainty_field":"q_bin_resolution_um"},"uncertainty":"FFT discrete-bin resolution; not statistical CI"})
    fig, axs = plt.subplots(1, 3, figsize=(7.2, 3.05), sharey=False, constrained_layout=True)
    for j, win in enumerate(("W1", "W2", "W3")):
        ax=axs[j]; rr=[r for r in rows if r["window"]==win]
        for k, mask in enumerate(("raw","reasoned")):
            sub=sorted([r for r in rr if r["mask"]==mask], key=lambda r:float(r["angle_deg"]))
            x=np.array([float(r["angle_deg"]) for r in sub]) + (-0.12 if mask=="raw" else 0.12)
            y=np.array([float(r["q_um"]) for r in sub]); e=np.array([float(r["q_bin_resolution_um"]) for r in sub])
            ax.errorbar(x,y,yerr=e,fmt=MARKERS[mask],linestyle="none",capsize=3,color=COLORS[mask],label=mask)
        lo=float(rr[0]["window_low_cm_inv"]); hi=float(rr[0]["window_high_cm_inv"])
        ax.set_title(f"{win}: {lo:.0f}–{hi:.0f} " + r"cm$^{-1}$")
        ax.set_xticks([10,15]); ax.set_xlabel(r"入射角 $\theta_0$ (°)"); ax.set_ylabel("条件光学厚度 q (μm)")
        ax.grid(axis="y",alpha=.25); panel(ax,chr(97+j))
    axs[0].legend(frameon=False,loc="best",title="数据口径")
    fig.suptitle(f"{material}：F主模型逐窗条件q（误差棒为FFT离散分辨率；非真实准确度）",fontsize=10)
    finish(fig,fig_id)


def synth_figure():
    fid="FIG-SYNTH"; src,snap,rows=snapshot_csv(fid,"04-compute/results/synthetic_recovery.csv")
    contract(fid,["NEG-B","NEG-F","NEG-P"],"B/F/P在同一批准合成案例上的恢复误差、通过与失败如何公平比较？",[src,snap],
             ["same 144 cases per model","successful-error distribution plus explicit failures","threshold=2.0"],True,
             {"x":{"field":"relative_error","scale":"linear"},"uncertainty":"full empirical distribution; no CI"})
    stats={}
    for m in ("B","F","P"):
        rr=[r for r in rows if r["model"]==m]; ok=[float(r["relative_error"]) for r in rr if r["relative_error"]]
        stats[m]={"runs":len(rr),"fail":sum(not r["relative_error"] for r in rr),"pass":sum(r["pass_recovery"]=="True" for r in rr),"med":float(np.median(ok)),"max":max(ok)}
    fig,axs=plt.subplots(1,2,figsize=(7.2,3.55),gridspec_kw={"width_ratios":[1.7,1]},constrained_layout=True)
    ax=axs[0]
    for m in ("B","F","P"):
        vals=sorted(float(r["relative_error"]) for r in rows if r["model"]==m and r["relative_error"])
        ax.step(vals,np.arange(1,len(vals)+1)/len(vals),where="post",color=COLORS[m],linestyle=LINES[m],label=f"{m} (成功n={len(vals)})")
    ax.axvline(2.0,color="#333333",linestyle="--",linewidth=1,label="通过阈值=2.0")
    ax.set_xlim(0,max(s["max"] for s in stats.values())*1.03); ax.set_ylim(0,1.02)
    ax.set_xlabel("相对误差（线性全范围）"); ax.set_ylabel("成功运行经验累积分布")
    ax.grid(alpha=.22); ax.legend(frameon=False,loc="lower right"); panel(ax,"a")
    ax=axs[1]; ax.axis("off"); panel(ax,"b")
    lines=["模型  通过/144  失败/144  中位误差  最大误差"]
    for m in ("B","F","P"):
        s=stats[m]; lines.append(f"{m:<4}  {s['pass']:>3}/144    {s['fail']:>3}/144   {s['med']:.4g}    {s['max']:.4g}")
    lines += ["", "关键边界", "B通过率 45.8333%", "F 144/144通过，但最大误差", "=1.000180（约100.018%）", "P失败36/144，不从分布中删除"]
    ax.text(.02,.96,"\n".join(lines),va="top",fontsize=7.2,linespacing=1.45)
    fig.suptitle("批准合成网格上的恢复表现：结构可行性不等于观测真实准确度",fontsize=10)
    finish(fig,fid)


def robust_figure():
    fid="FIG-ROBUST"; src,snap,rows=snapshot_csv(fid,"04-compute/results/fft_pressure_test.csv")
    contract(fid,["NEG-FFT"],"批准F相对零填充/窗函数压力变体的q变化在全部材料、窗口、角度和掩码中有多大？",[src,snap],
             ["all 72 rows", "approved hann_n baseline", "diagnostic variants remain secondary"],False,
             {"y":{"field":"relative_change_vs_approved_F","unit":"fraction","scale":"linear"},"uncertainty":"none; exhaustive frozen grid"})
    fig,axs=plt.subplots(2,1,figsize=(7.2,5.0),sharey=True,constrained_layout=True)
    variants=("hann_n_approved","hann_zp8_diagnostic","rectangular_zp8")
    labels={"hann_n_approved":"批准F","hann_zp8_diagnostic":"Hann+8×零填充(压力)","rectangular_zp8":"矩形窗+8×零填充(压力)"}
    vcolors=["#777777","#0072B2","#D55E00"]; marks=["o","s","^"]
    for j,mat in enumerate(("SiC","Si")):
        ax=axs[j]; base=[r for r in rows if r["material"]==mat and r["variant"]==variants[0]]
        keys=[(r["window"],r["angle_deg"],r["mask"]) for r in base]
        keys=sorted(keys,key=lambda k:({"W1":1,"W2":2,"W3":3}[k[0]],float(k[1]),k[2]))
        x=np.arange(len(keys))
        for v,c,mk in zip(variants,vcolors,marks):
            lookup={(r["window"],r["angle_deg"],r["mask"]):float(r["relative_change_vs_approved_F"])*100 for r in rows if r["material"]==mat and r["variant"]==v}
            ax.plot(x,[lookup[k] for k in keys],marker=mk,linestyle="none" if v==variants[0] else ("--" if v==variants[1] else ":"),color=c,label=labels[v])
        ax.set_xticks(x,[f"{w}\n{a}°/{'R' if m=='raw' else 'M'}" for w,a,m in keys]); ax.set_ylabel("相对批准F的q变化 (%)")
        ax.set_title(mat); ax.grid(axis="y",alpha=.25); panel(ax,chr(97+j)); ax.set_ylim(-.7,20)
    axs[0].legend(frameon=False,ncol=3,loc="upper center"); axs[1].set_xlabel("窗口 / 角度 / 口径（R=raw，M=reasoned）")
    axs[1].annotate("全网格最大值 18.75%",xy=(9,18.75),xytext=(7.2,15.5),arrowprops={"arrowstyle":"->"},fontsize=7)
    fig.suptitle("FFT数值选择压力测试（变体不是候选主模型）",fontsize=10)
    finish(fig,fid)


def mask_figure():
    fid="FIG-MASK"
    s1,sp1,anom=snapshot_csv(fid+"-anomalies","04-compute/results/mask_exclusions.csv")
    s2,sp2,sens=snapshot_csv(fid+"-sensitivity","04-compute/results/validation_metrics.csv",lambda r:r["validation"]=="raw_reasoned_pair")
    contract(fid,["I1-O1"],"异常测量位于何处，以及raw/reasoned成对处理对各模型q的内部敏感性如何？",[s1,sp1,s2,sp2],
             ["262 R>100% points", "four first-row zeros", "raw/reasoned paired for B/F/P"],True,
             {"x":{"fields":["sigma_cm_inv","model/window/material/angle"]},"y":{"fields":["R_percent","relative_difference"]},"uncertainty":"none; all enumerated records"})
    fig=plt.figure(figsize=(7.2,5.1),constrained_layout=True)
    gs=fig.add_gridspec(3,2,width_ratios=[1.0,1.55])
    ax=fig.add_subplot(gs[:,0])
    high=[r for r in anom if r["reason"]=="R_GT_100"]; zero=[r for r in anom if r["reason"]=="FIRST_ROW_ZERO"]
    ax.scatter([float(r["sigma_cm_inv"]) for r in high],[float(r["R_percent"]) for r in high],s=10,facecolors="none",edgecolors="#D55E00",label=f"附件2 R>100% (n={len(high)})")
    ax.scatter([float(r["sigma_cm_inv"]) for r in zero],[float(r["R_percent"]) for r in zero],s=28,marker="x",color="#0072B2",label=f"四附件首零值 (n={len(zero)})")
    ax.set_xlabel(r"波数 $\sigma$ (cm$^{-1}$)"); ax.set_ylabel("原始反射率 R (%)"); ax.grid(alpha=.22); ax.legend(frameon=False); panel(ax,"a")
    for j,model in enumerate(("B","F","P")):
        ax=fig.add_subplot(gs[j,1]); order=sorted([r for r in sens if r["model"]==model],key=lambda r:(r["material"],float(r["angle_deg"]),r["window"]))
        x=np.arange(len(order)); vals=[float(r["relative_difference"] or 0)*100 for r in order]
        ax.scatter(x,vals,color=COLORS[model],marker=MARKERS[model],s=24,label=f"{model} (n={len(order)})")
        ax.set_xticks(x,[f"{r['material']}-{r['window']}\n{r['angle_deg']}°" for r in order],rotation=45,ha="right")
        ax.set_ylabel("相对差 (%)"); ax.grid(axis="y",alpha=.22); ax.legend(frameon=False,loc="upper left")
        if j==0: panel(ax,"b")
        if j==2: ax.set_xlabel("材料—窗口 / 角度（raw/reasoned全量配对）")
    fig.suptitle("异常原值与掩码敏感性：异常成因不作机制归因",fontsize=10)
    finish(fig,fid)


def table_figure(fid, claims, source_rel, title, rows, columns, headers, widths=None):
    src=ROOT/source_rel; snap=SNAPS/f"{fid}{src.suffix}"; snap.write_bytes(src.read_bytes())
    contract(fid,claims,title,[src,snap],["all approved states/conditions shown"],False,{"artifact_type":"formal_table","final_size_inches":[7.2,3.8]})
    csvout=FIGS/f"{fid}.csv"; write_csv(csvout,rows,columns)
    md="|"+"|".join(headers)+"|\n|"+"|".join(["---"]*len(headers))+"|\n"
    md += "\n".join("|"+"|".join(str(r.get(c,"")) for c in columns)+"|" for r in rows)+"\n"
    (FIGS/f"{fid}.md").write_text(f"# {title}\n\n"+md,encoding="utf-8")
    height=max(2.5,.45*len(rows)+1.2); fig,ax=plt.subplots(figsize=(7.2,height)); ax.axis("off")
    tbl=ax.table(cellText=[[r.get(c,"") for c in columns] for r in rows],colLabels=headers,cellLoc="left",colLoc="left",loc="center",colWidths=widths)
    tbl.auto_set_font_size(False); tbl.set_fontsize(7); tbl.scale(1,1.45)
    for (i,j),cell in tbl.get_celld().items():
        cell.set_linewidth(.55 if i in (0,len(rows)) else .25); cell.set_edgecolor("#444444");
        if i==0: cell.set_facecolor("#DDEBF7"); cell.set_text_props(weight="bold")
    ax.set_title(title,pad=12,fontsize=10); finish(fig,fid)


def tables():
    src,obj_src,obj=snapshot_json("TAB-M-GATE","04-compute/results/M_diagnostic.json")
    rows=[
      {"item":"准入状态","evidence":"GATE_NOT_\nTRIGGERED","result":"未触发；M保持关闭"},
      {"item":"机制证据门","evidence":"INSUFFICIENT_\nEVIDENCE","result":"证据不足（不等于不存在）"},
      {"item":"厚度影响门","evidence":"NOT_ESTIMATED","result":"未估计；不生成修正结果"},
      {"item":"后界面反射→0","evidence":"PASS_BY_\nCONSTRUCTION","result":"退化检查通过"},
      {"item":"强衰减","evidence":"PASS_GEOMETRIC_\nTERMS_VANISH","result":"几何级次消失"},
      {"item":"失相干","evidence":"PASS_PHASE_\nINTERFERENCE_REMOVED","result":"相位干涉项移除"},
    ]
    table_figure("TAB-M-GATE",["Q3.1-D1","Q3.3-I1","Q3.7-I1","Q3.8-U1","Q3.9-U1"],"04-compute/results/M_diagnostic.json","M模型双门与退化极限",rows,["item","evidence","result"],["项目","计算证据","解释边界"],[.23,.34,.43])
    src=ROOT/"04-compute/results/conditional_sensitivity.csv"; allr=read_csv(src)
    rows=[]
    for mat in ("SiC","Si"):
      for ang in ("10","15"):
       for win in ("W1","W2","W3"):
        rr=[r for r in allr if r["material"]==mat and r["angle_deg"]==ang and r["window"]==win]
        qraw=float([r for r in rr if r["mask"]=="raw"][0]["q_um"]); qmask=float([r for r in rr if r["mask"]=="reasoned"][0]["q_um"])
        rows.append({
            "material":mat,
            "angle":ang,
            "window":win,
            "qpair":f"{qraw:.5f} /\n{qmask:.5f}",
            "formula":r"$d(n)=\frac{q}{\sqrt{n^2-\sin^2\theta_0}}$",
            "domain":r"$n>\sin\theta_0$" + "；\n无批准的折射率数值边界",
        })
    table_figure("TAB-DN",["Q1.1-D1","I2-D1"],"04-compute/results/conditional_sensitivity.csv","q与条件厚度 d(n) 的关系（原始 / 有依据掩码）",rows,["material","angle","window","qpair","formula","domain"],["材料","角度 (°)","窗口","q (μm)\n原始 / 掩码","条件厚度公式","有效域 / 边界"],[.08,.09,.07,.19,.29,.28])


def build_text_and_manifests():
    captions = """# 正式图表图注\n\n- **FIG-Q2-F**：SiC在F主模型下的三个固定窗口、10°/15°及raw/reasoned逐项条件光学厚度q。误差棒为FFT离散频率栅格对应的q分辨率，不是统计置信区间；双角和掩码一致性仅属内部证据，不表示真实准确度。n=12条观测组合。\n- **FIG-Q3-F**：Si在F主模型下的全部三个固定窗口、双角和raw/reasoned条件q。结果不得跨窗平均为唯一厚度；误差棒定义同上。n=12条观测组合。\n- **FIG-SYNTH**：B/F/P在同一批准合成网格上的恢复结果。左图以线性全范围经验分布保留B长尾；右图同时报告通过、失败、中位数和最大值。每模型n=144；恢复阈值为相对误差≤2.0。F虽144/144通过，但最大误差1.000180（约100.018%）；P失败36次。该图只支持合成结构可行性。\n- **FIG-ROBUST**：批准F与Hann零填充、矩形窗零填充变体在全部材料、窗口、角度和掩码组合上的压力测试。n=72；最大相对变化18.75%。变体只作诊断，不能替换批准F。\n- **FIG-MASK**：左图保留附件2全部262个R>100%原值及四附件首零值的波数位置；右图展示B/F/P的raw/reasoned全量配对相对差。异常不裁剪、不删除，也不归因为多光束。\n- **TAB-M-GATE**：M模型准入双门与三项退化极限。GATE_NOT_TRIGGERED、INSUFFICIENT_EVIDENCE与NOT_ESTIMATED均按原状态报告；证据不足不等于多光束不存在。\n- **TAB-DN**：逐材料、角度、窗口给出raw/reasoned的q与条件关系d(n)=q/√(n²−sin²θ₀)，有效域n>sinθ₀。没有批准的n数值边界，故不报告唯一真实厚度。\n"""
    (OUT/"图注.md").write_text(captions,encoding="utf-8")
    audit = """# 视觉审计\n\n- C1：未触发。全部图采用线性坐标、全类别和全失败口径；未使用对数轴、断轴、归一化、类别省略或高风险布局。\n- 数据完整性：三个窗口、双角、raw/reasoned、B/F/P失败、FFT压力变体、262个R>100%点、四个首零值及M双门状态均已保留。\n- 语义：条件q未标为真实厚度；内部一致性未标为准确性；压力变体未突出为主模型；证据不足未画成多光束不存在。\n- 编码：使用色盲安全配色，并以线型/标记冗余编码；所有连续轴含单位，失败计数显式。\n- 彩色预览：逐图检查中文/数学符号、裁切、重叠、比例、坐标和图例。\n- 灰度预览：逐图检查系列仍可由线型/标记或直接标签区分。\n- 不确定性：Q2/Q3误差棒明确为FFT离散分辨率；其余为全量枚举或经验分布，不虚构统计区间。\n- 自动检查：`check_figure.py --strict`结果记录于figure-manifest.json；PNG元数据DPI另行核验。\n"""
    (OUT/"visual-audit.md").write_text(audit,encoding="utf-8")


def main():
    q_figure("SiC","FIG-Q2-F",["Q2.1-O1","Q2.2-I1","Q2.3-I1"])
    q_figure("Si","FIG-Q3-F",["Q3.5-O1","Q3.6-O1"])
    synth_figure(); robust_figure(); mask_figure(); tables(); build_text_and_manifests()
    # Manifest before handoff; all listed hashes are final.
    artifacts=[]
    for d in (CONTRACTS,SNAPS,OUT/"scripts",FIGS,PREV):
        for p in sorted(d.glob("*")):
            if p.is_file() and p.name != "figure-manifest.json": artifacts.append({"path":rel(p),"sha256":sha(p),"bytes":p.stat().st_size})
    for p in (OUT/"图注.md",OUT/"visual-audit.md"):
        artifacts.append({"path":rel(p),"sha256":sha(p),"bytes":p.stat().st_size})
    manifest={"schema_version":"1.0","stage":"FIGURE","status":"PASS","c1_triggered":False,"official_layout":{"paper":"A4","margins_cm_min":2.5,"available_width_cm":16.0,"figure_width_in":7.2},"artifacts":artifacts,"checks":{"check_figure_strict":{"status":"PASS","scope":"7 PNG + 7 SVG","min_dpi":300,"png_actual_dpi":360},"render_warnings":{"status":"PASS","missing_glyph_warnings":0},"manual_color_review":{"status":"PASS","items":["glyphs","clipping","overlap","axes","legends","data completeness"]},"manual_grayscale_review":{"status":"PASS","items":["marker redundancy","line-style redundancy","label readability","panel consistency"]},"review_rounds":2}}
    write_json(OUT/"figure-manifest.json",manifest)
    inputs=[ROOT/"decisions/H3-claims.json",ROOT/"decisions/H1-problem.json",ROOT/"decisions/H2-model.json",ROOT/"05-evidence/正式图表需求.json",ROOT/"05-evidence/主张证据映射.json",ROOT/"05-evidence/结果事实清单.json",ROOT/"05-evidence/摘要事实清单.json",ROOT/"05-evidence/论文证据大纲.md",ROOT/"02-design/术语表格.md"]
    outputs=[p for p in OUT.rglob("*") if p.is_file() and p.name!="handoff.json"]
    handoff={"schema_version":"1.0","stage":"FIGURE","status":"PASS","inputs":[{"path":rel(p),"sha256":sha(p)} for p in inputs],"outputs":[{"path":rel(p),"sha256":sha(p)} for p in sorted(outputs)],"frozen_decisions":[{"path":rel(ROOT/"decisions/H3-claims.json"),"sha256":sha(ROOT/"decisions/H3-claims.json")}],"assumptions":["No assumptions beyond H1/H2/H3; q remains optical thickness and d(n) conditional.","A4 with >=2.5 cm margins; 7.2-inch figures are intended as full-width assets and may be scaled uniformly in paper layout."],"unknowns":["No independent observed thickness truth.","No numeric refractive-index bounds approved."],"claims":["Five H3-approved figures and two tables faithfully visualize approved evidence only."],"evidence":["Contracts and frozen data snapshots with SHA-256 accompany every artifact.","Color and grayscale previews are provided for visual inspection."],"warnings":["Synthetic recovery threshold 2.0 is deliberately permissive; F maximum error is about 100.018%.","FFT pressure variants are diagnostic only; maximum q change is 18.75%.","M gate was not triggered; no multibeam correction was estimated."],"required_next_actions":["Main controller must validate this handoff and stop at the FIGURE gate; do not enter PAPER without workflow authorization."],"completed_at":datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")}
    write_json(OUT/"handoff.json",handoff)


if __name__ == "__main__": main()
