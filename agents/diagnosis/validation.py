# Interpret observed API fields against the selected category SOP.
"""Interpret observed API fields against the selected category SOP."""
import re


MISSING = {"api_data", "api_fields", "completion_proof", "course_identity", "workday_status",
           "ias_status", "admin_status", "vpn_status", "maintenance_window", "sap_revision",
           "permission_status", "incident_history", "conflicting_evidence"}


# Extract bounded diagnostic values while excluding personal and sensitive response fields.
def collect_facts(data, check_id):
    facts = []
    # Walk response values recursively and collect permitted diagnostic facts.
    def visit(value, path):
        if isinstance(value, dict):
            for key, child in value.items():
                if not re.search(r"email|name|phone|secret|token|password|description|comment|url|address", key, re.I):
                    visit(child, path + [key])
        elif isinstance(value, list):
            for index, child in enumerate(value[:25]):
                visit(child, path + [index])
        elif isinstance(value, (str, int, float, bool)) and path and re.search(
            r"status|complete|pass|quiz|slide|active|access|lock|delivery|launch|retrain|date|type|progress|percentage|agreeButton|lmrEligible|vpnRequired|instructorLed|networkIssue|sapRevision|screenshotRequired|empStatID", str(path[-1]), re.I
        ):
            facts.append({"check_id": check_id, "path": path, "value": value[:120] if isinstance(value, str) else value})
    visit(data, [])
    return facts[:100]


# Check diagnosis labels, missing evidence, scenario verdicts and cited observed facts.
def validate_interpretation(result, guidance, scenario_ids, facts):
    if not isinstance(result, dict) or result.get("status") not in {"supported", "needs_more_evidence", "needs_human_review"}:
        raise ValueError("Invalid interpretation status")
    if result.get("confidence") not in {"low", "medium", "high"}:
        raise ValueError("Invalid confidence")
    labels = re.findall(r"^\* `([^`]+)`", guidance, re.M)
    if result.get("subcategory") is not None and result["subcategory"] not in labels:
        raise ValueError("Unknown subissue")
    if 'three strikes' in (result.get('subcategory') or '').lower():
        raise ValueError('Three-strike closure is a follow-up lifecycle action, not a diagnosed cause; leave subcategory null')
    missing = result.get("missing_evidence")
    if not isinstance(missing, list) or any(not isinstance(code, str) or code not in MISSING for code in missing):
        raise ValueError("Invalid missing evidence")
    verdicts = result.get("scenario_verdicts")
    if not isinstance(verdicts, list) or len(verdicts) != len(set(scenario_ids)):
        raise ValueError("Missing scenario verdicts")
    known_facts = {fact["id"] for fact in facts}
    seen = set()
    for verdict in verdicts:
        if not isinstance(verdict, dict):
            raise ValueError("Invalid verdict")
        scenario = verdict.get("scenario_id")
        if not isinstance(scenario, str) or scenario not in scenario_ids or scenario in seen:
            raise ValueError("Unknown or duplicate scenario")
        seen.add(scenario)
        if verdict.get("status") not in {"supported", "not_supported", "needs_more_evidence"}:
            raise ValueError("Invalid verdict status")
        refs = verdict.get("evidence_ids")
        if not isinstance(refs, list) or any(not isinstance(ref, str) or ref not in known_facts for ref in refs):
            raise ValueError("Fabricated evidence reference")
        if verdict["status"] in {"supported", "not_supported"} and not refs:
            raise ValueError("Verdict requires observed evidence")
    if result["status"] == "supported":
        if missing:
            raise ValueError("Supported diagnosis cannot list missing evidence; use needs_more_evidence")
        if not result.get("subcategory"):
            raise ValueError("Supported diagnosis requires an SOP subcategory; use needs_more_evidence if unknown")
        if not any(v["status"] == "supported" for v in verdicts):
            raise ValueError("Supported diagnosis requires a supported scenario verdict with observed fact IDs")
    if result["confidence"] == "high" and (missing or result["status"] != "supported"):
        raise ValueError("Unsupported high confidence")


# Validate the final diagnosis and retain only approved conclusion fields.
def finish_diagnosis(result, guidance, scenario_ids, facts, confirmed_courses=()):
    selected = result.get("scenario_ids")
    if not isinstance(selected, list) or any(not isinstance(s, str) or s not in scenario_ids for s in selected):
        raise ValueError("Unknown final scenario")
    if len(selected) != len(set(selected)):
        raise ValueError("Duplicate final scenario")
    validate_interpretation(result, guidance, selected, facts)
    if ('course_identity' in result['missing_evidence'] and len(set(confirmed_courses)) == 1
            and 'conflicting_evidence' not in result['missing_evidence']):
        raise ValueError('Course identity is already confirmed by a successful scoped read. Reuse it; '
                         'investigate the remaining gap instead of requesting it again. If identity conflicts, '
                         'report conflicting_evidence. API data/fields are internal gaps, not user requests.')
    clean = {key: result[key] for key in ("status", "subcategory", "confidence", "missing_evidence")}
    clean["scenario_verdicts"] = [{key: v[key] for key in ("scenario_id", "status", "evidence_ids")} for v in result["scenario_verdicts"]]
    return clean
