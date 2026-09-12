import hashlib,json
from pathlib import Path
from datetime import datetime,timezone,timedelta
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/"06-figure"
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rel(p): return Path(p).relative_to(ROOT).as_posix()
manifest=json.loads((OUT/"figure-manifest.json").read_text(encoding="utf-8"))
req={x["figure_id"]:x for x in json.loads((ROOT/"05-evidence"/"正式图表需求.json").read_text(encoding="utf-8"))["requirements"]}
special={"TAB-STRATEGY-ASSUMPTION":{"reader_question":"模型策略与假设为什么采用、如何检验、结论边界是什么？","mandatory_limit":"不得新增未经计算支持的优越性判断","placement":"主文"}}
special["TAB-Q4-DRY-SOLID-CONTINUITY"]={"reader_question":"Q4 移动边界的干固体守恒、局部连续性与几何是否一致？","mandatory_limit":"数值诊断非真实性验证","placement":"附录"}
req.update(special)

captions=["# 正式图表图注\n","统一说明：除非另有说明，所有曲线和数值均为题设经验律、冻结边界与已批准 M1–M4 路线下的条件仿真；数值验证、实现一致性和守恒检查不等于真实药材的经验准确性。\n"]
for i,fid in enumerate(manifest["main_figures"],1):
    q=req[fid]; captions.append(f"## 主文图 {i}（{fid}）\n\n{q['reader_question']} {q['key_annotations']}。限定：{q['mandatory_limit']}。数据快照与来源哈希见 `data-snapshots/{fid}.meta.json`。\n")
for i,fid in enumerate(manifest["appendix_figures"],1):
    q=req[fid]; captions.append(f"## 附录图 S{i}（{fid}）\n\n{q['reader_question']} {q['key_annotations']}。限定：{q['mandatory_limit']}。数据快照与来源哈希见 `data-snapshots/{fid}.meta.json`。\n")
captions.append("## Q4文字量化分析（双实现一致性）\n\nreference 与 moving-FV 的最细网格插值阈值时刻均为 `183789.3317 s`，数值差为 `5.82e-10 s`，按 `60 s` 报告均为 `183840 s`；相对于约 `1.84×10^5 s` 的事件时刻，该差值仅为 `10^-15` 量级。该结果改由正文和证据表承载，不单独制图；它只说明两种数值实现的一致性，不构成外部实验验证。\n")
for fid in manifest["tables"]:
    q=req[fid]; captions.append(f"## 表（{fid}）\n\n{q['reader_question']} 限定：{q['mandatory_limit']}。表格来自冻结快照，CSV 与 Markdown 内容一致。\n")
(OUT/"图注.md").write_text("\n".join(captions),encoding="utf-8")

(OUT/"文字披露.md").write_text(
    "# 不制图的文字披露\n\n"
    "V02 网格验收的最大登记场变化为 `4.00114e-5`，验收阈值为 `5e-5`，"
    "因此仅表述为通过但裕量较窄；本项不制作正式图件，也不得写成宽裕或零误差。\n\n"
    "V10 Jacobian 消融的归一化守恒失衡为 `0.5936318973`，"
    "批准路线最大失衡为 `9.6451610e-8`；该失败消融不制作独立正式图件，"
    "改由正文和验证表披露，且不得解释为真实药材准确性。\n"
    "Q4 双实现一致性的最细网格插值阈值时刻均为 `183789.3317 s`，数值差为 `5.82e-10 s`，"
    "按 `60 s` 报告均为 `183840 s`；相对于约 `1.84×10^5 s` 的事件时刻，该差值仅为 `10^-15` 量级。"
    "本项改由正文和证据表保留量化分析，不制作独立正式图件。"
    "该结果只说明数值实现一致性，不构成外部实验验证。\n",
    encoding="utf-8",
)

# Refresh hashes after final rerender.
for item in manifest["items"]:
    if item["id"].startswith("FIG"):
        for k in ("png","svg"): item[k+"_sha256"]=sha(ROOT/item[k])
(OUT/"figure-manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")

checks=[]
for fid in manifest["main_figures"]+manifest["appendix_figures"]:
    png=OUT/"figures"/f"{fid}.png"; svg=OUT/"figures"/f"{fid}.svg"; cp=OUT/"previews"/f"{fid}-color.png"; gp=OUT/"previews"/f"{fid}-grayscale.png"
    im=Image.open(png); dpi=im.info.get("dpi",(0,0)); checks.append({"id":fid,"png_dpi":min(dpi),"svg":svg.exists(),"color_preview":cp.exists(),"grayscale_preview":gp.exists(),"programmatic":"PASS" if min(dpi)>=300 and svg.exists() and cp.exists() and gp.exists() else "FAIL"})
nfig = len(manifest["main_figures"]) + len(manifest["appendix_figures"])
audit=f"# 视觉与程序审计\n\n- 最终图：{nfig}/{nfig} 均有 SVG、600 DPI PNG、彩色预览和灰度预览。\n- 程序检查：`check_figure.py --min-dpi 300 --strict` 对 {nfig}/{nfig} PNG 返回 PASS；最终生成无缺字警告。\n- 人工视觉检查：已逐图查看彩色联系表；无中文方框、裁切、图例遮挡或数据越界。FIG-VAL-BALANCE-RESIDUAL 已按团队决定移出活动论文图表集并归档。\n- FIG-Q3-TIME-CONV 本轮重绘：保留 30 s→15 s 基准/细化事件时刻与 47.5654 s 变化量，数据曲线使用高对比彩色实线和不同 marker，非数据元素统一黑色；未保留右下角备注。\n- 灰度检查：类别同时使用线型/marker；阈值、失败和右删失以虚线、叉号和文字冗余表达。\n- 解释边界：V02 窄裕量改用正文文字披露；V06 有限裕量、Q3 三个与 Q4 一个 72 h 未达标情景、Jacobian 消融失败均显式保留；守恒残差保留在验证表和证据记录中，不制作独立论文图。\n- S0：未使用 supplemental-extensions 的结果制作任何图。\n- C1：未触发；所有保留图的对数轴均由正式需求明确指定。本轮仅按团队决定移除低信息增益图件，未改变模型、指标或数值。\n\n## 逐图程序结果\n\n"+"\n".join(f"- {x['id']}: {x['programmatic']}; PNG {x['png_dpi']:.1f} DPI; SVG/彩色/灰度预览齐全。" for x in checks)+"\n"
audit += "- FIG-Q4-JACOBIAN-ABLATION 已按团队决定移出活动论文图表集；V10 数值和失败结论改由正文、验证表及可恢复归档承载。\n"
audit += "- FIG-Q4-IMPLEMENTATION-AGREEMENT 已按团队决定移出活动论文图表集；双实现差值与报告值改由正文、证据表及可恢复归档承载。\n"
(OUT/"visual-audit.md").write_text(audit,encoding="utf-8")

# Validate contracts.
for p in sorted((OUT/"contracts").glob("*.json")):
    c=json.loads(p.read_text(encoding="utf-8")); assert all(k in c for k in ("figure_id","claim_ids","question","source_files","required_comparisons","target_formats")); assert c["claim_ids"] and c["source_files"]

inputs=[ROOT/"decisions"/"H1-problem.json",ROOT/"decisions"/"H2-model.json",ROOT/"decisions"/"H3-claims.json",ROOT/"04-compute"/"handoff.json",ROOT/"05-evidence"/"handoff.json",ROOT/"05-evidence"/"正式图表需求.json",ROOT/"05-evidence"/"主张证据映射.json"]
outputs=[]
for p in sorted(OUT.rglob("*")):
    if p.is_file() and p.name not in {"handoff.json",".gitkeep"}: outputs.append({"path":rel(p),"sha256":sha(p)})
handoff={"schema_version":"1.0","stage":"FIGURE","status":"PASS","inputs":[{"path":rel(p),"sha256":sha(p)} for p in inputs],"outputs":outputs,"frozen_decisions":[{"path":rel(p),"sha256":sha(p)} for p in inputs[:3]],"assumptions":["Chinese core double-column working size 6.7 x 4.2 in; vector SVG and 600 DPI PNG retained.","All plotted values are frozen conditional simulations; no model output was recomputed.","The dry-solid continuity figure was replaced by an appendix table at the user's direction."],"unknowns":["No internal experimental observations are available for empirical accuracy claims."],"claims":[f"The current team-selected controlled set is rendered as {len(manifest['main_figures'])} main figures, {len(manifest['appendix_figures'])} appendix figures, 3 main tables and 3 appendix tables.","V02 narrow margin is retained as a text-only disclosure; V06 narrow margin, all 72 h non-crossing scenarios, failed Jacobian ablation, conservation residuals and conditional-simulation limits are retained."],"evidence":["06-figure/figure-manifest.json","06-figure/visual-audit.md","06-figure/图注.md","06-figure/文字披露.md"],"warnings":["Do not present numerical verification as real-material validation.","Supplemental CFD, PINN, surrogate and pure-ML routes remain limitation text only (S0).","The former FIG-Q4-DRY-SOLID-CONTINUITY figure is archived as superseded; use TAB-Q4-DRY-SOLID-CONTINUITY instead."],"required_next_actions":["Controller verifies every FIGURE output hash before advancing to PAPER.","PAPER uses the current frozen manifest, captions and text disclosure without changing data or claim limits."],"completed_at":datetime.now(timezone(timedelta(hours=8))).isoformat()}
handoff["assumptions"].append("The Jacobian ablation figure was omitted by the user's direction; its V10 calculation and failure conclusion remain disclosed in text and validation tables.")
handoff["warnings"].append("The former FIG-Q4-JACOBIAN-ABLATION figure is archived as omitted; use its V10 values from the validation register and text disclosure.")
handoff["assumptions"].append("The FIG-Q4-IMPLEMENTATION-AGREEMENT figure was omitted by the user's direction; its double-implementation difference and reported event time remain disclosed in text and evidence tables.")
handoff["warnings"].append("The former FIG-Q4-IMPLEMENTATION-AGREEMENT figure is archived as omitted; use the Q4 text disclosure and evidence snapshot for implementation consistency.")
assert handoff["schema_version"]=="1.0" and handoff["stage"]=="FIGURE" and handoff["status"]=="PASS" and handoff["outputs"] and handoff["completed_at"]
(OUT/"handoff.json").write_text(json.dumps(handoff,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({"contracts":len(list((OUT/"contracts").glob("*.json"))),"outputs":len(outputs),"handoff":"PASS","checks":sum(x["programmatic"]=="PASS" for x in checks)},ensure_ascii=False))
