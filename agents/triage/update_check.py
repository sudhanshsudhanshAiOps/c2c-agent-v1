# Triage compares evidence it has already fetched; this module performs no I/O.
"""Triage compares evidence it has already fetched; this module performs no I/O."""
import hashlib
import json
import os
from tools.request_analyser import RECEIPT_POLICY_VERSION


# Hash relevant ticket, screenshot and caller-reply evidence to detect meaningful updates.
def evidence_fingerprint(context):
    incident = context.evidence['incident']
    images = context.evidence.get('screenshots', {}).get('screenshots', [])
    replies = context.evidence.get('caller_replies', [])
    data = {key: incident.get(key) for key in ('short_description', 'description', 'caller_id', 'active')}
    data['closed'] = str(incident.get('state')) == os.getenv('SN_CLOSED_STATE')
    data['images'] = [(row.get('attachment_sys_id'), row.get('sys_updated_on'), row.get('text', '')) for row in images]
    data['screenshot_status'] = context.evidence.get('screenshots', {}).get('status')
    data['replies'] = [(row.get('sys_id'), row.get('sys_created_on')) for row in replies]
    data['receipt_policy'] = RECEIPT_POLICY_VERSION
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


# Decide whether a completed or waiting workflow can skip unchanged evidence.
def unchanged(context, fingerprint):
    state = context.state
    return (state.get('last_triage_fingerprint') == fingerprint and not state.get('processing_update')
            and not state.get('rediagnose_requested') and not state.get('retriage_requested'))
