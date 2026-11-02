# Project preferences

- Keep terminal logs readable: show stage starts, triage identity/screenshot/category findings, diagnosis plans and candidate IDs, individual tool outcomes, and the next action. Use the existing Python logging setup.
- Do not log credentials or raw ticket/OCR/API payloads. Distinguish unverified candidates from confirmed causes.
- When asked to run the server visibly, use a visible terminal so the user can watch these logs.
- Keep diagnosis model turns bounded by DIAGNOSIS_MAX_ITERATIONS in .env, including retries and finalization. Do not add a hidden model call after that cap.
- Keep repeated model context compact without dropping SOP decision rules or tool schemas. Report input/output/cached/total token usage separately; do not describe the iteration cap as a hard total-token budget.
