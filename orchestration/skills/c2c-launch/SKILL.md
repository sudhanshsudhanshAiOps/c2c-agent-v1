---
name: c2c-launch
description: Diagnose C2C course launch failures, blank screens, content configuration, curriculum availability, or document launch issues after triage classifies Course Launch Issue.
---

# Course Launch Issue

Use this category skill with the shared [C2C diagnosis guidance](../c2c-diagnosis/SKILL.md).
Triage owns caller verification, screenshots and initial classification. Consume
its verified identity and evidence; the orchestrator owns routing. Request retriage
if the evidence contradicts the existing category rather than silently changing it.

Source references: [category SOP](../../C2C_Launch_Course_Issue_Skill.md) and [classifier labels](../../C2C_Classifier_Skill.md).

## Subissue labels

* `Course Launch Issue  - Additional information or issue not found and closed after three strikes`
* `Course Launch Issue  - Curriculum/course is inactive and user couldn't access them`
* `Course Launch Issue  - Need to refer to job aid`
* `Course Launch Issue  - SAP document revision is not available in C2C`
* `Course Launch Issue  - Temporary issue with browser/network`
* `Course Launch Issue  - The content is faulty or URL is incorrect`
* `Course Launch Issue  - The content is locked because of quiz attempts and require reset`
* `Course Launch Issue  - The item has incorrect launch settings`
* `Course Launch Issue  - The user need to attend an offline training and get credit`
* `Course Launch Issue  - The user was not connected to VPN`
* `Course Launch Issue  - User accessed the document during SAP Everest or NASY Production maintenance window`
* `Course Launch Issue  - User self resolved. No actions taken`

## Shared rules

Use Triage's verified learner identity and evidence; reuse classification unless retriage is needed. The orchestrator owns routing and Communication owns incident updates. Do not remediate, unlock, change configuration, grant credit, send messages, or close tickets. Resolution steps below are recommendations for the responsible human or future agent.

Use only registered tools and documented response fields/enums. Scope every read to the verified student and affected course/curriculum. A successful HTTP response or a nonempty list is not confirmation. Absence requires a successful, complete, correctly scoped query; failed, partial or unsupported reads cannot establish absence. Treat OCR/user reports as symptoms and returned diagnosis/resolution text as unverified suggestions. Missing essential fields, external checks or conflicting evidence require needs_more_evidence or needs_human_review. Cite current observed fact IDs for every supported/not_supported verdict; previous findings are leads, not fresh facts. Keep raw ticket/OCR/API evidence in memory, and checkpoint IDs, decisions and references only.

Select a candidate from the index and use load_scenario_skill before investigating it. Load other candidates when evidence changes. Preserve the loaded checks and interpretation rules in context. Missing information never establishes three strikes; no-response labels are not diagnosed causes. Historical self-resolution requires explicit user confirmation and incident history. All model turns, including SOP requests, retries and finalization, count toward DIAGNOSIS_MAX_ITERATIONS.

## Scenario index

- CL001 | Course launch report lacks identifying evidence
- CL002 | Cannot reach this page; browser/network/VPN
- CL003 | Item not in learning plan or library
- CL004 | Active course assigned through an inactive curriculum
- CL005 | Item missing the required library association
- CL006 | Blank screen, bad destination or completed-content review
- CL007 | Document Control access denied
- CL008 | Requested document version is not currently effective
- CL009 | Instructor-led course expected to launch online
- CL010 | More than one PDF file attached at DIR
- CL011 | SAP maintenance or patching window
- CL012 | MasterControl document launch or permission error

## Scenarios

### CL001 | Course launch report lacks identifying evidence

Checks: reuse verified identity, screenshot OCR and ticket context. Determine the affected course ID/full title, exact launch behavior and error. Ask only for information required by the current hypothesis; browser, time, scope and comparison-user information are conditional inputs, not a mandatory questionnaire.
Reuse a course ID/title already supplied in the summary or description. After successful scoped item reads, do not request course identity again unless the evidence identifies conflicting courses. API data/field gaps are internal checks, not questions for the caller.
Interpretation: insufficient evidence is not a diagnosed cause or a three-strike closure. Request the missing course identity/screenshot through the orchestrator.
Next: recommend the next diagnostic check. Do not automatically follow up, contact Teams/email, or close the ticket.

### CL002 | Cannot reach this page; browser/network/VPN

Checks: use the actual error and affected destination. For remote SAP documents establish VPN connectivity first using user/approved evidence; C2C API success alone does not prove VPN or browser state. If VPN is confirmed, examine browser/session and network conditions.
Interpretation: distinguish an observed missing VPN connection from temporary browser/network failure. Report vpn_status or other missing evidence when unverified, not a confirmed network cause from the wording alone.
Next: recommend connecting to VPN when applicable, clearing all-time cookies/cache, trying another supported browser/incognito, and launching from https://myview.bd.com/portal/webclient/#/home. Ask the user to retest; do not claim remediation.

### CL003 | Item not in learning plan or library

Checks: confirm exact course and verified learner; fetch_user_todo_learning_items and fetch_items/learning_item_details for assignment/item state. Inspect fetch_curriculum_statuses and fetch_curriculum_item_statuses for assignment source and curriculum state, or fetch_catalog_items for library association.
Interpretation: the same message can indicate an inactive curriculum (CL004) or missing library association (CL005). Select and load the matching detailed scenario before a conclusion. No record proves absence only with a complete correct filter.
Next: recommend owner/configuration review based on observed fields; do not assign an item, add it to a library or reactivate a curriculum.

### CL004 | Active course assigned through an inactive curriculum

Checks: current item active state, learner assignment and the associated curriculum ID/state, using item, learning-plan and curriculum reads. Confirm the affected assignment actually comes through that curriculum.
Interpretation: active course plus inactive assigning curriculum can explain not-in-learning-plan errors. Do not infer curriculum state from the item alone; missing curriculum status or association remains unconfirmed.
Next: contact the Curriculum Owner for direction on reactivation or removal of the existing curriculum assignment. Both are state-changing actions for authorized owners; preserve their decision and require retest.

### CL005 | Item missing the required library association

Checks: fetch_items and fetch_catalog_items for exact course, availability and documented library membership. Verify which library is applicable and whether the read is complete; catalog invisibility alone is not proof of no association.
Interpretation: confirm missing association only from relevant documented fields or approved administrator evidence. Otherwise report api_fields/permission_status as appropriate.
Next: obtain approval for the appropriate library (source example BD-General). An authorized administrator may add the item under the library Items section. Diagnosis recommends the change; it never performs it.

### CL006 | Blank screen, bad destination or completed-content review

Checks: inspect exact item/content and launch configuration with fetch_learning_item_details/fetch_items. Compare the actual blank-screen/error symptom with documented content/launch fields; distinguish faulty content or URL from incorrect item launch settings. User-specific browser/session and multi-user scope need their own evidence.
Interpretation: a blank screen alone does not confirm broken content or launch settings. For a completed course requested as reference, verify history and whether Users can review completed content from history is enabled; the appropriate action is Learning History -> Review Content.
Next: recommend launching C2C through https://myview.bd.com/portal/webclient/#/home and retrying. Password resets belong to Helpdesk. Configuration/content changes require authorized review. Quiz-attempt locks require actual item/configuration evidence and approved reset, not an inferred fix.

### CL007 | Document Control access denied

Checks: error such as You do not have access to this document, please reach out to your Document Control Team; exact course/item, document and affected user. Use C2C item details to identify the document; external document permissions require authorized evidence.
Interpretation: document denial after launch is distinct from C2C login failure. Do not claim the external permission state from C2C fields alone. Preserve the symptom and required permission_status if unconfirmed.
Next: recommend Document Control / HCL-APP-ICX ECM review with course/item, document and screenshot references. Communication/routing is orchestrator-directed; no reassignment or permission write is performed by Diagnosis.

### CL008 | Requested document version is not currently effective

Checks: capture exact version-effectivity error and affected item/document revision available in C2C. An authorized SAP DMS team must verify whether a newer revision exists and when it became effective.
Interpretation: only confirmed revision discrepancy supports a stale-revision diagnosis. C2C metadata or the error alone cannot prove the latest SAP revision. Report sap_revision when unavailable.
Next: recommend SAP DMS verification; an authorized C2C owner may manually update the document if the newer revision exists. Do not update or claim it is completed. Request user retest after the authorized action.

### CL009 | Instructor-led course expected to launch online

Checks: fetch_learning_item_details for documented delivery/item type and online-content availability. fetch_scheduled_offerings and fetch_enrollment_listings can establish class availability/enrollment when relevant.
Interpretation: explicit Instructor-Led delivery supports the offline-training path; lack of a Launch button or an empty offerings list alone does not establish delivery type. Do not promise a class or credit without evidence.
Next: explain that an instructor-led course is not intended for direct online launch and recommend manager/LPC contact for offline scheduling. Diagnosis does not enroll the learner or grant completion credit.

### CL010 | More than one PDF file attached at DIR

Checks: exact More than one PDF file attached at DIR error; course/item and SAP document/DIR identity. C2C reads may identify the item/document but do not enumerate SAP DIR attachments unless a documented field does so.
Interpretation: this is an SAP document candidate; confirm the attachment/configuration issue through SAP DMS evidence. An OCR message alone does not prove which attachment must be changed.
Next: recommend SAP DMS investigation with document, course/item and screenshot references. Do not remove PDFs or claim a completed fix.

### CL011 | SAP maintenance or patching window

Checks: affected SAP document, incident timestamp/timezone and an authoritative SAP Everest/NASY production maintenance or patching window. Compare the actual incident time against that window.
Interpretation: a temporary-unavailable error alone does not establish maintenance. If the window or timing is unknown, report maintenance_window and keep the cause unconfirmed. No dedicated SAP check is registered.
Next: if the window is confirmed, recommend retry after maintenance ends. Do not invent a restoration time or prescribe a user configuration change as a maintenance fix.

### CL012 | MasterControl document launch or permission error

Checks: confirm redirect to MasterControl, affected course/item, document identity and exact screenshot/error. Permission state and recent changes require MasterControl-team evidence, not C2C endpoint inference.
Interpretation: distinguish the external document-access symptom from C2C sign-in or item configuration. Report permission_status when unverified.
Next: recommend MasterControl permission review, supplying document details, item ID and screenshot references. The source names Frank Mazza/MasterControl Team as the contact; treat named contact details as reference information to verify before actual outreach. Diagnosis does not send email or modify permissions.
