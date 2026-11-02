Diagnosis follows triage's caller verification, screenshot check and classification.
Triage shares current evidence in a per-run ContextVar; diagnosis does not refetch
it. Raw ticket, OCR, API records and model/tool message history are not checkpointed.

The diagnosis agent loads the category's Neo4j scenarios and a compact overview
of the matching c2c-access, c2c-launch or c2c-completion skill. Each existing skill
file has shared rules, an index and scenario sections. It runs a native loop:
model selects load_scenario_skill or a registered read -> runtime validates arguments -> tool executes ->
scoped observations return to the model -> model adjusts arguments, selects another
read, or calls finish_diagnosis. There is no API-ID dispatch table or regex-based
course-ID extraction. Actual query values must occur in ticket/OCR evidence or be
discovered in earlier tool results. Learner arguments must match the verified ID.

Tool registration, descriptions and JSON parameter schemas are in tools/registry.py. These
include required fields, supported alternate filters, value types and rejection of
unknown properties. All reads and model calls execute through AgentRunner and
ToolExecutor. Validation errors, HTTP failures and empty responses are observations
the model can use on its next turn. Identical calls reuse the existing observation
rather than reissuing a backend request. API payloads are reduced to bounded,
nonpersonal entity fields and diagnostic facts before model feedback.
In main.py, startup connects stdio sessions to the C2C and ServiceNow MCP servers.
External calls follow AgentRunner -> ToolExecutor -> MCP server -> HTTP client.
The servers own API authentication and ServiceNow OCR; tool results return to
the agent in memory. Incident numbers accompany calls for scoped file logging.
Startup checks advertised tool names and fails if a required gateway is absent;
there is no production fallback to direct HTTP calls. Tests may inject local
adapters or mocked sessions. Skills, LLM requests and validation remain local.
tools/skill_loader.py returns the overview through load_category_skill and one
detailed section through load_scenario_skill. The LLM supplies only scenario_id;
the agent binds the current issue_id and rejects candidates outside the current
KG category. Tool results retain selected SOP rules once in the native message
history; duplicate requests return already_loaded without repeating the text.
Supported/not_supported verdicts require that scenario's detailed SOP to be loaded.
Root SOP files remain reference sources and are not sent wholesale to the model.
The diagnosis agent calls next_diagnosis_action through AgentRunner, which invokes
DiagnosisAgent.next_action, which delegates to agents/diagnosis/llm_client.py.
That agent owns its cached client and model request logic. The shared registry
binds its callback without constructing a model client or moving its prompts.
Diagnosis schemas and validation live in agents/diagnosis/tool_schema.py and
validation.py. Triage follows Python rules and calls tools/classifier.py for
LLM-backed category classification. Communication drafts screenshot requests with
agents/communication/llm_client.py and skills/c2c-communication/SKILL.md. Python
validates channel fields and controls sending/state; messages.py provides a fixed
fallback. Generated message bodies are not stored in checkpoint state.
The registry exposes the 12 original C2C GET routes under /learning/odatav4/.
There are no custom account-status, launch-troubleshoot or completion-status
routes. Missing slide, Agree-button or external-system evidence stays missing;
C2C-reported employment status is not an authoritative Workday check.

.env setting:

    DIAGNOSIS_MAX_ITERATIONS=10

This is a positive-integer limit on total diagnosis model turns. Errors, retries,
prose-only answers, scenario-SOP requests and finish_diagnosis each consume a turn. Each model turn is
also capped at 1000 output tokens. At most one read executes per turn. There is
no extra interpretation/model call after the limit. Limit exhaustion returns
needs_more_evidence with stop_reason=iteration_limit; model failures stop with
model_unavailable. The cap limits work, not evidence requirements.

Token telemetry separates input, output, cached input and cumulative total. Total
includes repeated input on every request; it is not just generated output. Cached
input is a subset of input. The iteration/output caps are not a hard total-token
budget. Prompts use only the category SOP decision steps, a compact KG view and
concise schemas; full skill text and duplicate KG IDs stay outside model context.

finish_diagnosis includes per-scenario verdicts, exact SOP subissue label,
confidence and missing evidence. Supported/not_supported verdicts must cite actual
fact IDs. Missing authoritative Workday/IAS/SAP evidence remains missing. The
runtime validates final conclusions and persists fact references (check IDs and
paths), not raw values. Invalid final calls can be corrected within the remaining
iterations. The orchestrator still ends at review_diagnosis because resolution
is not built.

Triage maps ServiceNow user_name (or SN_CALLER_GLOBAL_ID_FIELD) -> dummy Students
lookup by studentID -> studentID. Exactly one match is required. The user confirmed that the
dummy globalId equals studentID, including responses that return only studentID.
Caller checks refresh each run; a completed classification is reused unless an
agent requests retriage. Diagnosis cannot replace identity from ticket text.

Before restarting a checkpointed workflow, an update guard compares hashes of
the current summary, description, caller ID and screenshot IDs/update metadata.
Unchanged completed diagnoses remain at review_diagnosis; unchanged screenshot
waits do not cause ticket writes. State, priority, comments and work-note edits
alone do not restart agents. Raw evidence is not stored in these hashes.
The authenticated webhook accepts rediagnose_requested=true to refresh a
diagnosis, or retriage_requested=true to classify again. Failed/partial runs
remain retryable. Older checkpoints without a baseline need one fresh run.

C2C_AUTH_MODE=none is the temporary dummy authentication setting. Set oauth or
remove it and restart main.py to restore OAuth. No automatic fallback follows an
OAuth failure.

Run unit tests: .venv\Scripts\python.exe -m unittest discover -s tests
Run synthetic checkpoint check: .venv\Scripts\python.exe scripts/check_checkpoint.py
Run visible dummy demo: .venv\Scripts\python.exe -u scripts/demo_diagnosis.py
The demo uses live LLM/KG/C2C reads and mocks ServiceNow writes.
