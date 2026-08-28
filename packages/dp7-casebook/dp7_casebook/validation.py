"""Strict, dependency-free validation of manually adjudicated DP7 casebooks.

This module deliberately never infers an industry conclusion or a case grade.  It
only checks that a human supplied a complete, internally permitted record.
"""

from __future__ import annotations

import datetime as dt
from collections import Counter
from typing import Any
from urllib.parse import urlparse

SCHEMA_VERSION = "dp7.casebook.input.v1"
GRADES = {"A", "B", "C", "D"}
USAGES = {"load_bearing", "background", "limit"}
ANCHOR_TYPES = {"url", "local_file", "ledger_ref", "search_protocol", "web_snapshot"}
TRAP_STATUSES = {"checked", "not_applicable"}
PROCESS_STAGES = ["disclosure_history", "procedure_paragraph", "award_or_designation", "amount_fingerprint"]
SLOT_TYPES = {"point", "edge", "knowledge_edge", "open_question"}
TRAPS = {
    "direct_terminal_customer", "accounting_period", "fx", "multi_entity",
    "trader_intermediary", "group_subject_scope", "bonded_processing_trade",
    "outsourced_process_attribution", "substrate_mixing", "lithium_copper_foil",
    "area_unit_period", "tpca_scope", "plant_legal_issuer",
}
ROOT_KEYS = {"schema_version", "cases", "references"}
CASE_KEYS = {
    "case_id", "title", "human_conclusion", "grade", "slot_references",
    "process_ladder", "evidence_chain", "alternative_explanations", "trap_checks",
    "remaining_unknowns", "overturn_conditions", "adjudicator", "adjudication_date", "version",
}
SLOT_KEYS = {"slot_type", "slot_id"}
PROCESS_KEYS = {"reached_stage", "unused_stages"}
EVIDENCE_KEYS = {
    "origin_source_id", "independence_group", "anchor_type", "anchor_locator",
    "retrieval_date", "claim_or_role", "evidence_strength",
}
ALTERNATIVE_KEYS = {"explanation", "exclusion_reason"}
TRAP_KEYS = {"status", "explanation", "evidence_anchor"}
REFERENCE_KEYS = {"reference_id", "case_id", "consumer_type", "consumer_id", "usage", "anchor"}
REFERENCE_ANCHOR_KEYS = {"anchor_type", "anchor_locator"}


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _date(value: Any) -> bool:
    if not _nonempty(value):
        return False
    try:
        dt.date.fromisoformat(value)
        return True
    except ValueError:
        return False


def _unknown_and_missing(value: Any, allowed: set[str], required: set[str], path: str, errors: list[dict[str, str]]) -> bool:
    if not isinstance(value, dict):
        errors.append(_error("not_object", path, "must be an object"))
        return False
    for key in sorted(required - value.keys()):
        errors.append(_error("missing_field", f"{path}.{key}", "required field is missing"))
    for key in sorted(value.keys() - allowed):
        errors.append(_error("unknown_field", f"{path}.{key}", "unknown fields are not permitted"))
    return True


def _error(code: str, path: str, message: str) -> dict[str, str]:
    return {"code": code, "path": path, "message": message}


def _validate_anchor(anchor_type: Any, locator: Any, path: str, errors: list[dict[str, str]]) -> None:
    if anchor_type not in ANCHOR_TYPES:
        errors.append(_error("anchor_type_invalid", f"{path}.anchor_type", "must be one of the permitted anchor types"))
        return
    if not _nonempty(locator):
        errors.append(_error("anchor_locator_empty", f"{path}.anchor_locator", "anchor locator must be non-empty"))
        return
    text = locator.strip()
    if anchor_type == "url":
        parsed = urlparse(text)
        valid = parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    elif anchor_type == "local_file":
        valid = "://" not in text and ("/" in text or text.startswith("."))
    else:
        valid = ":" in text and not any(char.isspace() for char in text)
    if not valid:
        errors.append(_error("anchor_locator_invalid", f"{path}.anchor_locator", f"invalid basic format for {anchor_type}"))


def _require_texts(value: dict[str, Any], keys: set[str], path: str, errors: list[dict[str, str]]) -> None:
    for key in sorted(keys):
        if not _nonempty(value.get(key)):
            errors.append(_error("text_required", f"{path}.{key}", "must be a non-empty string"))


def _validate_case(case: Any, index: int, errors: list[dict[str, str]]) -> str | None:
    path = f"cases[{index}]"
    if not _unknown_and_missing(case, CASE_KEYS, CASE_KEYS, path, errors):
        return None
    _require_texts(case, {"case_id", "title", "human_conclusion", "remaining_unknowns", "overturn_conditions", "adjudicator", "version"}, path, errors)
    if case.get("grade") not in GRADES:
        errors.append(_error("grade_invalid", f"{path}.grade", "grade must be A, B, C, or D"))
    if not _date(case.get("adjudication_date")):
        errors.append(_error("date_invalid", f"{path}.adjudication_date", "must be ISO-8601 YYYY-MM-DD"))

    slots = case.get("slot_references")
    if not isinstance(slots, list) or not slots:
        errors.append(_error("slots_required", f"{path}.slot_references", "at least one slot reference is required"))
    elif isinstance(slots, list):
        for slot_index, slot in enumerate(slots):
            spath = f"{path}.slot_references[{slot_index}]"
            if _unknown_and_missing(slot, SLOT_KEYS, SLOT_KEYS, spath, errors):
                if slot.get("slot_type") not in SLOT_TYPES:
                    errors.append(_error("slot_type_invalid", f"{spath}.slot_type", "unknown slot type"))
                _require_texts(slot, {"slot_id"}, spath, errors)

    ladder = case.get("process_ladder")
    if _unknown_and_missing(ladder, PROCESS_KEYS, PROCESS_KEYS, f"{path}.process_ladder", errors):
        reached = ladder.get("reached_stage")
        unused = ladder.get("unused_stages")
        if reached not in PROCESS_STAGES:
            errors.append(_error("process_stage_invalid", f"{path}.process_ladder.reached_stage", "unknown process stage"))
        if not isinstance(unused, list) or any(item not in PROCESS_STAGES for item in unused):
            errors.append(_error("unused_stage_invalid", f"{path}.process_ladder.unused_stages", "must be a stage list"))
        elif len(unused) != len(set(unused)):
            errors.append(_error("unused_stage_duplicate", f"{path}.process_ladder.unused_stages", "duplicate unused stage"))
        elif reached in PROCESS_STAGES:
            expected = PROCESS_STAGES[PROCESS_STAGES.index(reached) + 1:]
            if unused != expected:
                errors.append(_error("unused_stage_order", f"{path}.process_ladder.unused_stages", "must be exactly the later, unused stages"))

    evidence = case.get("evidence_chain")
    groups: set[str] = set()
    evidence_source_ids: set[str] = set()
    origin_groups: dict[str, set[str]] = {}
    hard_groups: set[str] = set()
    hard_origins: set[str] = set()
    hard_count = 0
    if not isinstance(evidence, list) or not evidence:
        errors.append(_error("evidence_required", f"{path}.evidence_chain", "at least one evidence entry is required"))
    elif isinstance(evidence, list):
        for evidence_index, entry in enumerate(evidence):
            epath = f"{path}.evidence_chain[{evidence_index}]"
            if _unknown_and_missing(entry, EVIDENCE_KEYS, EVIDENCE_KEYS, epath, errors):
                _require_texts(entry, {"origin_source_id", "independence_group", "claim_or_role"}, epath, errors)
                origin_id = entry.get("origin_source_id", "").strip() if _nonempty(entry.get("origin_source_id")) else ""
                group = entry.get("independence_group", "").strip() if _nonempty(entry.get("independence_group")) else ""
                if origin_id:
                    evidence_source_ids.add(origin_id)
                if _nonempty(entry.get("independence_group")):
                    groups.add(group)
                if origin_id and group:
                    origin_groups.setdefault(origin_id, set()).add(group)
                if entry.get("evidence_strength") not in {"hard", "supporting"}:
                    errors.append(_error("evidence_strength_invalid", f"{epath}.evidence_strength", "must be hard or supporting"))
                elif entry.get("evidence_strength") == "hard":
                    hard_count += 1
                    if group:
                        hard_groups.add(group)
                    if origin_id:
                        hard_origins.add(origin_id)
                _validate_anchor(entry.get("anchor_type"), entry.get("anchor_locator"), epath, errors)
                if not _date(entry.get("retrieval_date")):
                    errors.append(_error("date_invalid", f"{epath}.retrieval_date", "must be ISO-8601 YYYY-MM-DD"))
    for origin_id, claimed_groups in origin_groups.items():
        if len(claimed_groups) > 1:
            errors.append(_error("independence_group_conflict", f"{path}.evidence_chain", f"origin {origin_id} claims multiple independence groups"))
    if case.get("grade") == "A" and (len(hard_groups) < 2 or len(hard_origins) < 2):
        errors.append(_error("grade_a_independence", f"{path}.evidence_chain", "A requires hard evidence from at least two origins and independence groups"))
    if case.get("grade") == "B" and hard_count < 1:
        errors.append(_error("grade_b_hard_evidence", f"{path}.evidence_chain", "B requires at least one human-marked hard evidence entry"))

    alternatives = case.get("alternative_explanations")
    if not isinstance(alternatives, list) or not alternatives:
        errors.append(_error("alternative_required", f"{path}.alternative_explanations", "at least one alternative explanation is required"))
    elif isinstance(alternatives, list):
        for alternative_index, alternative in enumerate(alternatives):
            apath = f"{path}.alternative_explanations[{alternative_index}]"
            if _unknown_and_missing(alternative, ALTERNATIVE_KEYS, ALTERNATIVE_KEYS, apath, errors):
                _require_texts(alternative, ALTERNATIVE_KEYS, apath, errors)

    traps = case.get("trap_checks")
    if not isinstance(traps, dict):
        errors.append(_error("traps_not_object", f"{path}.trap_checks", "must be an object keyed by all 13 trap IDs"))
    else:
        for trap in sorted(TRAPS - traps.keys()):
            errors.append(_error("trap_missing", f"{path}.trap_checks.{trap}", "required trap is missing"))
        for trap in sorted(traps.keys() - TRAPS):
            errors.append(_error("trap_unknown", f"{path}.trap_checks.{trap}", "extra trap is not permitted"))
        for trap in sorted(TRAPS & traps.keys()):
            tpath = f"{path}.trap_checks.{trap}"
            item = traps[trap]
            if _unknown_and_missing(item, TRAP_KEYS, TRAP_KEYS, tpath, errors):
                if item.get("status") not in TRAP_STATUSES:
                    errors.append(_error("trap_status_invalid", f"{tpath}.status", "must be checked or not_applicable"))
                _require_texts(item, {"explanation", "evidence_anchor"}, tpath, errors)
                if _nonempty(item.get("evidence_anchor")) and item["evidence_anchor"].strip() not in evidence_source_ids:
                    errors.append(_error("trap_anchor_dangling", f"{tpath}.evidence_anchor", "must reference an origin_source_id in this case evidence chain"))
    return case.get("case_id") if _nonempty(case.get("case_id")) else None


def _validate_reference(
    reference: Any,
    index: int,
    case_grades: dict[str, str],
    case_slots: dict[str, set[tuple[str, str]]],
    errors: list[dict[str, str]],
) -> str | None:
    path = f"references[{index}]"
    if not _unknown_and_missing(reference, REFERENCE_KEYS, REFERENCE_KEYS, path, errors):
        return None
    _require_texts(reference, {"reference_id", "case_id", "consumer_type", "consumer_id"}, path, errors)
    if reference.get("consumer_type") not in SLOT_TYPES:
        errors.append(_error("consumer_type_invalid", f"{path}.consumer_type", "unknown consumer type"))
    if reference.get("usage") not in USAGES:
        errors.append(_error("usage_invalid", f"{path}.usage", "unknown reference usage"))
    case_id = reference.get("case_id")
    grade = case_grades.get(case_id) if _nonempty(case_id) else None
    if grade is None and _nonempty(case_id):
        errors.append(_error("reference_dangling", f"{path}.case_id", "referenced case_id does not exist"))
    elif grade == "C" and reference.get("usage") == "load_bearing":
        errors.append(_error("grade_c_load_bearing", f"{path}.usage", "C cases cannot be load-bearing"))
    elif grade == "D" and reference.get("usage") != "limit":
        errors.append(_error("grade_d_usage", f"{path}.usage", "D cases may only be used as limit"))
    if grade is not None and (
        str(reference.get("consumer_type")), str(reference.get("consumer_id"))
    ) not in case_slots.get(str(case_id), set()):
        errors.append(_error("reference_slot_mismatch", path, "consumer must match a declared slot_reference on the case"))
    anchor = reference.get("anchor")
    if _unknown_and_missing(anchor, REFERENCE_ANCHOR_KEYS, REFERENCE_ANCHOR_KEYS, f"{path}.anchor", errors):
        _validate_anchor(anchor.get("anchor_type"), anchor.get("anchor_locator"), f"{path}.anchor", errors)
    return reference.get("reference_id") if _nonempty(reference.get("reference_id")) else None


def _duplicate_errors(values: list[str | None], label: str, errors: list[dict[str, str]]) -> None:
    for value, count in Counter(item for item in values if item is not None).items():
        if count > 1:
            errors.append(_error(f"duplicate_{label}", label, f"duplicate {label}: {value}"))


def validate_document(document: Any) -> dict[str, Any]:
    """Return a deterministic report.  Empty ``cases`` and ``references`` are valid."""
    errors: list[dict[str, str]] = []
    if not _unknown_and_missing(document, ROOT_KEYS, ROOT_KEYS, "$", errors):
        return {"valid": False, "error_count": len(errors), "errors": errors, "case_count": 0, "reference_count": 0}
    if document.get("schema_version") != SCHEMA_VERSION:
        errors.append(_error("schema_version_invalid", "$.schema_version", f"must equal {SCHEMA_VERSION}"))
    cases = document.get("cases")
    references = document.get("references")
    if not isinstance(cases, list):
        errors.append(_error("cases_not_array", "$.cases", "must be an array"))
        cases = []
    if not isinstance(references, list):
        errors.append(_error("references_not_array", "$.references", "must be an array"))
        references = []
    case_ids = [_validate_case(case, index, errors) for index, case in enumerate(cases)]
    _duplicate_errors(case_ids, "case_id", errors)
    case_grades = {
        case_id: case["grade"] for case_id, case in zip(case_ids, cases)
        if case_id is not None and isinstance(case, dict) and case.get("grade") in GRADES
    }
    case_slots = {
        case_id: {
            (str(slot.get("slot_type")), str(slot.get("slot_id")))
            for slot in case.get("slot_references", [])
            if isinstance(slot, dict)
        }
        for case_id, case in zip(case_ids, cases)
        if case_id is not None and isinstance(case, dict)
    }
    reference_ids = [
        _validate_reference(reference, index, case_grades, case_slots, errors)
        for index, reference in enumerate(references)
    ]
    _duplicate_errors(reference_ids, "reference_id", errors)
    return {
        "valid": not errors,
        "error_count": len(errors),
        "case_count": len(cases),
        "reference_count": len(references),
        "errors": errors,
    }
