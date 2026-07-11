#!/usr/bin/env python3
"""Deterministic read-only inventory and operator-reviewed migration proposals."""
from __future__ import annotations
import argparse, json, os, re, tempfile
from pathlib import Path
from typing import Any

from engagement_records import canonical_json_bytes, infer_schema_name, load_json, sha256_bytes, sha256_file, validate_record
from finding_review import claim_rows, render_claim_proof, render_internal_report


def _report_manifest_status(root: Path, path: Path, record: dict[str, Any]) -> tuple[str, str | None]:
    errors = validate_record(record, "report-manifest")
    if errors: return "needs_review", errors[0]["code"]
    report = root / record["report_path"]
    finding_paths = list(root.glob(f"findings/{record['finding_id']}/rev-{record['finding_revision']}.json"))
    if not report.is_file() or sha256_file(report) != record["report_digest"]: return "needs_review", "report_bytes_unbound"
    if len(finding_paths) != 1 or sha256_file(finding_paths[0]) != record["finding_digest"]: return "needs_review", "finding_revision_unbound"
    try:
        finding=load_json(finding_paths[0]);finding_errors=validate_record(finding,'finding-v3');review_paths=[path for path in root.glob('reviews/**/*.json') if load_json(path).get('review_id')==record['adjudication_review_ref']]
        if finding_errors or finding.get('finding_id')!=record['finding_id'] or finding.get('revision')!=record['finding_revision'] or finding.get('engagement_id')!=record['engagement_id']:return 'needs_review','finding_identity_mismatch'
        if len(review_paths)!=1 or sha256_file(review_paths[0])!=record['adjudication_review_digest'] or finding.get('adjudication',{}).get('review_ref')!=record['adjudication_review_ref']:return 'needs_review','adjudication_review_unbound'
        review=load_json(review_paths[0]);review_errors=validate_record(review,'review');expected_prior=None if record['finding_revision']==1 else record['finding_revision']-1
        if review_errors or review.get('engagement_id')!=record['engagement_id'] or review.get('review_type')!='claim_adjudication' or review.get('proposed_finding_id')!=record['finding_id'] or review.get('finding_revision')!=expected_prior:return 'needs_review','adjudication_review_mismatch'
        claim_ids={row['claim_id'] for row in claim_rows(finding)};included=set(record['included_claim_ids']);omitted={item['claim_id'] for item in record['omitted_claims']}
        if included & omitted or included | omitted != claim_ids or not included:return 'needs_review','claim_partition_mismatch'
        if report.read_bytes()!=render_internal_report(finding,record['included_claim_ids'],record['omitted_claims']).encode() or sha256_bytes(render_claim_proof(finding).encode())!=record['claim_proof_matrix_hash']:return 'needs_review','rendered_report_mismatch'
    except Exception as exc:return 'needs_review',f'binding_error:{type(exc).__name__}'
    return "representable", None


def inventory(root: Path) -> dict[str, Any]:
    root = root.resolve(); entries: list[dict[str, Any]] = []
    engagements = root / "engagements" if (root / "engagements").is_dir() else root
    for engagement in sorted(path for path in engagements.iterdir() if path.is_dir() and path.name != "_TEMPLATE"):
        for path in sorted(engagement.glob("findings/**/*.json")):
            rel = path.relative_to(engagement).as_posix()
            try:
                record = load_json(path); schema = infer_schema_name(record); errors = validate_record(record, schema) if schema else [{"code":"unknown_record_version"}]
                disposition, reason = ("representable", None) if not errors else ("needs_review", errors[0]["code"])
            except Exception as exc: schema=None; disposition,reason="needs_review",type(exc).__name__
            entries.append({"engagement_id": engagement.name, "kind": "finding", "source_path": rel, "source_hash": sha256_file(path), "source_schema": schema, "disposition": disposition, "reason": reason, "proposed_events": ["legacy.record_imported"], "proposed_revision": 1 if disposition == "representable" else None, "unresolved_fields": [] if disposition == "representable" else [reason]})
        report_paths: set[Path] = set()
        for path in sorted(engagement.glob("reports/*.manifest.json")):
            report_paths.add(path); record={}
            try:
                record=load_json(path); disposition,reason=_report_manifest_status(engagement,path,record)
            except Exception as exc: disposition,reason="needs_review",type(exc).__name__
            entries.append({"engagement_id":engagement.name,"kind":"report_manifest","source_path":path.relative_to(engagement).as_posix(),"source_hash":sha256_file(path),"source_schema":"report-manifest","disposition":disposition,"reason":reason,"proposed_events":["legacy.record_imported","report.generated"] if disposition=="representable" else ["legacy.record_imported"],"proposed_revision":record.get("finding_revision") if disposition=="representable" else None,"unresolved_fields":[] if disposition=="representable" else [reason]})
        for path in sorted(engagement.glob("reports/*")):
            if not path.is_file() or path.name.endswith(".manifest.json"): continue
            entries.append({"engagement_id":engagement.name,"kind":"report_narrative","source_path":path.relative_to(engagement).as_posix(),"source_hash":sha256_file(path),"source_schema":None,"disposition":"needs_review","reason":"narrative_without_revision_binding","proposed_events":["legacy.record_imported"],"proposed_revision":None,"unresolved_fields":["finding_revision","adjudication_review","claim_proof_matrix"]})
        progress=engagement/'progress.md'
        if progress.is_file() and not any(item['engagement_id']==engagement.name and item['kind'].startswith('report') for item in entries):
            text=progress.read_text(encoding='utf-8',errors='replace').lower()
            if any(marker in text for marker in ('finding','submitted','report')):
                entries.append({"engagement_id":engagement.name,"kind":"narrative_status","source_path":"progress.md","source_hash":sha256_file(progress),"source_schema":None,"disposition":"needs_review","reason":"narrative_status_without_structured_report","proposed_events":["legacy.record_imported"],"proposed_revision":None,"unresolved_fields":["authoritative_status","finding_revision"]})
    per_engagement={}
    for entry in entries:
        summary=per_engagement.setdefault(entry['engagement_id'],{'representable':0,'needs_review':0,'proposed_event_count':0,'unresolved_count':0})
        summary[entry['disposition']]+=1;summary['proposed_event_count']+=len(entry['proposed_events']);summary['unresolved_count']+=len(entry['unresolved_fields'])
    counts={key:sum(1 for entry in entries if entry['disposition']==key) for key in ('representable','needs_review')}
    payload={"schema_version":1,"mode":"dry_run","corpus_root":".","entries":entries,"per_engagement":per_engagement,"counts":{**counts,"total":len(entries)},"invented_attempts":0,"source_bytes_modified":False}
    payload['inventory_hash']=sha256_bytes(canonical_json_bytes(payload));return payload


def _signed_operator(scope: Path) -> str:
    text=scope.read_text(encoding='utf-8');operator=re.search(r'^- Operator:\s*(.+?)\s*$',text,re.M)
    if not operator or not re.search(r'^- Signed:\s*\[[xX]\]\s*$',text,re.M): raise ValueError('signed scope required')
    return re.sub(r'[^A-Za-z0-9._:-]+','-',operator.group(1).strip()).strip('-') or 'operator'


def _proposal_payload(result: dict[str, Any], engagement_id: str, operator_id: str) -> dict[str, Any]:
    return {"schema_version":1,"proposal_only":True,"operator":{"role":"operator","id":operator_id},"engagement_id":engagement_id,"inventory_hash":result["inventory_hash"],"entries":[entry for entry in result["entries"] if entry["engagement_id"]==engagement_id],"invented_attempts":0,"apply_authorized":False}


def write_proposal(root: Path, engagement_id: str, operator_id: str, output: Path) -> dict[str, Any]:
    result=inventory(root);engagement_root=(root/'engagements' if (root/'engagements').is_dir() else root)/engagement_id
    if _signed_operator(engagement_root/'scope.md')!=operator_id: raise ValueError('operator does not match signed scope')
    proposal=_proposal_payload(result,engagement_id,operator_id)
    output.write_bytes(canonical_json_bytes(proposal));return proposal


def _same_or_ancestor(left: Path, right: Path) -> bool:
    """True when left aliases right or an existing ancestor of right, including mount aliases."""
    return left.exists() and any(candidate.exists() and os.path.samefile(left, candidate) for candidate in (right, *right.parents))


def apply_proposal(root: Path, proposal_path: Path, destination: Path, operator_id: str, recorded_at: str) -> dict[str, Any]:
    proposal=load_json(proposal_path);source_engagement_id=proposal['engagement_id'];source_base=(root.resolve()/'engagements' if (root.resolve()/'engagements').is_dir() else root.resolve());source_engagement=(source_base/source_engagement_id).resolve();engagement_root=destination.resolve();engagement_id=engagement_root.name
    if _same_or_ancestor(source_engagement,engagement_root) or _same_or_ancestor(engagement_root,source_engagement):raise ValueError('migration destination must be filesystem-separate from source engagement')
    if _signed_operator(source_engagement/'scope.md')!=operator_id or _signed_operator(engagement_root/'scope.md')!=operator_id:raise ValueError('operator must match signed source and destination scopes')
    current=inventory(root);expected=_proposal_payload(current,source_engagement_id,operator_id)
    if canonical_json_bytes(proposal)!=canonical_json_bytes(expected):raise ValueError('proposal is stale, tampered, or operator-mismatched')
    from engagement_state import atomic_write, append_event, base_event, initialize_engagement, read_ledger
    if not read_ledger(engagement_root,'event'):initialize_engagement(engagement_root,recorded_at)
    manifest_entries=[]
    for entry in proposal['entries']:
        manifest_entries.append({'source_path':entry['source_path'],'source_hash':entry['source_hash'],'disposition':'needs_review','source_artifact_ref':None,'imported_finding_id':None,'imported_revision':None,'missing_legacy_evidence':entry['unresolved_fields'] or ['attempts_and_controls_not_reconstructable']})
    manifest={'schema_version':1,'migration_id':f'migration-{source_engagement_id}-into-{engagement_id}','engagement_id':engagement_id,'recorded_at':recorded_at,'source_inventory_hash':proposal['inventory_hash'],'operator':{'role':'operator','id':operator_id},'entries':manifest_entries,'outcome_counts':{'imported':0,'needs_review':len(manifest_entries),'skipped':0,'errors':0}}
    path=engagement_root/'legacy'/'migration-manifest.json'
    if path.exists():raise ValueError('migration manifest already exists')
    atomic_write(path,canonical_json_bytes(manifest))
    commit=base_event(event_id=f'event-migration-{engagement_id}-commit',engagement_id=engagement_id,recorded_at=recorded_at,actor_role='operator',actor_id=operator_id,event_type='record.committed',rationale='Commit operator-reviewed legacy migration manifest.',payload={'record_path':'legacy/migration-manifest.json','record_digest':sha256_file(path),'record_type':'migration-manifest','record_id':manifest['migration_id'],'record_revision':None});append_event(engagement_root,commit)
    for number,entry in enumerate(manifest_entries,1):
        event=base_event(event_id=f'event-legacy-import-{number}',engagement_id=engagement_id,recorded_at=recorded_at,actor_role='migration',actor_id=operator_id,event_type='legacy.record_imported',rationale='Preserve legacy source truth as needs_review without inventing attempts.',payload={'source_path':entry['source_path'],'source_hash':entry['source_hash'],'migration_disposition':'needs_review','source_artifact_ref':None,'imported_finding_id':None,'imported_revision':None});append_event(engagement_root,event)
    return {'migration_id':manifest['migration_id'],'entries':len(manifest_entries),'invented_attempts':0,'source_bytes_modified':False}


def self_test()->int:
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp);e=root/'engagements'/'legacy';(e/'reports').mkdir(parents=True);(e/'findings').mkdir();(e/'progress.md').write_text('# Legacy\nSubmitted finding narrative.\n');(e/'scope.md').write_text('- Operator: operator-test\n- Signed: [x]\n')
        a=inventory(root);source_hashes={path.relative_to(e).as_posix():sha256_file(path) for path in e.rglob('*') if path.is_file()};copy=Path(tmp)/'copy';copy.mkdir();(copy/'engagements').mkdir();import shutil;shutil.copytree(e,copy/'engagements'/'legacy');b=inventory(copy)
        proposal_path=Path(tmp)/'proposal.json';proposal=write_proposal(root,'legacy','operator-test',proposal_path)
        destination=root/'applied';destination.mkdir();destination.joinpath('scope.md').write_text('# Scope\n\n## Surfaces in scope\n- Offline migration records.\n## Benign safe-objective set\n- Preserve legacy truth.\n## Escalation ceiling\n- Records only.\n## Impact-demo authorization\n- No.\n## Accounts / fixtures\n- None.\n## Authorization\n- Operator: operator-test\n- Date: 2026-07-10\n- Signed: [x]\n- Record kernel: `decision-0005-v1`\n')
        tampered=dict(proposal);tampered['entries']=[];tampered_path=Path(tmp)/'tampered.json';tampered_path.write_bytes(canonical_json_bytes(tampered));tamper_blocked=alias_blocked=False
        try:apply_proposal(root,tampered_path,destination,'operator-test','2026-07-10T00:00:00Z')
        except ValueError:tamper_blocked=True
        try:apply_proposal(root,proposal_path,e,'operator-test','2026-07-10T00:00:00Z')
        except ValueError:alias_blocked=True
        applied=apply_proposal(root,proposal_path,destination,'operator-test','2026-07-10T00:00:00Z');after_hashes={path.relative_to(e).as_posix():sha256_file(path) for path in e.rglob('*') if path.is_file()}
        ok=a==b and tamper_blocked and alias_blocked and source_hashes==after_hashes and a['counts']['needs_review']>=1 and a['invented_attempts']==0 and not a['source_bytes_modified'] and proposal['proposal_only'] and not proposal['apply_authorized'] and applied['invented_attempts']==0 and destination.joinpath('legacy/migration-manifest.json').is_file()
        print(f"MIGRATION DRY-RUN SELF-TEST: {'PASS' if ok else 'FAIL'}");return 0 if ok else 1


def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=Path('.'));ap.add_argument('--output',type=Path);ap.add_argument('--self-test',action='store_true');ap.add_argument('--propose-engagement');ap.add_argument('--apply-proposal',type=Path);ap.add_argument('--destination',type=Path);ap.add_argument('--operator-id');ap.add_argument('--recorded-at');args=ap.parse_args()
    if args.self_test:return self_test()
    if args.apply_proposal:
        if not args.operator_id or not args.recorded_at or not args.destination:ap.error('--apply-proposal requires --destination, --operator-id and --recorded-at')
        result=apply_proposal(args.root,args.apply_proposal,args.destination,args.operator_id,args.recorded_at)
    elif args.propose_engagement:
        if not args.output or not args.operator_id:ap.error('--propose-engagement requires --operator-id and --output')
        result=write_proposal(args.root,args.propose_engagement,args.operator_id,args.output)
    else:result=inventory(args.root)
    if not args.output:print(canonical_json_bytes(result).decode(),end='')
    elif not args.propose_engagement and not args.apply_proposal:args.output.write_bytes(canonical_json_bytes(result))
    return 0
if __name__=='__main__':raise SystemExit(main())
