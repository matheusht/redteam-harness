#!/usr/bin/env python3
"""Freeze an A/B contract and report readiness; never run either arm or contact a target."""
from __future__ import annotations
import argparse, subprocess, sys, tempfile
from pathlib import Path
from typing import Any
from engagement_records import RecordError, canonical_json_bytes, load_json, sha256_bytes, sha256_file, validate_record


def _git(repo: Path, *args: str) -> bytes:
    result=subprocess.run(["git","-C",str(repo),*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False)
    if result.returncode:raise RecordError("ab_source_commitment_invalid",result.stderr.decode(errors="replace"))
    return result.stdout


def source_commitment(repo: Path, commit_ref: str, paths: list[str]) -> dict[str,Any]:
    commit=_git(repo,"rev-parse","--verify",f"{commit_ref}^{{commit}}").decode().strip();git_tree=_git(repo,"rev-parse","--verify",f"{commit}^{{tree}}").decode().strip()
    if len(paths)!=len(set(paths)) or not paths:raise RecordError("ab_source_paths_invalid","source paths must be nonempty and unique")
    files=[]
    for path in sorted(paths):
        candidate=Path(path)
        if candidate.is_absolute() or ".." in candidate.parts:raise RecordError("ab_source_paths_invalid",path)
        data=_git(repo,"show",f"{commit}:{candidate.as_posix()}")
        files.append({"path":candidate.as_posix(),"sha256":sha256_bytes(data)})
    return {"commit":commit,"git_tree":git_tree,"files":files,"tree_hash":sha256_bytes(canonical_json_bytes(files))}


def _evidence(repo: Path, reference: dict[str,str] | None) -> tuple[dict[str,Any] | None,dict[str,str] | None]:
    if reference is None:return None,None
    path=(repo/reference["path"]).resolve()
    if not path.is_relative_to(repo.resolve()) or path.is_symlink() or not path.is_file() or sha256_file(path)!=reference["sha256"]:raise RecordError("ab_study_evidence_binding_invalid","study evidence path/hash is invalid")
    evidence=load_json(path);errors=validate_record(evidence,"ab-study-evidence")
    if errors:raise RecordError("ab_study_evidence_invalid","study evidence failed validation",errors)
    base=path.parent
    pairs=[(evidence['model_runtime_path'],evidence['model_runtime_hash']),(evidence['tool_runtime_path'],evidence['tool_runtime_hash'])]
    pairs += [(item['target_source_path'],item['target_source_hash']) for item in evidence['holdouts']];pairs += [(item['curation_review_path'],item['curation_review_hash']) for item in evidence['holdouts']]
    pairs += [(evidence['pilot']['analysis_protocol_path'],evidence['pilot']['analysis_protocol_hash']),(evidence['adjudication']['protocol_path'],evidence['adjudication']['protocol_hash']),(evidence['adjudication']['tie_rule_path'],evidence['adjudication']['tie_rule_hash']),(evidence['adjudication']['sealed_judge_packet_path'],evidence['adjudication']['sealed_judge_packet_hash'])]
    for item in evidence['isolation']:pairs += [(item['scope_path'],item['scope_hash']),(item['environment_manifest_path'],item['environment_hash']),(item['withheld_materials_path'],item['withheld_materials_hash']),(item['allowed_actions_path'],item['allowed_actions_hash']),(item['safety_stops_path'],item['safety_stops_hash'])]
    for relative,digest in pairs:
        artifact=(base/relative).resolve()
        if not artifact.is_relative_to(base.resolve()) or artifact.is_symlink() or not artifact.is_file() or sha256_file(artifact)!=digest:raise RecordError("ab_study_evidence_artifact_invalid",relative)
    from engagement_state import _scope_metadata
    for item in evidence['isolation']:
        _scope_metadata((base/item['scope_path']).resolve())
        environment=load_json((base/item['environment_manifest_path']).resolve())
        if validate_record(environment,'environment-preflight') or environment.get('status')!='ready':raise RecordError("ab_study_environment_not_ready",item['case_id'])
    return evidence,reference


def prepare(repo: Path, config: dict[str,Any]) -> tuple[dict[str,Any],dict[str,Any]]:
    arms=[{"blind_label":item["blind_label"],"treatment":item["treatment"],"source":source_commitment(repo,item["commit"],item["files"])} for item in config["arms"]]
    overlay=source_commitment(repo,config["common_safety_overlay"]["commit"],config["common_safety_overlay"]["files"])
    evidence,evidence_ref=_evidence(repo,config.get("study_evidence_ref"));pilot=evidence.get('pilot') if evidence else None;adjudication_evidence=evidence.get('adjudication') if evidence else None
    matching=dict(config["matching"]);matching["model_runtime_hash"]=evidence.get('model_runtime_hash') if evidence else None;matching["tool_runtime_hash"]=evidence.get('tool_runtime_hash') if evidence else None
    adjudication={"blind_arm_labels":True,"cold_primary_evidence":True,"independent_panel_registered":bool(adjudication_evidence and len(adjudication_evidence['panel_ids'])>=2),"tie_rule_registered":bool(adjudication_evidence),"judge_packet_sealed":bool(adjudication_evidence),"evidence_ref":evidence_ref}
    prereg={"schema_version":1,"study_id":config["study_id"],"status":"draft_not_authorized","lane":config["lane"],"exploratory":config["exploratory"],"arms":arms,"common_safety_overlay":overlay,"matching":matching,"inclusion_rules":config["inclusion_rules"],"exclusion_rules":config["exclusion_rules"],"contamination_rules":config["contamination_rules"],"target_strata":[{key:item[key] for key in ('domain','size','mode','difficulty','truth_class')} for item in evidence['holdouts']] if evidence else config["target_strata"],"root_cause_deduplication":config["root_cause_deduplication"],"allowed_actions":config["allowed_actions"],"safety_stops":config["safety_stops"],"co_primary_endpoints":["rigor_non_inferiority","resolution_benefit"],"secondary_endpoints":config["secondary_endpoints"],"blocked_run_treatment":"publish_and_exclude_from_effect_imputation","minimum_practical_effect":pilot.get('minimum_practical_effect') if pilot else None,"sample_size":pilot.get('recommended_sample_size') if pilot else None,"power_basis":"pilot_bound" if pilot else "unavailable","endpoint_definitions":{"rigor_non_inferiority_margin":config.get("rigor_non_inferiority_margin"),"resolution_minimum_effect":pilot.get('minimum_practical_effect') if pilot else None},"analysis_plan":"paired_case_deltas_exact_counts_publish_all_cases_no_unplanned_peeking","study_evidence_ref":evidence_ref,"case_isolation_plan_ref":evidence_ref,"withheld_material_manifest_ref":evidence_ref,"no_peeking":True,"adjudication":adjudication,"safety":{"identical_root_gates":True,"zone2_fresh_confirmation":True,"operator_only_filing":True,"cleanup_required":True,"shared_live_state_forbidden":True},"execution_authorized":False}
    errors=validate_record(prereg,"ab-preregistration")
    if errors:raise RecordError("ab_preregistration_invalid","preregistration failed validation",errors)
    blockers=[]
    if matching["model_provider_version"] is None or matching["call_budget"] is None or matching["time_budget"] is None:blockers.append("model_or_budget_unfrozen")
    if evidence is None:
        blockers.extend(["pilot_variance_unavailable","sample_size_unregistered","adjudication_panel_unregistered","tie_rule_unregistered","judge_packet_unsealed","no_eligible_holdout_manifest","signed_scope_or_environment_missing"])
    labels_unique=len({a['blind_label'] for a in arms})==2;treatments_distinct=len({a['treatment'] for a in arms})==2
    source_verified=all(source_commitment(repo,item["commit"],item["files"])==arm["source"] for item,arm in zip(config["arms"],arms))
    trees_verified=source_verified and all(_git(repo,"rev-parse","--verify",f"{item['source']['commit']}^{{tree}}").decode().strip()==item['source']['git_tree'] for item in arms+[{'source':overlay}])
    checks={"source_hashes_verified":source_verified,"full_git_trees_verified":trees_verified,"arm_labels_unique":labels_unique,"treatments_distinct":treatments_distinct,"safety_overlay_shared":True,"historical_cases_excluded_from_holdout":config.get("historical_cases_excluded_from_holdout") is True and (evidence is None or all(not item['decision5_informed'] and not item['lesson_present'] for item in evidence['holdouts']))}
    if not all(checks.values()) and "no_eligible_holdout_manifest" not in blockers:blockers.append("study_evidence_missing_or_invalid")
    # Slice J is readiness scaffolding, not an authorization issuer. Even complete evidence must pass
    # a later human-reviewed implementation/PR that introduces an authorization transition.
    blockers.append("reviewed_transition_implementation_absent")
    report={"schema_version":1,"report_id":f"{config['study_id']}-readiness","study_id":config["study_id"],"preregistration_hash":sha256_bytes(canonical_json_bytes(prereg)),"status":"not_ready","blockers":blockers,"checks":checks,"execution":{"target_contact":False,"arm_runs":0,"artifact_execution":False,"zone2_creation":False,"results_fabricated":False},"claims":{"ab_readiness":"not_ready","regression_parity":"not_demonstrated","efficacy":"not_demonstrated"}}
    errors=validate_record(report,"ab-readiness-report")
    if errors:raise RecordError("ab_readiness_report_invalid","readiness report failed validation",errors)
    return prereg,report

def self_test()->int:
    with tempfile.TemporaryDirectory() as tmp:
        repo=Path(tmp);subprocess.run(["git","init","-q",str(repo)],check=True);subprocess.run(["git","-C",str(repo),"config","user.email","test@example.invalid"],check=True);subprocess.run(["git","-C",str(repo),"config","user.name","test"],check=True);(repo/'policy.txt').write_text('safe\n');(repo/'arm.txt').write_text('treatment\n');subprocess.run(["git","-C",str(repo),"add","."],check=True);subprocess.run(["git","-C",str(repo),"commit","-qm","fixture"],check=True)
        config={"study_id":"ab-selftest","lane":"sealed_known_truth","exploratory":True,"arms":[{"blind_label":"arm-x","treatment":"staged_baseline","commit":"HEAD","files":["arm.txt"]},{"blind_label":"arm-y","treatment":"decision_0005_kernel","commit":"HEAD","files":["arm.txt"]}],"common_safety_overlay":{"commit":"HEAD","files":["policy.txt"]},"matching":{"model_provider_version":None,"tools":[],"target_copy":"independent_per_arm","call_budget":None,"time_budget":None,"starting_information":"identical_recon_only","filesystem_isolation":True,"session_isolation":True},"inclusion_rules":["sealed local case"],"exclusion_rules":["historical lesson exposed"],"contamination_rules":["independent sessions"],"secondary_endpoints":[],"adjudication":{"blind_arm_labels":True,"cold_primary_evidence":True,"independent_panel_registered":False,"tie_rule_registered":False,"judge_packet_sealed":False},"pilot_variance_available":False,"eligible_holdout_manifest":None,"signed_scope_environment_ready":False,"historical_cases_excluded_from_holdout":True,"study_evidence_ref":None,"target_strata":[{"domain":"fixture","size":"small","mode":"hermetic","difficulty":"fixture","truth_class":"unknown"}],"root_cause_deduplication":["mechanism boundary"],"allowed_actions":["offline fixture only"],"safety_stops":["stop on drift"],"rigor_non_inferiority_margin":0.0}
        prereg,report=prepare(repo,config);ok=not prereg['execution_authorized'] and report['status']=='not_ready' and report['execution']['arm_runs']==0 and report['claims']['efficacy']=='not_demonstrated'
    print(f"A/B READINESS SELF-TEST: {'PASS' if ok else 'FAIL'}");return 0 if ok else 1


def main()->int:
    parser=argparse.ArgumentParser();parser.add_argument('--config',type=Path);parser.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1]);parser.add_argument('--preregistration-output',type=Path);parser.add_argument('--report-output',type=Path);parser.add_argument('--self-test',action='store_true');args=parser.parse_args()
    if args.self_test:return self_test()
    if not args.config or not args.preregistration_output or not args.report_output:parser.error('--config, --preregistration-output, and --report-output are required')
    prereg,report=prepare(args.repo.resolve(),load_json(args.config));args.preregistration_output.write_bytes(canonical_json_bytes(prereg));args.report_output.write_bytes(canonical_json_bytes(report));return 0
if __name__=='__main__':
    try:raise SystemExit(main())
    except RecordError as exc:sys.stdout.buffer.write(canonical_json_bytes({"valid":False,"error":exc.as_dict()}));raise SystemExit(1)
