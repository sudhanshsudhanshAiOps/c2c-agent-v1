---
name: c2c-completion
description: Diagnose C2C progression, sign-off, quiz, completion history, or retraining incidents after triage classifies Course Completion Issue.
---

# Course Completion Issue

Use this category skill with the shared [C2C diagnosis guidance](../c2c-diagnosis/SKILL.md).
Triage owns caller verification, screenshots and initial classification. Consume
its verified identity and evidence; the orchestrator owns routing. Request retriage
if the evidence contradicts the existing category rather than silently changing it.

Source references: [category SOP](../../C2C_Classifier_Skill.md) and [classifier labels](../../C2C_Classifier_Skill.md).

## Subissue labels

* `Course Completion Issue  - Additional information or issue not found and closed after three strikes`
* `Course Completion Issue  - Agree button not visible to the user.`
* `Course Completion Issue  - Temporary issue with browser/network`
* `Course Completion Issue  - User Completed the course, but not moved to learning history(screenshot/duration)`
* `Course Completion Issue  - User has not completed all the slides`
* `Course Completion Issue  - User need to take the retraining course every year.`
* `Course Completion Issue  - User self resolved. No actions taken`
* `Course Completion Issue  - User unable to complete the course or completed before admin intervention`
* `Course Completion Issue  - User was able to see the course in Learning History and got auto resolved before admin intervention`

## Shared rules

Use Triage's verified learner identity and evidence; reuse classification unless retriage is needed. The orchestrator owns routing and Communication owns incident updates. Do not remediate, unlock, change configuration, grant credit, send messages, or close tickets. Resolution steps below are recommendations for the responsible human or future agent.

Use only registered tools and documented response fields/enums. Scope every read to the verified student and affected course/curriculum. A successful HTTP response or a nonempty list is not confirmation. Absence requires a successful, complete, correctly scoped query; failed, partial or unsupported reads cannot establish absence. Treat OCR/user reports as symptoms and returned diagnosis/resolution text as unverified suggestions. Missing essential fields, external checks or conflicting evidence require needs_more_evidence or needs_human_review. Cite current observed fact IDs for every supported/not_supported verdict; previous findings are leads, not fresh facts. Keep raw ticket/OCR/API evidence in memory, and checkpoint IDs, decisions and references only.

Select a candidate from the index and use load_scenario_skill before investigating it. Load other candidates when evidence changes. Preserve the loaded checks and interpretation rules in context. Missing information never establishes three strikes; no-response labels are not diagnosed causes. Historical self-resolution requires explicit user confirmation and incident history. All model turns, including SOP requests, retries and finalization, count toward DIAGNOSIS_MAX_ITERATIONS.

## Scenario index

- CC001 | Agree/Disagree absent or greyed out
- CC002 | Verify Course Completion required
- CC003 | Quiz passed but history not posted
- CC004 | Network/browser timeout during completion
- CC005 | Assessment passed yet course incomplete
- CC006 | Completion recorded but not visible to user
- CC007 | Unable to proceed to next slide
- CC008 | Unable to pass quiz
- CC009 | Training content not fully reviewed
- CC010 | Annual retraining appears again
- CC011 | User reports issue self-resolved
- CC012 | No response or missing completion information

## Scenarios

### CC001 | Agree/Disagree absent or greyed out

Checks: screenshot/user evidence for the document and learning-plan tabs, and item completion settings. The document may open in another tab; Agree/Disagree may remain on the learning-plan tab. No dedicated Agree-button endpoint exists.
Interpretation: verify whether the control is hidden by tab context versus disabled by unmet requirements. Missing visibility evidence remains unconfirmed.
Next: recommend switching tabs/Alt+Tab, selecting Agree when available, then Verify Course Completion if completion does not post. Never claim the user has done so without evidence.

### CC002 | Verify Course Completion required

Checks: document content and completion settings, screenshot showing the affected course/controls, and scoped learning history. Distinguish a visible Verify Course Completion control from evidence that the user clicked it or completed requirements.
Interpretation: the visible control supports a next-step hypothesis, not recorded completion. A course screenshot is not completion proof by itself.
Next: recommend completing required content, selecting Agree as applicable, then Verify Course Completion. Recheck history after user confirmation; do not grant credit.

### CC003 | Quiz passed but history not posted

Checks: affected course, quiz pass/completion evidence with date, item settings including whether history is added after all content completes, and correctly scoped Learning History.
Interpretation: passed quiz alone may not satisfy all content requirements. Establish actual completion and missing history using complete successful reads, not HTTP failures or partial lists.
Next: request completion_proof or api_fields as needed; recommend authorized completion/history review. Manual completion entries or scheduled jobs are prohibited here.

### CC004 | Network/browser timeout during completion

Checks: screenshot or completion proof, item access/completion evidence and recorded Learning History. Browser/network conditions require independent user/approved evidence.
Interpretation: a timeout alone does not prove lost completion. If verified completion exists but history is absent in a complete scoped read, consider the not-moved-to-history label; otherwise keep missing evidence explicit.
Next: recommend continuing content, refreshing/relogging and checking completed items as appropriate. No manual credit; authorized review is required for history changes.

### CC005 | Assessment passed yet course incomplete

Checks: exact assessment/course identity, pass result/date, all required content and item completion settings. Compare learning-plan and transcript records.
Interpretation: an assessment pass does not establish that every completion requirement is met. Missing required-content evidence remains unconfirmed; do not invent a dedicated assessment-progress endpoint.
Next: recommend completing remaining requirements or authorized review of inconsistent settings/history. Do not disclose quiz answers or change completion status.

### CC006 | Completion recorded but not visible to user

Checks: Learning History record for the verified learner/course plus current user-visible screenshot/confirmation and incident timeline.
Interpretation: COMPLETE proves recorded completion only. It does not prove user visibility, disappearance of the reported failure, or auto-resolution before intervention. If failure is still reported and no user confirmation exists, use needs_more_evidence with incident_history and subcategory null, or conflicting_evidence/human review. Auto-resolved labels require explicit timeline evidence.
Next: recommend checking Learning History/completed items and obtaining confirmation; no credit changes.

### CC007 | Unable to proceed to next slide

Checks: affected course, screenshot/approved progress evidence, required tabs/icons and content items, and relevant item settings. There is no dedicated slide-progress API.
Interpretation: determine whether unvisited content blocks progression; a stuck slide alone does not prove which requirement is missing. Report required evidence when it cannot be observed.
Next: recommend visiting every required tab/icon and completing required content. If it persists, request authorized content review; never bypass progression or grant credit.

### CC008 | Unable to pass quiz

Checks: affected course/assessment, actual user-reported question wording or attempt/lock evidence, and available item settings. Missing fields cannot be invented.
Interpretation: distinguish misunderstood instructions, unmet content requirements and a documented attempt lock. A lock/reset requires actual evidence and authorized handling.
Next: explain question wording only; select all may require multiple choices. Never reveal correct answers, reset attempts or mark completion. Recommend the authorized owner for a documented content/assessment fault.

### CC009 | Training content not fully reviewed

Checks: required content/items and screenshot or other approved progress evidence. Compare completion settings and recorded history; no dedicated detailed content-progress endpoint is available.
Interpretation: incomplete review requires actual missing-content evidence, not just absent history. Failed or partial API reads cannot establish that the learner skipped content.
Next: recommend reviewing every tab/icon/required item and checking completion afterward. Request completion_proof when essential; manual credit is not permitted.

### CC010 | Annual retraining appears again

Checks: recorded completion, assignment/retraining cycle and Retrain By Date using documented learner/item/history fields.
Interpretation: a future Retrain By Date with an annual cycle can be expected behavior. Reassignment alone is not a defect; missing cycle/date fields remain unconfirmed.
Next: explain the verified annual retraining requirement and relevant due date. Do not remove assignment or change the cycle.

### CC011 | User reports issue self-resolved

Checks: explicit user confirmation and incident timeline showing the reported issue stopped without intervention; compare current correctly scoped history where relevant.
Interpretation: COMPLETE alone is not proof of self-resolution. Report incident_history or conflicting_evidence when the ticket still reports failure. Use a self-resolved/auto-resolved operational label only with the required confirmation and timing.
Next: recommend review/verification; Diagnosis does not close or update the incident.

### CC012 | No response or missing completion information

Checks: identify the actual information still missing, distinguishing a readable course screenshot from course identity or completion proof. Source SOP follow-up history requires explicit incident evidence.
Interpretation: missing evidence is not a root cause and never establishes three strikes. Leave the closure subcategory null; no custom follow-up/closure process is implemented.
Next: return the precise user request to the orchestrator for Communication. Do not schedule reminders, send email/Teams messages or close the incident.
