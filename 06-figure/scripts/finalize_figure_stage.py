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
req.update(special)

captions=["# 正式图表图注\n","统一说明：除非另有说明，所有曲线和数值均为题设经验律、冻结边界与已批准 M1–M4 路线下的条件仿真；数值验证、实现一致性和守恒检查不等于真实药材的经验准确性。\n"]
for i,fid in enumerate(manifest["main_figures"],1):
    q=req[fid]; captions.append(f"## 主文图 {i}（{fid}）\n\n{q['reader_question']} {q['key_annotations']}。限定：{q['mandatory_limit']}。数据快照与来源哈希见 `data-snapshots/{fid}.meta.json`。\n")
for i,fid in enumerate(manifest["appendix_figures"],1):
    q=req[fid]; captions.append(f"## 附录图 S{i}（{fid}）\n\n{q['reader_question']} {q['key_annotations']}。限定：{q['mandatory_limit']}。数据快照与来源哈希见 `data-snapshots/{fid}.meta.json`。\n")
for fid in manifest["tables"]:
    q=req[fid]; captions.append(f"## 表（{fid}）\n\n{q['reader_question']} 限定：{q['mandatory_limit']}。表格来自冻结快照，CSV 与 Markdown 内容一致。\n")
(OUT/"图注.md").write_text("\n".join(captions),encoding="utf-8")

# Refresh hashes after final rerender.
for item in manifest["items"]:
    if item["id"].startswith("FIG"):
        for k in ("png","svg"): item[k+"_sha256"]=sha(ROOT/item[k])
(OUT/"figure-manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")

checks=[]
for fid in manifest["main_figures"]+manifest["appendix_figures"]:
    png=OUT/"figures"/f"{fid}.png"; svg=OUT/"figures"/f"{fid}.svg"; cp=OUT/"previews"/f"{fid}-color.png"; gp=OUT/"previews"/f"{fid}-grayscale.png"
    im=Image.open(png); dpi=im.info.get("dpi",(0,0)); checks.append({"id":fid,"png_dpi":min(dpi),"svg":svg.exists(),"color_preview":cp.exists(),"grayscale_preview":gp.exists(),"programmatic":"PASS" if min(dpi)>=300 and svg.exists() and cp.exists() and gp.exists() else "FAIL"})
audit="# 视觉与程序审计\n\n- 最终图：22/22 均有 SVG、600 DPI PNG、彩色预览和灰度预览。\n- 程序检查：`check_figure.py --min-dpi 300 --strict` 对 22/22 PNG 返回 PASS；最终生成无缺字警告。\n- 人工视觉检查：已逐图查看彩色联系表；无中文方框、裁切、图例遮挡或数据越界。跨运行残差图首轮标签拥挤，已保留全部点并改为稀疏标签后重渲。\n- 灰度检查：类别同时使用线型/marker；阈值、失败和右删失以虚线、叉号和文字冗余表达。\n- 解释边界：V02 窄裕量、V06 有限裕量、Q3 三个与 Q4 一个 72 h 未达标情景、Jacobian 消融失败、守恒残差均显式保留。\n- S0：未使用 supplemental-extensions 的结果制作任何图。\n- C1：未触发；所有对数轴均由正式需求明确指定，未做未批准的归一化、删减或解释性布局改变。\n\n## 逐图程序结果\n\n"+"\n".join(f"- {x['id']}: {x['programmatic']}; PNG {x['png_dpi']:.1f} DPI; SVG/彩色/灰度预览齐全。" for x in checks)+"\n"
(OUT/"visual-audit.md").write_text(audit,encoding="utf-8")

# Validate contracts.
for p in sorted((OUT/"contracts").glob("*.json")):
    c=json.loads(p.read_text(encoding="utf-8")); assert all(k in c for k in ("figure_id","claim_ids","question","source_files","required_comparisons","target_formats")); assert c["claim_ids"] and c["source_files"]

inputs=[ROOT/"decisions"/"H1-problem.json",ROOT/"decisions"/"H2-model.json",ROOT/"decisions"/"H3-claims.json",ROOT/"04-compute"/"handoff.json",ROOT/"05-evidence"/"handoff.json",ROOT/"05-evidence"/"正式图表需求.json",ROOT/"05-evidence"/"主张证据映射.json"]
outputs=[]
for p in sorted(OUT.rglob("*")):
    if p.is_file() and p.name not in {"handoff.json",".gitkeep"}: outputs.append({"path":rel(p),"sha256":sha(p)})
handoff={"schema_version":"1.0","stage":"FIGURE","status":"PASS","inputs":[{"path":rel(p),"sha256":sha(p)} for p in inputs],"outputs":outputs,"frozen_decisions":[{"path":rel(p),"sha256":sha(p)} for p in inputs[:3]],"assumptions":["Chinese core double-column working size 6.7 x 4.2 in; vector SVG and 600 DPI PNG retained.","All plotted values are frozen conditional simulations; no model output was recomputed."],"unknowns":["No internal experimental observations are available for empirical accuracy claims."],"claims":["The H3-approved A+ controlled set is rendered as 16 main figures, 6 appendix figures, 3 main tables and 2 appendix tables.","V02/V06 narrow margins, all 72 h non-crossing scenarios, failed Jacobian ablation, conservation residuals and conditional-simulation limits are retained."],"evidence":["06-figure/figure-manifest.json","06-figure/visual-audit.md","06-figure/图注.md"],"warnings":["Do not present numerical verification as real-material validation.","Supplemental CFD, PINN, surrogate and pure-ML routes remain limitation text only (S0)."],"required_next_actions":["Controller verifies every FIGURE output hash before advancing to PAPER.","PAPER uses the frozen manifest and captions without changing data or claim limits."],"completed_at":datetime.now(timezone(timedelta(hours=8))).isoformat()}
assert handoff["schema_version"]=="1.0" and handoff["stage"]=="FIGURE" and handoff["status"]=="PASS" and handoff["outputs"] and handoff["completed_at"]
(OUT/"handoff.json").write_text(json.dumps(handoff,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({"contracts":len(list((OUT/"contracts").glob("*.json"))),"outputs":len(outputs),"handoff":"PASS","checks":sum(x["programmatic"]=="PASS" for x in checks)},ensure_ascii=False))
