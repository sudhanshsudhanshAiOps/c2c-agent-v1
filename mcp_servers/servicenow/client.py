# Implement ServiceNow incident, caller, journal and attachment operations.
import re
import os
from datetime import datetime, timezone

from . import create_client as _client


IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/gif", "image/bmp", "image/webp"}
MAX_SCREENSHOT_BYTES = 10 * 1024 * 1024


# Read recent comments authored by the verified caller, excluding bot notes.
def fetch_caller_replies(incident_sys_id: str, caller_user_name: str, since: str) -> list:
    """Read recent comments authored by the verified caller, excluding bot notes."""
    if not re.fullmatch(r"[0-9a-fA-F]{32}", incident_sys_id):
        raise ValueError("Invalid incident sys_id")
    if not re.fullmatch(r"[\w.@+-]{1,200}", caller_user_name):
        raise ValueError("Unsupported caller user name")
    timestamp = datetime.fromisoformat(since).astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    with _client() as client:
        response = client.get('/api/now/table/sys_journal_field', params={
            'sysparm_query': f'element_id={incident_sys_id}^name=incident^element=comments'
                             f'^sys_created_by={caller_user_name}^sys_created_on>={timestamp}^ORDERBYDESCsys_created_on',
            'sysparm_fields': 'sys_id,value,sys_created_on,sys_created_by', 'sysparm_limit': '100',
        })
        response.raise_for_status()
        return list(reversed(response.json().get('result', [])))


# Fetch an incident by number and optionally include its displayed journal fields.
def fetch_incident(
    number: str,
    display_value: bool = False,
    include_journal: bool = True,
) -> dict:
    with _client() as c:
        r = c.get(
            "/api/now/table/incident",
            params={
                "sysparm_query": f"number={number}",
                "sysparm_display_value": "true" if display_value else "false",
                "sysparm_limit": "1",
            },
        )
        r.raise_for_status()
        results = r.json().get("result", [])
        if not results:
            return {}

        incident = results[0]
        if not include_journal:
            return incident

        journal_response = c.get(
            "/api/now/table/incident",
            params={
                "sysparm_query": f"number={number}",
                "sysparm_fields": "comments,work_notes",
                "sysparm_display_value": "true",
                "sysparm_limit": "1",
            },
        )
        journal_response.raise_for_status()
        journal_results = journal_response.json().get("result", [])
        journal_fields = journal_results[0] if journal_results else {}

        for field in ("comments", "work_notes"):
            value = journal_fields.get(field, "")
            if isinstance(value, dict):
                value = value.get("display_value") or value.get("value", "")
            incident[field] = value or ""

        return incident


# Fetch the exact ServiceNow incident identified by its sys_id.
def fetch_incident_by_sys_id(
    sys_id: str,
    display_value: bool = False,
    include_journal: bool = True,
) -> dict:
    """Fetch the exact ServiceNow incident identified by its sys_id."""
    if not re.fullmatch(r"[0-9a-fA-F]{32}", sys_id):
        raise ValueError("Invalid incident sys_id")

    with _client() as client:
        response = client.get(
            f"/api/now/table/incident/{sys_id}",
            params={"sysparm_display_value": "true" if display_value else "false"},
        )
        if response.status_code == 404:
            return {}
        response.raise_for_status()
        incident = response.json().get("result", {})
        if not incident or not include_journal:
            return incident

        journal_response = client.get(
            f"/api/now/table/incident/{sys_id}",
            params={
                "sysparm_fields": "comments,work_notes",
                "sysparm_display_value": "true",
            },
        )
        journal_response.raise_for_status()
        journal = journal_response.json().get("result", {})
        for field in ("comments", "work_notes"):
            value = journal.get(field, "")
            if isinstance(value, dict):
                value = value.get("display_value") or value.get("value", "")
            incident[field] = value or ""
        return incident


# Look up the display name of the incident caller.
def fetch_caller_name(sys_id: str) -> str:
    with _client() as c:
        r = c.get(
            f"/api/now/table/sys_user/{sys_id}",
            params={"sysparm_fields": "name"},
        )
        r.raise_for_status()
        return r.json().get("result", {}).get("name", "")


# Read the approved shared ID; User ID (user_name) is the dummy convention.
def fetch_caller_global_id(sys_id: str) -> str:
    """Read the approved shared ID; User ID (user_name) is the dummy convention."""
    if not re.fullmatch(r"[0-9a-fA-F]{32}", sys_id):
        raise ValueError("Invalid caller sys_id")
    field = os.getenv("SN_CALLER_GLOBAL_ID_FIELD", "user_name")
    if not re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", field):
        raise ValueError("Invalid caller Global ID field")
    with _client() as c:
        response = c.get(f"/api/now/table/sys_user/{sys_id}", params={"sysparm_fields": field})
        response.raise_for_status()
        value = response.json().get("result", {}).get(field)
    return value.strip() if isinstance(value, str) else ""


# List attachments belonging to the incident.
def fetch_attachments(sys_id: str) -> list:
    with _client() as c:
        r = c.get(
            "/api/now/attachment",
            params={"sysparm_query": f"table_sys_id={sys_id}"},
        )
        r.raise_for_status()
        return r.json().get("result", [])


# Check whether the incident has an eligible image attachment.
def has_screenshot(sys_id: str) -> bool:
    return bool(list_screenshots(sys_id))


# List eligible screenshot attachments belonging to the incident.
def list_screenshots(incident_sys_id: str) -> list[dict]:
    if not re.fullmatch(r"[0-9a-fA-F]{32}", incident_sys_id):
        raise ValueError("Invalid incident sys_id")
    return [
        attachment
        for attachment in fetch_attachments(incident_sys_id)
        if attachment.get("content_type", "").lower() in IMAGE_TYPES
    ]


# Validate attachment ownership and image metadata, then download its bounded image bytes.
def fetch_screenshot(incident_sys_id: str, attachment_sys_id: str) -> dict:
    if not re.fullmatch(r"[0-9a-fA-F]{32}", attachment_sys_id):
        raise ValueError("Invalid attachment sys_id")
    attachment = next(
        (item for item in list_screenshots(incident_sys_id) if item.get("sys_id") == attachment_sys_id),
        None,
    )
    if attachment is None:
        raise ValueError("Screenshot is not attached to this incident")

    size = int(attachment.get("size_bytes") or 0)
    if size > MAX_SCREENSHOT_BYTES:
        raise ValueError("Screenshot exceeds the 10 MB limit")

    with _client() as client:
        with client.stream("GET", f"/api/now/attachment/{attachment_sys_id}/file") as response:
            response.raise_for_status()
            chunks = []
            total = 0
            for chunk in response.iter_bytes():
                total += len(chunk)
                if total > MAX_SCREENSHOT_BYTES:
                    raise ValueError("Screenshot exceeds the 10 MB limit")
                chunks.append(chunk)
    image = b"".join(chunks)
    return {
        "file_name": attachment.get("file_name", ""),
        "content_type": attachment["content_type"].lower(),
        "image": image,
    }


# Read the incident work-note journal by incident number.
def fetch_work_notes(number: str) -> str:
    with _client() as c:
        r = c.get(
            "/api/now/table/incident",
            params={
                "sysparm_query": f"number={number}",
                "sysparm_fields": "work_notes",
                "sysparm_display_value": "true",
                "sysparm_limit": "1",
            },
        )
        r.raise_for_status()
        results = r.json().get("result", [])
        return results[0].get("work_notes", "") if results else ""


# Set the specified ServiceNow incident state and return the updated record.
def update_state(sys_id: str, state: str) -> dict:
    with _client() as c:
        r = c.put(
            f"/api/now/table/incident/{sys_id}",
            json={"state": state},
        )
        r.raise_for_status()
        return r.json().get("result", {})


# Apply the supplied fields to the specified ServiceNow incident.
def update_incident(sys_id: str, fields: dict) -> dict:
    with _client() as c:
        r = c.put(f"/api/now/table/incident/{sys_id}", json=fields)
        r.raise_for_status()
        return r.json().get("result", {})


# Apply this helper's configured resolution state, close code and close notes.
def close_incident(sys_id: str, close_notes: str) -> dict:
    return update_incident(
        sys_id,
        {
            "state": "6",
            "close_code": "Solved (Permanently)",
            "close_notes": close_notes,
        },
    )


# Append an internal work note to the specified incident.
def add_work_note(sys_id: str, note: str) -> dict:
    with _client() as c:
        r = c.put(
            f"/api/now/table/incident/{sys_id}",
            json={"work_notes": note},
        )
        r.raise_for_status()
        return r.json().get("result", {})


# Append a user-visible comment to the specified incident.
def add_comment(sys_id: str, comment: str) -> dict:
    with _client() as c:
        r = c.put(
            f"/api/now/table/incident/{sys_id}",
            json={"comments": comment},
        )
        r.raise_for_status()
        return r.json().get("result", {})
