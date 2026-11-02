# Implement the C2C Learning API reads used by the MCP server.
from . import create_client as _client


# Perform a C2C GET request and return its JSON body after checking HTTP status.
def _get(path: str, query_params: dict = None) -> dict:
    with _client() as client:
        response = client.get(path, params=query_params or {})
        response.raise_for_status()
        return response.json()


# Read learner records from the C2C Students endpoint using the supplied filters.
def fetch_students(query_params: dict = None) -> dict:
    return _get("/learning/odatav4/searchStudent/v1/Students", query_params)


# Read detailed LMS profile information for the specified learner.
def fetch_user_information(query_params: dict = None) -> dict:
    return _get(
        "/learning/odatav4/public/admin/user-service/v2/UserInformation",
        query_params,
    )


# Read the learner learning plan and assigned course items.
def fetch_user_todo_learning_items(query_params: dict = None) -> dict:
    return _get(
        "/learning/odatav4/public/user/learningPlan/v1/UserTodoLearningItems",
        query_params,
    )


# Read the affected course content, delivery and completion configuration.
def fetch_learning_item_details(query_params: dict = None) -> dict:
    return _get("/learning/odatav4/learningPlan/v1/LearningItemDetails", query_params)


# Search C2C learning items by the supplied item filters.
def fetch_items(query_params: dict = None) -> dict:
    return _get("/learning/odatav4/public/admin/searchItem/v1/Items", query_params)


# Read matching catalog items and their library visibility information.
def fetch_catalog_items(query_params: dict = None) -> dict:
    return _get("/learning/odatav4/catalogSearch/v1/CatalogItems", query_params)


# Read curriculum assignment statuses for the specified learner.
def fetch_curriculum_statuses(query_params: dict = None) -> dict:
    return _get("/learning/odatav4/curriculum/v1/CurriculumStatuses", query_params)


# Read the items and statuses within the specified curriculum.
def fetch_curriculum_item_statuses(query_params: dict = None) -> dict:
    return _get(
        "/learning/odatav4/curriculum/v1/CurriculumItemStatuses",
        query_params,
    )


# Read class sessions and scheduled offerings for the supplied course or schedule.
def fetch_scheduled_offerings(query_params: dict = None) -> dict:
    return _get(
        "/learning/odatav4/public/user/scheduledoffering-service/v1/ScheduledOfferings",
        query_params,
    )


# Read learner enrollment records using the supplied filters.
def fetch_enrollment_listings(query_params: dict = None) -> dict:
    return _get(
        "/learning/odatav4/public/user/scheduledoffering-service/v1/EnrollmentListings",
        query_params,
    )


# Read recorded learner completions, optionally restricted to a course component.
def fetch_learning_history(query_params: dict = None) -> dict:
    return _get(
        "/learning/odatav4/public/user/learningHistory/v1/learninghistorys",
        query_params,
    )


# Search curriculum configuration by identifier or title.
def fetch_curricula(query_params: dict = None) -> dict:
    return _get("/learning/odatav4/searchCurriculum/v1/Curricula", query_params)


