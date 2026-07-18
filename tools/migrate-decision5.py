#!/usr/bin/env python3
"""Deterministic read-only inventory and operator-reviewed migration proposals."""
from __future__ import annotations
import argparse, json, mimetypes, os, re, shutil, stat, tempfile
from pathlib import Path
from typing import Any

from engagement_records import RecordError, canonical_json_bytes, detect_secret_classes, infer_schema_name, load_json, sha256_bytes, sha256_file, validate_record
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


def _source_hash(path: Path) -> str:
    return sha256_bytes(os.readlink(path).encode()) if path.is_symlink() else sha256_file(path)


def _classify_source(engagement: Path, path: Path) -> tuple[str, str, str | None, str, str | None, list[str]]:
    rel=path.relative_to(engagement).as_posix(); lower=rel.lower(); schema=None
    if path.is_symlink(): return "unknown", "symlink", None, "needs_review", "symlink_not_importable", ["regular_source_bytes"]
    if any(part in {"artifacts","evidence","pocs","poc"} for part in path.parts) or path.suffix.lower() in {".har",".pcap",".zip",".wasm",".exe",".sh"}:
        return "artifact", "artifact", None, "needs_review", "artifact_requires_environment_and_zone_review", ["environment_identity","advisory_zone","operator_redaction_review"]
    if "submission" in lower or path.name.lower().startswith("submit"):
        return "submission_like", "submission_like", None, "needs_review", "operator_submission_authority_unreconstructable", ["submission_authority"]
    if path.suffix.lower()==".json":
        try:
            record=load_json(path);schema=infer_schema_name(record);errors=validate_record(record,schema) if schema else [{"code":"unknown_record_version"}]
        except Exception as exc:
            intended=any(part in {"findings","reviews","reports","migration","memory"} for part in path.parts)
            return ("structured_drifted", "structured_record", None, "needs_review", type(exc).__name__, ["valid_structured_record"]) if intended else ("unknown", "unknown", None, "needs_review", "unclassified_json", ["source_classification"])
        if errors:
            if schema=='finding-v2-legacy':return "structured_drifted", "finding", schema, "needs_review", errors[0]["code"], ["scope","environment","attempts","controls","replay","adjudication"]
            intended=any(part in {"findings","reviews","reports","migration","memory"} for part in path.parts)
            return ("structured_drifted", "structured_record", schema, "needs_review", errors[0]["code"], [errors[0]["code"]]) if intended else ("unknown", "unknown", schema, "needs_review", "unclassified_json", ["source_classification"])
        if schema=="finding-v3":
            return "structured_valid", "finding", schema, "needs_review", "finding_dependency_reconstruction_required", ["committed_attempts","controls","adjudication_review","environment_identity"]
        if schema=="finding-v2-legacy":
            return "structured_valid", "finding", schema, "needs_review", "legacy_finding_requires_v3_adjudication", ["attempts","controls","adjudication_review","environment_identity"]
        if schema=="report-manifest":
            disposition,reason=_report_manifest_status(engagement,path,record)
            if disposition=="representable": return "report", "report_manifest", schema, "needs_review", "imported_finding_revision_unavailable", ["imported_finding_revision"]
            return "report", "report_manifest", schema, "needs_review", reason, [reason or "report_binding"]
        return "structured_valid", "structured_record", schema, "needs_review", "legacy_record_requires_typed_import_mapping", ["typed_import_mapping"]
    if "report" in lower:
        return "report", "report_narrative", None, "needs_review", "narrative_without_revision_binding", ["finding_revision","adjudication_review","claim_proof_matrix"]
    if path.suffix.lower() in {".md",".txt",".rst"}:
        return "narrative_only", "narrative", None, "needs_review", "narrative_not_structured_truth", ["authoritative_status"]
    return "unknown", "unknown", None, "needs_review", "unclassified_source", ["source_classification"]


def inventory(root: Path, *, resolve_root: bool = True) -> dict[str, Any]:
    root=root.resolve() if resolve_root else root;entries=[];engagements=root/"engagements" if (root/"engagements").is_dir() else root
    for engagement in sorted(path for path in engagements.iterdir() if path.is_dir() and path.name!="_TEMPLATE"):
        paths=sorted((path for path in engagement.rglob("*") if path.is_file() or path.is_symlink()),key=lambda path:path.relative_to(engagement).as_posix())
        for path in paths:
            classification,kind,schema,disposition,reason,unresolved=_classify_source(engagement,path)
            proposed=["legacy.record_imported"]
            entries.append({"engagement_id":engagement.name,"kind":kind,"classification":classification,"source_path":path.relative_to(engagement).as_posix(),"source_hash":_source_hash(path),"source_schema":schema,"disposition":disposition,"reason":reason,"proposed_events":proposed,"proposed_revision":None,"unresolved_fields":unresolved})
    per_engagement={}
    for entry in entries:
        summary=per_engagement.setdefault(entry['engagement_id'],{'representable':0,'needs_review':0,'proposed_event_count':0,'unresolved_count':0,'source_file_count':0})
        summary[entry['disposition']]+=1;summary['proposed_event_count']+=len(entry['proposed_events']);summary['unresolved_count']+=len(entry['unresolved_fields']);summary['source_file_count']+=1
    counts={key:sum(1 for entry in entries if entry['disposition']==key) for key in ('representable','needs_review')};classes={key:sum(1 for entry in entries if entry['classification']==key) for key in ('structured_valid','structured_drifted','narrative_only','artifact','report','submission_like','unknown')}
    payload={"schema_version":1,"mode":"dry_run","corpus_root":".","entries":entries,"per_engagement":per_engagement,"classifications":classes,"counts":{**counts,"total":len(entries)},"invented_attempts":0,"source_bytes_modified":False}
    payload['inventory_hash']=sha256_bytes(canonical_json_bytes(payload));return payload


def write_dry_run_bundle(root: Path, engagement_id: str, operator_id: str, recorded_at: str, output: Path, *, producer_role: str = 'operator', producer_id: str | None = None) -> dict[str, Any]:
    result=inventory(root);base=(root.resolve()/"engagements" if (root.resolve()/"engagements").is_dir() else root.resolve());engagement=base/engagement_id
    if _signed_operator(engagement/'scope.md')!=operator_id:raise ValueError('operator does not match signed scope')
    proposal=_proposal_payload(result,root,engagement_id,operator_id,recorded_at,producer_role=producer_role,producer_id=producer_id);selected=proposal['entries']
    output.mkdir(parents=True,exist_ok=False);(output/'proposed-finding-revisions').mkdir()
    scoped={**result,'entries':selected,'per_engagement':{engagement_id:result['per_engagement'].get(engagement_id,{})},'counts':{'representable':sum(e['disposition']=='representable' for e in selected),'needs_review':sum(e['disposition']=='needs_review' for e in selected),'total':len(selected)}};scoped['inventory_hash']=sha256_bytes(canonical_json_bytes({k:v for k,v in scoped.items() if k!='inventory_hash'}))
    (output/'inventory.json').write_bytes(canonical_json_bytes(scoped))
    events=[{'event_type':'legacy.record_imported','source_path':entry['source_path'],'source_hash':entry['source_hash'],'migration_disposition':entry['disposition']} for entry in selected]
    (output/'proposed-events.jsonl').write_bytes(b''.join(canonical_json_bytes(event) for event in events))
    for item in proposal['proposed_finding_revisions']:
        finding=item['record'];directory=output/'proposed-finding-revisions'/finding['finding_id'];directory.mkdir();(directory/'rev-1.json').write_bytes(canonical_json_bytes(finding))
    unresolved={'engagement_id':engagement_id,'entries':[{'source_path':entry['source_path'],'reason':entry['reason'],'unresolved_fields':entry['unresolved_fields']} for entry in selected if entry['unresolved_fields']]};(output/'unresolved.json').write_bytes(canonical_json_bytes(unresolved))
    return {'engagement_id':engagement_id,'producer':proposal['operator'],'scope_operator_id':operator_id,'source_files':len(selected),'proposed_events':len(events),'proposed_finding_revisions':len(proposal['proposed_finding_revisions']),'unresolved':len(unresolved['entries']),'invented_attempts':0,'source_bytes_modified':False}

def _signed_operator(scope: Path) -> str:
    text=scope.read_text(encoding='utf-8');operator=re.search(r'^- Operator:\s*(.+?)\s*$',text,re.M)
    if not operator or not re.search(r'^- Signed:\s*\[[xX]\]\s*$',text,re.M): raise ValueError('signed scope required')
    return re.sub(r'[^A-Za-z0-9._:-]+','-',operator.group(1).strip()).strip('-') or 'operator'


def _legacy_finding_revision(source: dict[str, Any], engagement_id: str, artifact_id: str, source_hash: str, recorded_at: str, operator_id: str) -> dict[str, Any]:
    is_v3=source.get('schema_version')==3;claims=source.get('claims',{}) if is_v3 else {};severity=source.get('classification',{}).get('severity',{}).get('label') if is_v3 else source.get('severity');severity=severity if severity in {'informational','low','medium','high','critical'} else 'informational'
    raw_id=source.get('finding_id') if is_v3 else source.get('id');finding_id=re.sub(r'[^A-Za-z0-9._:-]+','-',str(raw_id or f'legacy-{source_hash[-12:]}')).strip('-') or f'legacy-{source_hash[-12:]}'
    mechanism=(claims.get('mechanism') or {}).get('statement') if is_v3 else source.get('surface');reach=(claims.get('reachability') or {}).get('statement') if is_v3 else source.get('objective');impact=((claims.get('impact_claims') or [{}])[0]).get('statement') if is_v3 else None
    mechanism=str(mechanism or 'Legacy record contains a finding mechanism that requires independent reconstruction.');reach=str(reach or 'Legacy reachability was not preserved as broker-owned evidence.');impact=str(impact or f"Legacy record reports status {source.get('status','unknown')}; impact remains unadjudicated.")
    proof_rows=[{'claim_id':cid,'attempt_refs':[],'artifact_refs':[artifact_id],'control_refs':[],'replay_refs':[],'applicability_rationale':'Only the immutable legacy source artifact is available; attempts, controls, and replay were not reconstructed.'} for cid in ('claim-mechanism','claim-reach','claim-impact')]
    record={'schema_version':3,'finding_id':finding_id,'engagement_id':engagement_id,'revision':1,'supersedes_revision':None,'recorded_at':recorded_at,'change_reason':'initial legacy reconstruction','classification':{'domain':str(source.get('owasp') or source.get('classification',{}).get('domain') or 'legacy-import'),'weakness_identifiers':[],'severity':{'label':severity,'system':'legacy-record','vector':None,'rationale':'Preserved legacy label only; independent severity adjudication is unavailable.'}},'scope_provenance':{'target_refs':[],'provenance':{'actor':{'role':'migration','id':operator_id},'model':None,'provider':None,'prompt_version':None,'card_versions':[],'tool_versions':[]}},'claim_state':'needs_review','claims':{'mechanism':{'claim_id':'claim-mechanism','statement':mechanism,'evidence_refs':[artifact_id]},'attacker_model':'Historical attacker model unresolved.','preconditions':['Historical preconditions require reconstruction.'],'reachability':{'claim_id':'claim-reach','statement':reach,'evidence_refs':[artifact_id],'causal_spine':['legacy source record','unreconstructed reachability']},'impact_claims':[{'claim_id':'claim-impact','statement':impact,'status':'inferred','evidence_refs':[artifact_id]}],'conflicting_evidence':[],'uncertainty':['Attempts, controls, environment identity, and adjudication are unavailable.']},'proof':{'primary_attempt_refs':[],'negative_control_refs':[],'positive_control_refs':[],'replay_refs':[],'evidence_refs':[],'fresh_state_properties':[],'contamination_disposition':'unresolved','claim_proofs':proof_rows,'control_applicability':{'negative':'not_applicable','positive':'not_applicable','replay':'not_applicable','rationale':'Historical attempts and controls are unavailable and were not invented.'}},'adjudication':{'justification':'Historical record reconstructed only into needs_review; no adjudication authority was inferred.'},'search_linkage':{'candidate_refs':[],'hypothesis_refs':[]},'legacy_import':{'source_artifact_ref':artifact_id,'source_hash':source_hash,'missing_legacy_evidence':['scope','environment','attempts','controls','replay','adjudication']}}
    errors=validate_record(record,'finding-v3')
    if errors:raise ValueError(f'legacy finding reconstruction invalid: {errors}')
    return record


def _proposal_payload(result: dict[str, Any], root: Path, engagement_id: str, operator_id: str, recorded_at: str, *, resolve_root: bool = True, producer_role: str = 'operator', producer_id: str | None = None) -> dict[str, Any]:
    entries=[entry for entry in result["entries"] if entry["engagement_id"]==engagement_id];root_base=root.resolve() if resolve_root else root;base=(root_base/"engagements" if (root_base/"engagements").is_dir() else root_base)/engagement_id;findings=[]
    source_finding_ids={}
    for number,entry in enumerate(entries,1):
        if entry['kind']=='finding' and entry['source_schema'] in {'finding-v2-legacy','finding-v3'}:
            source=load_json(base/entry['source_path']);reconstructed=_legacy_finding_revision(source,engagement_id,f"legacy-artifact-{number:05d}",entry['source_hash'],recorded_at,producer_id or operator_id);findings.append({'source_path':entry['source_path'],'record':reconstructed});source_finding_ids[str(source.get('finding_id') or source.get('id'))]=reconstructed['finding_id']
    # Reconstructed findings are deliberately needs_review, so historical reports cannot become
    # authoritative destination reports. Their source bytes remain artifacts and their binding stays unresolved.
    report_bindings=[]
    return {"schema_version":1,"proposal_only":True,"operator":{"role":producer_role,"id":producer_id or operator_id},"scope_operator_id":operator_id,"engagement_id":engagement_id,"recorded_at":recorded_at,"inventory_hash":result["inventory_hash"],"entries":entries,"proposed_finding_revisions":findings,"report_bindings":report_bindings,"invented_attempts":0,"apply_authorized":False}


def write_proposal(root: Path, engagement_id: str, operator_id: str, recorded_at: str, output: Path, *, producer_role: str = 'operator', producer_id: str | None = None) -> dict[str, Any]:
    result=inventory(root);engagement_root=(root/'engagements' if (root/'engagements').is_dir() else root)/engagement_id
    if _signed_operator(engagement_root/'scope.md')!=operator_id: raise ValueError('operator does not match signed scope')
    proposal=_proposal_payload(result,root,engagement_id,operator_id,recorded_at,producer_role=producer_role,producer_id=producer_id)
    output.write_bytes(canonical_json_bytes(proposal));return proposal


def _same_or_ancestor(left: Path, right: Path) -> bool:
    """True when left aliases right or an existing ancestor of right, including mount aliases."""
    return left.exists() and any(candidate.exists() and os.path.samefile(left, candidate) for candidate in (right, *right.parents))


def apply_proposal(root: Path, proposal_path: Path, destination: Path, operator_id: str, recorded_at: str, *, operator_redaction_attested: bool = False, artifact_review_path: Path | None = None, bound_root_fd: int | None = None, bound_destination_fd: int | None = None, destination_engagement_id: str | None = None, resume_authorized: bool = False, authority_request_ref: str | None = None, authority_action_digest: str | None = None, authority_control_engagement_id: str | None = None, expected_source_scope_hash: str | None = None, expected_destination_scope_hash: str | None = None, executor_id: str | None = None, executor_session_id: str | None = None) -> dict[str, Any]:
    proposal=load_json(proposal_path);source_engagement_id=proposal['engagement_id'];root_base=Path(f'/dev/fd/{bound_root_fd}') if bound_root_fd is not None else root.resolve();source_base=(root_base/'engagements' if (root_base/'engagements').is_dir() else root_base);source_engagement=source_base/source_engagement_id;engagement_root=Path(f'/dev/fd/{bound_destination_fd}') if bound_destination_fd is not None else destination.resolve();engagement_id=destination_engagement_id or engagement_root.name
    if _same_or_ancestor(source_engagement,engagement_root) or _same_or_ancestor(engagement_root,source_engagement):raise ValueError('migration destination must be filesystem-separate from source engagement')
    if not operator_redaction_attested:raise ValueError('operator redaction attestation required before legacy bytes may be copied')
    source_scope_hash=sha256_file(source_engagement/'scope.md');destination_scope_hash=sha256_file(engagement_root/'scope.md')
    if _signed_operator(source_engagement/'scope.md')!=operator_id or _signed_operator(engagement_root/'scope.md')!=operator_id:raise ValueError('operator must match signed source and destination scopes')
    if expected_source_scope_hash is not None and (source_scope_hash!=expected_source_scope_hash or destination_scope_hash!=expected_destination_scope_hash):raise ValueError('migration scope binding changed after authorization')
    producer=proposal.get('operator',{}); producer_role=producer.get('role'); producer_id=producer.get('id')
    if proposal.get('scope_operator_id')!=operator_id or producer_role not in {'operator','broker'} or not isinstance(producer_id,str):raise ValueError('proposal provenance or scope operator binding invalid')
    if authority_request_ref and (producer_role!='broker' or executor_id!=producer_id or not executor_session_id):raise ValueError('authorized migration executor provenance invalid')
    actor_role='broker' if authority_request_ref else producer_role;actor_id=executor_id if authority_request_ref else producer_id
    current=inventory(root_base,resolve_root=False);expected=_proposal_payload(current,root_base,source_engagement_id,operator_id,recorded_at,resolve_root=False,producer_role=producer_role,producer_id=producer_id)
    if not resume_authorized and canonical_json_bytes(proposal)!=canonical_json_bytes(expected):raise ValueError('proposal is stale, tampered, or operator-mismatched')
    from engagement_state import atomic_write, _append_kernel_event_idempotent as append_event, base_event, initialize_engagement, read_governed_file, read_ledger, _register_legacy_artifact as register_artifact
    if proposal.get('recorded_at')!=recorded_at:raise ValueError('proposal and apply timestamps must match')
    risky=[entry for entry in proposal['entries'] if entry['classification'] in {'artifact','unknown'}];artifact_reviews={}
    if risky:
        if artifact_review_path is None:raise ValueError('artifact/unknown sources require a complete operator artifact review')
        review=load_json(artifact_review_path);errors=validate_record(review,'migration-artifact-review')
        if errors:raise ValueError(f'artifact review invalid: {errors}')
        if review['inventory_hash']!=proposal['inventory_hash'] or review['operator']!={'role':'operator','id':operator_id}:raise ValueError('artifact review authority or inventory mismatch')
        if any(entry.get('advisory_zone')!='clear_local' or entry.get('contains_executable_capability') or entry.get('escalation_confirmation_event_ref') is not None for entry in review['entries']):raise ValueError('migration apply accepts only operator-reviewed clear_local inert artifacts; Zone-2 uses the canonical precreation flow')
        artifact_reviews={entry['source_path']:entry for entry in review['entries']}
        expected_risky={(entry['source_path'],entry['source_hash'],entry['classification']) for entry in risky};reviewed={(entry['source_path'],entry['source_hash'],entry['classification']) for entry in review['entries']}
        if reviewed!=expected_risky:raise ValueError('artifact review must cover every and only artifact/unknown source')
    elif artifact_review_path is not None:raise ValueError('artifact review supplied but inventory has no artifact/unknown sources')
    if proposal.get('proposed_finding_revisions') and engagement_id!=source_engagement_id:raise ValueError('finding reconstruction destination must retain the source engagement id')
    finding_ids=[item['record']['finding_id'] for item in proposal.get('proposed_finding_revisions',[])];
    if len(finding_ids)!=len(set(finding_ids)):raise ValueError('reconstructed finding IDs collide')
    sources=[];staging=tempfile.TemporaryFile()
    for entry in proposal['entries']:
        source=source_engagement/entry['source_path'];fd=os.open(source,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0))
        try:
            before=os.fstat(fd)
            if not stat.S_ISREG(before.st_mode):raise ValueError(f"legacy source changed or is not a regular file: {entry['source_path']}")
            chunks=[]
            while True:
                chunk=os.read(fd,1024*1024)
                if not chunk:break
                chunks.append(chunk)
            after=os.fstat(fd)
            if (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns):raise ValueError(f"legacy source changed during read: {entry['source_path']}")
        finally:os.close(fd)
        data=b''.join(chunks)
        if sha256_bytes(data)!=entry['source_hash']:raise ValueError(f"legacy source changed or is not a regular file: {entry['source_path']}")
        if detect_secret_classes(data):raise ValueError(f"secret-shaped legacy source requires operator redaction outside migration: {entry['source_path']}")
        offset=staging.tell();staging.write(data);sources.append((entry,offset,len(data)))
    if not read_ledger(engagement_root,'event'):initialize_engagement(engagement_root,recorded_at)
    manifest_entries=[]
    evidence_dir=engagement_root/'evidence'/'legacy';evidence_dir.mkdir(parents=True,exist_ok=True)
    for number,(entry,offset,size) in enumerate(sources,1):
        artifact_id=f"legacy-artifact-{number:05d}"
        copied=evidence_dir/f"{number:05d}-{Path(entry['source_path']).name}";staging.seek(offset);data=staging.read(size);atomic_write(copied,data)
        if sha256_file(copied)!=entry['source_hash']:raise ValueError(f"legacy copy fidelity failure: {entry['source_path']}")
        try:
            artifact_review=artifact_reviews.get(entry['source_path'],{});advisory_zone=artifact_review.get('advisory_zone','clear_local');existing_artifact=next((item for item in read_ledger(engagement_root,'artifact') if item['artifact_id']==artifact_id),None)
            if existing_artifact is not None:
                if existing_artifact.get('relative_path')!=copied.relative_to(engagement_root).as_posix() or existing_artifact.get('sha256')!=entry['source_hash']:raise ValueError(f"legacy artifact resume mismatch: {entry['source_path']}")
            else: register_artifact(engagement_root,copied,{'schema_version':1,'artifact_id':artifact_id,'engagement_id':engagement_id,'created_at':recorded_at,'producer':{'role':actor_role,'id':actor_id},**({'producer_session_id':executor_session_id} if executor_session_id else {}),'acquisition_method':'migration','target_refs':[],'environment_ref':None,'media_type':mimetypes.guess_type(source.name)[0] or 'application/octet-stream','sensitivity':'internal','redaction_status':'not_needed','contains_executable_capability':artifact_review.get('contains_executable_capability',False),'advisory_zone':advisory_zone,'escalation_confirmation_event_ref':artifact_review.get('escalation_confirmation_event_ref'),'cleanup_obligation_ref':artifact_review.get('cleanup_obligation_ref'),'supersedes_artifact_id':None})
        except RecordError as exc:
            raise ValueError(f"legacy artifact registration failed: {exc.as_dict()}") from exc
        manifest_entries.append({'source_path':entry['source_path'],'source_hash':entry['source_hash'],'disposition':'imported' if entry['disposition']=='representable' else 'needs_review','source_artifact_ref':artifact_id,'imported_finding_id':None,'imported_revision':None,'missing_legacy_evidence':entry['unresolved_fields']})
    proposed_by_source={item['source_path']:item['record'] for item in proposal.get('proposed_finding_revisions',[])}
    for entry in manifest_entries:
        finding=proposed_by_source.get(entry['source_path'])
        if finding is None:continue
        finding_path=engagement_root/'findings'/finding['finding_id']/'rev-1.json';finding_bytes=canonical_json_bytes(finding)
        try: prior_finding=read_governed_file(finding_path)
        except FileNotFoundError: prior_finding=None
        if prior_finding is not None and prior_finding!=finding_bytes:raise ValueError(f"migration finding resume mismatch: {finding['finding_id']}")
        if prior_finding is None:atomic_write(finding_path,finding_bytes)
        commit=base_event(event_id=f"event-legacy-finding-{finding['finding_id']}-commit",engagement_id=engagement_id,recorded_at=recorded_at,actor_role=actor_role,actor_id=actor_id,event_type='record.committed',rationale='Commit a needs_review v3 reconstruction from operator-approved legacy fields.',payload={'record_path':finding_path.relative_to(engagement_root).as_posix(),'record_digest':sha256_file(finding_path),'record_type':'finding-v3','record_id':finding['finding_id'],'record_revision':1,**({'authority_request_ref':authority_request_ref} if authority_request_ref else {})},session_id=executor_session_id,operation_class='authority' if authority_request_ref else None);append_event(engagement_root,commit)
        entry['imported_finding_id']=finding['finding_id'];entry['imported_revision']=1
    # A needs_review reconstruction cannot satisfy deterministic report rendering or acceptance authority;
    # report entries therefore retain null binding fields and explicit unresolved evidence.
    manifest={'schema_version':1,'migration_id':f'migration-{source_engagement_id}-into-{engagement_id}','engagement_id':engagement_id,'recorded_at':recorded_at,'source_inventory_hash':proposal['inventory_hash'],'operator':{'role':'operator','id':operator_id},'producer':{'role':actor_role,'id':actor_id},**({'producer_session_id':executor_session_id} if executor_session_id else {}),'scope_operator_id':operator_id,**({'authority_request_ref':authority_request_ref,'authority_action_digest':authority_action_digest,'authority_control_engagement_id':authority_control_engagement_id,'source_scope_hash':source_scope_hash,'destination_scope_hash':destination_scope_hash} if authority_request_ref and authority_action_digest and authority_control_engagement_id else {}),'entries':manifest_entries,'outcome_counts':{'imported':sum(entry['disposition']=='imported' for entry in manifest_entries),'needs_review':sum(entry['disposition']=='needs_review' for entry in manifest_entries),'skipped':0,'errors':0}}
    path=engagement_root/'legacy'/'migration-manifest.json'
    manifest_bytes=canonical_json_bytes(manifest)
    try: prior_manifest=read_governed_file(path)
    except FileNotFoundError: prior_manifest=None
    if prior_manifest is not None and prior_manifest!=manifest_bytes:raise ValueError('migration manifest resume mismatch')
    if prior_manifest is None:atomic_write(path,manifest_bytes)
    commit=base_event(event_id=f'event-migration-{engagement_id}-commit',engagement_id=engagement_id,recorded_at=recorded_at,actor_role=actor_role,actor_id=actor_id,event_type='record.committed',rationale='Commit operator-reviewed legacy migration manifest.',payload={'record_path':'legacy/migration-manifest.json','record_digest':sha256_file(path),'record_type':'migration-manifest','record_id':manifest['migration_id'],'record_revision':None,**({'authority_request_ref':authority_request_ref} if authority_request_ref else {})},session_id=executor_session_id,operation_class='authority' if authority_request_ref else None);append_event(engagement_root,commit)
    for number,entry in enumerate(manifest_entries,1):
        reconstructed_source=entry['source_path'] in proposed_by_source
        event=base_event(event_id=f'event-legacy-import-{number}',engagement_id=engagement_id,recorded_at=recorded_at,actor_role='migration',actor_id=actor_id,event_type='legacy.record_imported',rationale='Preserve legacy source truth as needs_review without inventing attempts.',payload={'source_path':entry['source_path'],'source_hash':entry['source_hash'],'migration_disposition':entry['disposition'],'source_artifact_ref':entry['source_artifact_ref'],'imported_finding_id':entry['imported_finding_id'] if reconstructed_source else None,'imported_revision':entry['imported_revision'] if reconstructed_source else None,**({'authority_request_ref':authority_request_ref} if authority_request_ref else {})},session_id=executor_session_id,operation_class='authority');append_event(engagement_root,event)
    staging.close();return {'migration_id':manifest['migration_id'],'entries':len(manifest_entries),'legacy_artifacts_registered':len(manifest_entries),'invented_attempts':0,'source_bytes_modified':False}


def self_test()->int:
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp);e=root/'engagements'/'legacy';(e/'reports').mkdir(parents=True);(e/'findings').mkdir();(e/'progress.md').write_text('# Legacy\nSubmitted finding narrative.\n');(e/'scope.md').write_text('- Operator: operator-test\n- Signed: [x]\n');fixture=Path(__file__).resolve().parents[1]/'fixtures/findings/example-legacy-finding.json';legacy_finding=load_json(fixture);legacy_finding['schema_version']=2;(e/'findings'/'legacy.json').write_bytes(canonical_json_bytes(legacy_finding));(e/'artifacts').mkdir();(e/'artifacts'/'inert.txt').write_text('inert historical fixture\n');(e/'submissions').mkdir();(e/'submissions'/'submit.sh').write_text('# inert executable-shaped fixture\n')
        a=inventory(root);source_hashes={path.relative_to(e).as_posix():sha256_file(path) for path in e.rglob('*') if path.is_file()};copy=Path(tmp)/'copy';copy.mkdir();(copy/'engagements').mkdir();shutil.copytree(e,copy/'engagements'/'legacy');b=inventory(copy)
        proposal_path=Path(tmp)/'proposal.json';proposal=write_proposal(root,'legacy','operator-test','2026-07-10T00:00:00Z',proposal_path);bundle_path=Path(tmp)/'migration-bundle';bundle=write_dry_run_bundle(root,'legacy','operator-test','2026-07-10T00:00:00Z',bundle_path)
        destination=root/'destination'/'legacy';destination.mkdir(parents=True);destination.joinpath('scope.md').write_text('# Scope\n\n## Surfaces in scope\n- Offline migration records.\n## Benign safe-objective set\n- Preserve legacy truth.\n## Escalation ceiling\n- Records only.\n## Impact-demo authorization\n- No.\n## Accounts / fixtures\n- None.\n## Authorization\n- Operator: operator-test\n- Date: 2026-07-10\n- Signed: [x]\n- Record kernel: `decision-0005-v1`\n')
        tampered=dict(proposal);tampered['entries']=[];tampered_path=Path(tmp)/'tampered.json';tampered_path.write_bytes(canonical_json_bytes(tampered));risky=[entry for entry in proposal['entries'] if entry['classification'] in {'artifact','unknown'}];artifact_review={'schema_version':1,'review_id':'migration-artifact-review-test','inventory_hash':proposal['inventory_hash'],'operator':{'role':'operator','id':'operator-test'},'operator_reviewed':True,'redaction_attested':True,'entries':[{'source_path':entry['source_path'],'source_hash':entry['source_hash'],'classification':entry['classification'],'classification_rationale':'Operator reviewed this inert fixture as clear local.','advisory_zone':'clear_local','contains_executable_capability':False,'escalation_confirmation_event_ref':None,'cleanup_obligation_ref':None} for entry in risky]};artifact_review_path=Path(tmp)/'artifact-review.json';artifact_review_path.write_bytes(canonical_json_bytes(artifact_review));tamper_blocked=alias_blocked=redaction_blocked=artifact_review_blocked=False
        try:apply_proposal(root,tampered_path,destination,'operator-test','2026-07-10T00:00:00Z')
        except ValueError:tamper_blocked=True
        try:apply_proposal(root,proposal_path,e,'operator-test','2026-07-10T00:00:00Z')
        except ValueError:alias_blocked=True
        try:apply_proposal(root,proposal_path,destination,'operator-test','2026-07-10T00:00:00Z')
        except ValueError:redaction_blocked=True
        try:apply_proposal(root,proposal_path,destination,'operator-test','2026-07-10T00:00:00Z',operator_redaction_attested=True)
        except ValueError:artifact_review_blocked=True
        applied=apply_proposal(root,proposal_path,destination,'operator-test','2026-07-10T00:00:00Z',operator_redaction_attested=True,artifact_review_path=artifact_review_path);reapplied=apply_proposal(root,proposal_path,destination,'operator-test','2026-07-10T00:00:00Z',operator_redaction_attested=True,artifact_review_path=artifact_review_path);after_hashes={path.relative_to(e).as_posix():sha256_file(path) for path in e.rglob('*') if path.is_file()}
        ok=a==b and tamper_blocked and alias_blocked and redaction_blocked and artifact_review_blocked and bundle['invented_attempts']==0 and bundle['proposed_finding_revisions']==1 and all(bundle_path.joinpath(name).exists() for name in ('inventory.json','proposed-events.jsonl','proposed-finding-revisions','unresolved.json')) and source_hashes==after_hashes and a['counts']['needs_review']>=1 and any(entry['source_path']=='submissions/submit.sh' and entry['classification']=='artifact' for entry in a['entries']) and a['invented_attempts']==0 and not a['source_bytes_modified'] and proposal['proposal_only'] and not proposal['apply_authorized'] and applied==reapplied and destination.joinpath('legacy/migration-manifest.json').is_file() and destination.joinpath('findings/FX-legacy-bola/rev-1.json').is_file()
        if not ok:print({'equal_inventory':a==b,'tamper':tamper_blocked,'alias':alias_blocked,'redaction':redaction_blocked,'bundle_findings':bundle['proposed_finding_revisions'],'source_unchanged':source_hashes==after_hashes,'needs_review':a['counts']['needs_review'],'applied':applied})
        print(f"MIGRATION DRY-RUN SELF-TEST: {'PASS' if ok else 'FAIL'}");return 0 if ok else 1


def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=Path('.'));ap.add_argument('--output',type=Path);ap.add_argument('--self-test',action='store_true');ap.add_argument('--propose-engagement');ap.add_argument('--dry-run-engagement');ap.add_argument('--migration-dir',type=Path);ap.add_argument('--apply-proposal',type=Path);ap.add_argument('--destination',type=Path);ap.add_argument('--operator-id');ap.add_argument('--recorded-at');ap.add_argument('--artifact-review',type=Path);args=ap.parse_args()
    if args.self_test:return self_test()
    if args.apply_proposal:
        raise ValueError('public migration apply requires a Decision-0006 digest-bound authority request; direct apply is disabled')
    elif args.propose_engagement or args.dry_run_engagement:
        raise ValueError('public migration proposal and dry-run require the Decision-0006 run-engagement broker path; direct operator-attributed CLI output is disabled')
    else:result=inventory(args.root)
    if not args.output:print(canonical_json_bytes(result).decode(),end='')
    elif not args.propose_engagement and not args.apply_proposal:args.output.write_bytes(canonical_json_bytes(result))
    return 0
if __name__=='__main__':raise SystemExit(main())
