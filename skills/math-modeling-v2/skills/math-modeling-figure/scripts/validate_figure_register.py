#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

REQUIRED_ITEM = {
    "id", "kind", "subproblem", "claim_or_question", "source_data",
    "model_result_version", "evidence_class", "visual_family", "axes",
    "groups", "uncertainty", "annotations", "expected_reading",
    "argument_role", "information_gain", "render_or_table_reason",
    "generation", "placement", "provenance", "limitations",
    "prohibited_interpretations", "confirmation"
}
QUANTITATIVE = {"quantitative", "model-diagnostic", "optimization", "uncertainty", "statistical"}
DETERMINISTIC = {"matlab", "python", "r", "julia", "gnuplot"}
SCHEMATIC = {"mermaid", "graphviz", "svg", "tikz", "programmatic-drawing"}
IMAGE_MODEL = {"image-model", "imagegen", "generative-image"}

def nonempty(value):
    return value is not None and value != "" and value != [] and value != {}

def validate(doc):
    errors = []
    for key in ("schema_version", "status", "project", "route_confirmed", "coverage", "global_visual_spec", "items"):
        if key not in doc:
            errors.append(f"register: missing {key}")
    if doc.get("status") == "VALIDATED" and doc.get("route_confirmed") is not True:
        errors.append("register: VALIDATED requires route_confirmed=true")
    coverage=doc.get("coverage",{})
    required_roles={k for k,v in coverage.items() if isinstance(v,dict) and v.get("status") in {"required","covered"}}
    ids = set(); covered_roles=set()
    for i, item in enumerate(doc.get("items", [])):
        where = f"items[{i}]"
        missing = sorted(REQUIRED_ITEM - set(item))
        if missing:
            errors.append(f"{where}: missing {', '.join(missing)}")
            continue
        if not item["id"] or item["id"] in ids:
            errors.append(f"{where}: ID is empty or duplicated")
        ids.add(item["id"])
        covered_roles.add(item.get("argument_role"))
        for key in ("claim_or_question", "model_result_version", "expected_reading", "limitations", "prohibited_interpretations"):
            if not nonempty(item[key]):
                errors.append(f"{item['id']}: {key} must be non-empty")
        evidence = str(item["evidence_class"]).lower()
        tool = str(item.get("generation", {}).get("tool", "")).lower()
        if evidence in QUANTITATIVE and tool not in DETERMINISTIC:
            errors.append(f"{item['id']}: quantitative evidence must use a deterministic quantitative renderer")
        if evidence == "deterministic-schematic" and tool not in SCHEMATIC:
            errors.append(f"{item['id']}: deterministic schematic must use Mermaid/Graphviz/SVG/TikZ/programmatic drawing")
        if tool in IMAGE_MODEL:
            if evidence != "conceptual-non-evidential":
                errors.append(f"{item['id']}: image-model output must be conceptual-non-evidential")
            if item.get("confirmation") != "USER_CONSENTED_DRAFT":
                errors.append(f"{item['id']}: image-model output requires USER_CONSENTED_DRAFT")
            if "DRAFT" not in item.get("annotations", []):
                errors.append(f"{item['id']}: image-model output requires a DRAFT annotation")
        if evidence in QUANTITATIVE and not item["source_data"]:
            errors.append(f"{item['id']}: quantitative evidence requires source_data")
        if not nonempty(item.get("information_gain")) or not nonempty(item.get("render_or_table_reason")):
            errors.append(f"{item['id']}: information-gain gate is incomplete")
        for src in item.get("source_data",[]):
            if str(src.get("sha256","")).upper() in {"","TBD","TODO"}:
                errors.append(f"{item['id']}: source hash must be frozen")
        if item.get("kind")=="figure" and str(item.get("information_gain","")).strip().lower() in {"none","low","无","低"}:
            errors.append(f"{item['id']}: low-information item must be merged or converted to a table")
    missing_roles=sorted(required_roles-covered_roles)
    if missing_roles:
        errors.append("register: required argument roles missing: "+", ".join(missing_roles))
    return errors

def main():
    parser = argparse.ArgumentParser(description="Validate a Phase-3 figure register.")
    parser.add_argument("register", type=Path)
    args = parser.parse_args()
    try:
        doc = json.loads(args.register.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: cannot read register: {exc}", file=sys.stderr)
        return 2
    errors = validate(doc)
    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        return 1
    print(f"PASS: {len(doc['items'])} registered item(s); routing and required fields are valid.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
