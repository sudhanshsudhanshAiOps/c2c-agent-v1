# Draft validation and approved fallback messages.
"""Draft validation and approved fallback messages."""


# Validate the generated message channels, lengths and incident reference before sending.
def validate_draft(draft, number, channels, require_screenshot=True):
    if not isinstance(draft, dict) or set(draft) != set(channels):
        raise ValueError("Communication draft must contain only the requested channels")
    for value in draft.values():
        if not isinstance(value, str) or not value.strip() or len(value) > 2000:
            raise ValueError("Invalid communication message")
        if number not in value or (require_screenshot and "screenshot" not in value.lower()):
            raise ValueError("Message must request a screenshot and reference the incident")
    return draft


# Build the approved fallback message requesting an incident screenshot.
def screenshot_request(number, channels, awaiting_state):
    fields = {}
    if "comments" in channels:
        fields["comments"] = (
            f"For incident {number}, please attach a screenshot showing the error "
            "or screen you see in C2C. This will help us review your issue."
        )
    if "work_notes" in channels:
        fields["work_notes"] = (
            "Automated triage found no screenshot attached. "
            "Requested a screenshot from the caller before classification."
        )
    if awaiting_state is not None:
        fields["state"] = awaiting_state
    return fields
