from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"03-prototype"

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def item(rel): return {"path":rel.as_posix(),"sha256":digest(ROOT/rel)}

input_paths=[
 Path("decisions/H1-problem.json"), Path("decisions/prototype-authorization.json"),
 Path("02-design/handoff.json"), Path("02-design/验证计划.json"), Path("02-design/H2-优化审计与方向.md"),
 Path("02-design/contracts/model-baseline-fringe.json"), Path("02-design/contracts/model-fft-optical.json"),
 Path("02-design/contracts/model-physical-regression.json"), Path("02-design/contracts/model-multibeam-transfer.json"),
 Path("input/B题/附件/附件1.xlsx"), Path("input/B题/附件/附件2.xlsx"),
 Path("input/B题/附件/附件3.xlsx"), Path("input/B题/附件/附件4.xlsx")]
files=sorted([p for p in OUT.rglob("*") if p.is_file() and p.name not in {"handoff.json","handoff.sha256"} and "__pycache__" not in p.parts])
handoff={
 "schema_version":"1.0","stage":"PROTOTYPE","status":"PASS",
 "inputs":[item(p) for p in input_paths],
 "outputs":[item(p.relative_to(ROOT)) for p in files],
 "frozen_decisions":[item(Path("decisions/H1-problem.json")),item(Path("decisions/prototype-authorization.json"))],
 "assumptions":[
  "A1: 仅在固定局部窗口把n*cos(theta1)视为有效常量；观察到跨窗漂移时不作全谱外推。",
  "A2: 空气折射率为1；本原型只输出q，未用未获证据支持的材料n。",
  "A3: 合成门槛按完整周期与窗口分辨率预注册；失败码和近失效结果保留。",
  "A4: B/F/P使用平行均匀层最低基线；楔度和粗糙度只作为未检验失效解释。",
  "A5: P仅含固定低维线性基线，不外推吸收或样品参数。",
  "A6: 10度与15度先独立；未运行共享厚度联合拟合。",
  "A7: 种子、窗口、掩码、预算、停止规则及支持门槛在观察输出前冻结。"],
 "unknowns":[
  "题目样品匹配的SiC/Si线性n(sigma)、k(sigma)、晶型、掺杂、温度及偏振适用域仍缺直接证据。",
  "仪器分辨率、相干长度、角度误差、粗糙度、楔度和独立厚度真值未知。",
  "跨窗漂移可由色散、基线、吸收、异常或多光束等多种机制产生，本原型不能归因。"],
 "claims":[
  "B/F/P已在同数据、窗口、掩码对、指标、预算和停止规则下完成可复现小型比较。",
  "F相对B的目标稳定性改进达到预注册门槛，证据标记supported；这不是最终模型选择。",
  "P未达到逐案例胜率门槛，证据标记inconclusive；未因较优中位数修改门槛。",
  "M只完成条件诊断接口与退化极限，双门未触发，未准入。",
  "所有观察结果均为条件光学厚度诊断，不是唯一真实厚度。"],
 "evidence":[
  "03-prototype/原型结果.csv保存全部合成和观察模型运行、失败码、诊断量及运行时。",
  "03-prototype/model-b、model-f、model-p和model-m保存最小实现说明与逐模型输出。",
  "03-prototype/预注册规则.json记录冻结的阈值、种子、窗口、掩码、预算和停止规则。",
  "03-prototype/候选方案对比.md与H2-选择包.md给出相对B的supported/inconclusive分类及限制。"],
 "warnings":[
  "PASS仅表示PROTOTYPE产物与验证完整，不表示H2已选择最终路线。",
  "F的supported只针对本预注册原型的目标缺陷；无独立真值，不能解释为真实准确性。",
  "B的OK_CONDITIONAL不保证物理可信；低周期和复杂结构下已观察到误配失败。",
  "不得用本轮输出倒推折射率、窗口或门槛，不得把联合双角结果冒充独立验证。",
  "handoff.json不自列哈希；其自身哈希保存在03-prototype/handoff.sha256。"],
 "required_next_actions":[
  "主控验证handoff schema、所有inputs/outputs哈希及handoff.sha256。",
  "队长在H2中显式审查B/F/P/M证据并作团队选择；本任务在H2前停止。",
  "若H2要求新原型，须先批准具体参数边界、预算和重新预注册门槛；否则不得继续COMPUTE。"],
 "completed_at":datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")}
(OUT/"handoff.json").write_text(json.dumps(handoff,ensure_ascii=False,indent=2),encoding="utf-8")
(OUT/"handoff.sha256").write_text(digest(OUT/"handoff.json")+"  handoff.json\n",encoding="ascii")
print(len(handoff["outputs"]),digest(OUT/"handoff.json"))
