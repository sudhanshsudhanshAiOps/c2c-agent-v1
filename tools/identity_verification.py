# Verify learner identity using the registered Students read tool.
"""Verify learner identity using the registered Students read tool."""


# Resolve exactly one matching dummy globalId without guessing a student.
async def resolve_c2c_student(global_id: str, *, execute_tool) -> dict:
    """Resolve exactly one matching dummy globalId without guessing a student."""
    # In the dummy system the ServiceNow global ID is the Students studentID.
    response = await execute_tool("fetch_students", {"query_params": {"studentID": global_id}})
    rows = response.get("value") if isinstance(response, dict) else None
    if not isinstance(rows, list):
        return {"status": "invalid_response"}
    if not rows:
        return {"status": "not_found"}
    matches = [row for row in rows if isinstance(row, dict)
               and row.get("globalId", row.get("studentID")) == global_id]
    if len(matches) > 1:
        return {"status": "ambiguous"}
    if not matches:
        return {"status": "identity_mismatch"}
    row = matches[0]
    # The dummy may return the shared ID under studentID rather than echo globalId.
    # Confirmed dummy-server convention: globalId is also the Learning studentID.
    student_id = row.get("studentID", global_id)
    if not isinstance(student_id, str) or not student_id.strip():
        return {"status": "student_id_missing"}
    return {"status": "matched", "studentID": student_id}

