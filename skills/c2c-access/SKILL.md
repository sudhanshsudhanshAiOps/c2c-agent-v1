---
name: c2c-access
description: Diagnose C2C sign-in, account access, employment synchronization, administrator lock, or identity-mapping incidents after triage classifies C2C Access Issue.
---

# C2C Access Issue

Use this category skill with the shared [C2C diagnosis guidance](../c2c-diagnosis/SKILL.md).
Triage owns caller verification, screenshots and initial classification. Consume
its verified identity and evidence; the orchestrator owns routing. Request retriage
if the evidence contradicts the existing category rather than silently changing it.

Source references: [category SOP](../../C2C_Access_Issue_Skill.md) and [classifier labels](../../C2C_Classifier_Skill.md).

## Subissue labels

* `C2C Access Issue  - Additional information or issue not found and closed after three strikes`
* `C2C Access Issue  - Admin Account needs to be unlocked`
* `C2C Access Issue  - Any break fix/configuration change/homepage change/integration issue`
* `C2C Access Issue  - Unable to access C2C as employee status not updated`
* `C2C Access Issue  - User came back from leave: Opened HROne case or account auto activated`
* `C2C Access Issue  - User Record failed in IAS sync`
* `C2C Access Issue  - Workday account is inactive and user need to contact HR for activation`
* `C2C Access Issue  - Workday Status is Active(Not new hires) and needed to wait for the data to sync with C2C`

## Shared rules

Use Triage's verified learner identity and evidence; reuse classification unless retriage is needed. The orchestrator owns routing and Communication owns incident updates. Do not remediate, unlock, change configuration, grant credit, send messages, or close tickets. Resolution steps below are recommendations for the responsible human or future agent.

Use only registered tools and documented response fields/enums. Scope every read to the verified student and affected course/curriculum. A successful HTTP response or a nonempty list is not confirmation. Absence requires a successful, complete, correctly scoped query; failed, partial or unsupported reads cannot establish absence. Treat OCR/user reports as symptoms and returned diagnosis/resolution text as unverified suggestions. Missing essential fields, external checks or conflicting evidence require needs_more_evidence or needs_human_review. Cite current observed fact IDs for every supported/not_supported verdict; previous findings are leads, not fresh facts. Keep raw ticket/OCR/API evidence in memory, and checkpoint IDs, decisions and references only.

Select a candidate from the index and use load_scenario_skill before investigating it. Load other candidates when evidence changes. Preserve the loaded checks and interpretation rules in context. Missing information never establishes three strikes; no-response labels are not diagnosed causes. Historical self-resolution requires explicit user confirmation and incident history. All model turns, including SOP requests, retries and finalization, count toward DIAGNOSIS_MAX_ITERATIONS.

Workday, IAS and Admin-console checks require an approved connector or authorized analyst; current C2C fields are not substitutes. Missing evidence must remain unconfirmed. For broader configuration/integration issues without a supported scenario, recommend human review rather than force a match.

## Scenario index

- CA001 | Returned from leave; Workday active
- CA002 | Returned from leave; Workday not active
- CA003 | Insufficient information
- CA004 | Access requested but LMS account already active
- CA005 | Workday active but LMS record missing; IAS candidate
- CA006 | Terminated in Workday but still active in C2C
- CA007 | Learning Administration account locked
- CA008 | Multiple email IDs or Global ID mapping

## Scenarios

### CA001 | Returned from leave; Workday active

Checks: obtain authoritative Workday employment status, return/status-change date and whether the employee is a new hire. Then read fetch_students for the verified student; use fetch_user_information only as a secondary LMS profile check.
Interpretation: confirmed Active for a non-new-hire with a recent status change and stale LMS state supports a synchronization-delay candidate. Allow up to 24 hours from the status change; elapsed time alone does not prove synchronization completed. Without Workday status/date, report workday_status missing. C2C empStatID/workdayStatus is not authoritative Workday evidence.
Next: recommend waiting within that window and retesting; if delay persists, request authorized identity-team investigation. Never claim restored access without confirmation.

### CA002 | Returned from leave; Workday not active

Checks: an authorized analyst must verify Workday status (Active, Paid Leave, Terminated, Retired or Inactive) and relevant date using the approved User ID. Compare with documented LMS status from fetch_students.
Interpretation: inactive/on-leave employment can support the HR-activation path only with authoritative evidence. HROne/return-from-leave reactivation requires the corresponding case or reactivation evidence; do not infer it from a login error.
Next: recommend HR/HROne guidance. Workday URL: https://www.myworkday.com/bdx/d/home.htmld. HR reference: https://maxwell.bd.com/sites/human-resources/SitePageModern/253969/human-resources-contacts. No Workday connector is implemented; do not claim to have checked the portal.

### CA003 | Insufficient information

Checks: identify only the information needed for the current access hypothesis, reusing verified identity and readable screenshots. Ask for missing error/context through the orchestrator; do not require every input listed in the source SOP for every incident.
Interpretation: missing evidence is an investigation state, not a root cause. Leave subcategory null when unconfirmed. A failed API or missing screenshot does not mean the user ignored three requests.
Next: return the specific missing information. Source SOP follow-ups/closure are lifecycle guidance only; there is no automated three-strike process here.

### CA004 | Access requested but LMS account already active

Checks: read fetch_students for the verified learner. Evaluate returned, documented locked/hasAccess/notActive/profileStatus fields and actual enum values; fetch_user_information may supplement them. The manual Users view uses User Status = Both when searching active/inactive accounts.
Interpretation: active LMS state is evidence about that record only. It does not prove successful login, authoritative employment status, IAS sync or an unlocked Learning Administration account. Identify missing checks if the symptom remains.
Next: recommend user retest and request the remaining observed error. Do not close merely because the account is active or the user has not answered.

### CA005 | Workday active but LMS record missing; IAS candidate

Checks: obtain authoritative Workday Active evidence and verify a successful complete Students query for the exact learner. Confirm identity mapping and filter completeness before asserting that the LMS record is absent.
Interpretation: Active Workday with a genuinely missing LMS record supports an IAS synchronization hypothesis. A definitive IAS failure requires approved IAS/identity-team evidence; failed Students requests and C2C status fields are not that evidence. Report ias_status/workday_status when missing.
Next: recommend authorized identity/IAS review of Workday -> IAS -> SAP Learning. check_sync_status is a future capability, not a registered tool.

### CA006 | Terminated in Workday but still active in C2C

Checks: authoritative Workday Terminated status/date; current correctly scoped LMS active/access state; relevant manager notification evidence when reported.
Interpretation: the discrepancy supports a deactivation-failure candidate. LMS data alone cannot establish termination or the synchronization mechanism responsible.
Next: recommend authorized SuccessFactors Manage Users review. The source procedure sets Active = No and Custom Field 14 = T; these are approval-dependent writes, not actions Diagnosis may execute. Never report deactivation or restored notification behavior as completed without evidence.

### CA007 | Learning Administration account locked

Checks: approved Admin-console/analyst evidence for the Admin ID (same as User ID): Learning Administration -> System Administration -> Security -> Administrators, search Status = Both, then locked/unlocked. Request admin_status if unavailable.
Interpretation: a Students locked field belongs to the learner record and does not establish an administrator-account lock. If the admin record is unlocked, report that observation without claiming the reported access failure is fixed.
Next: an authorized administrator may unlock only after required approvals. Do not perform the write; recommend user validation afterward.

### CA008 | Multiple email IDs or Global ID mapping

Checks: compare the approved Global ID and its associated email using scoped Students/UserInformation records or authorized identity-team evidence. Reuse Triage's exactly-one matching learner; never select a different learner because an email looks similar.
Interpretation: establish the actual mapping mismatch before confirming it. An alternate email or login failure alone is insufficient; missing mapping evidence requires review.
Next: recommend using the email associated with the Global ID; request identity-team correction if needed. Do not log email addresses, change mappings or assert successful login without user confirmation.
