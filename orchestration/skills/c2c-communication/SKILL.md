---
name: c2c-communication
description: Draft concise incident updates and requests for user information.
---

# C2C communication

The orchestrator selects the action. This skill drafts wording only; it does not
classify, diagnose, choose routing, or change ticket state.

For request_screenshot, ask the caller to attach a readable screenshot of their
C2C error or affected course screen. Include the incident number and screenshot
in every requested channel.

For request_information, request only the supplied information. If a previous
answer was ambiguous, politely ask for clarification. Do not invent a fix or
claim resolution. Do not mention strike counters, deadlines, automatic reminders
or automatic closure.

When the request is structured, ask for every item in required_information and
include target_id when present. Use reason for a brief explanation. requested_by
and request_type are internal metadata; do not expose them or add requirements.
Never ask the caller for API responses, database records, backend access or tool
execution. Those are internal investigation gaps, not user-information requests.

Keep normal status updates, comments and work notes appropriate to the selected
action. Include the exact supplied incident number in every channel. Do not ask
for passwords or access tokens.

Return one JSON object containing exactly the requested channel names. Each
value must be a nonempty string of at most 2000 characters. No extra fields,
Markdown fencing, routing instructions or state values.

Sending, allowed channels and ticket state changes are controlled by Python.
If drafting fails validation, Python uses an approved fixed template.
