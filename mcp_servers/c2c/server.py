# Explicit C2C MCP tools; client.py owns HTTP requests and endpoint paths.
"""Explicit C2C MCP tools; client.py owns HTTP requests and endpoint paths."""
from mcp.server import MCPServer
from mcp_servers import c2c
from mcp_servers.gateway import configure_gateway_logging, run_gateway

mcp = MCPServer("c2c")


# GET /learning/odatav4/searchStudent/v1/Students.
@mcp.tool(name="fetch_students")
def get_students(query_params: dict | None = None, incident_number: str | None = None) -> dict:
    """GET /learning/odatav4/searchStudent/v1/Students"""
    return run_gateway(c2c.fetch_students, {"query_params": query_params}, incident_number)


# GET /learning/odatav4/public/admin/user-service/v2/UserInformation.
@mcp.tool(name="fetch_user_information")
def get_user_information(query_params: dict | None = None, incident_number: str | None = None) -> dict:
    """GET /learning/odatav4/public/admin/user-service/v2/UserInformation"""
    return run_gateway(c2c.fetch_user_information, {"query_params": query_params}, incident_number)


# GET /learning/odatav4/public/user/learningPlan/v1/UserTodoLearningItems.
@mcp.tool(name="fetch_user_todo_learning_items")
def get_user_todo_learning_items(query_params: dict | None = None, incident_number: str | None = None) -> dict:
    """GET /learning/odatav4/public/user/learningPlan/v1/UserTodoLearningItems"""
    return run_gateway(c2c.fetch_user_todo_learning_items, {"query_params": query_params}, incident_number)


# GET /learning/odatav4/learningPlan/v1/LearningItemDetails.
@mcp.tool(name="fetch_learning_item_details")
def get_learning_item_details(query_params: dict | None = None, incident_number: str | None = None) -> dict:
    """GET /learning/odatav4/learningPlan/v1/LearningItemDetails"""
    return run_gateway(c2c.fetch_learning_item_details, {"query_params": query_params}, incident_number)


# GET /learning/odatav4/public/admin/searchItem/v1/Items.
@mcp.tool(name="fetch_items")
def search_items(query_params: dict | None = None, incident_number: str | None = None) -> dict:
    """GET /learning/odatav4/public/admin/searchItem/v1/Items"""
    return run_gateway(c2c.fetch_items, {"query_params": query_params}, incident_number)


# GET /learning/odatav4/catalogSearch/v1/CatalogItems.
@mcp.tool(name="fetch_catalog_items")
def search_catalog_items(query_params: dict | None = None, incident_number: str | None = None) -> dict:
    """GET /learning/odatav4/catalogSearch/v1/CatalogItems"""
    return run_gateway(c2c.fetch_catalog_items, {"query_params": query_params}, incident_number)


# GET /learning/odatav4/curriculum/v1/CurriculumStatuses.
@mcp.tool(name="fetch_curriculum_statuses")
def get_curriculum_statuses(query_params: dict | None = None, incident_number: str | None = None) -> dict:
    """GET /learning/odatav4/curriculum/v1/CurriculumStatuses"""
    return run_gateway(c2c.fetch_curriculum_statuses, {"query_params": query_params}, incident_number)


# GET /learning/odatav4/curriculum/v1/CurriculumItemStatuses.
@mcp.tool(name="fetch_curriculum_item_statuses")
def get_curriculum_item_statuses(query_params: dict | None = None, incident_number: str | None = None) -> dict:
    """GET /learning/odatav4/curriculum/v1/CurriculumItemStatuses"""
    return run_gateway(c2c.fetch_curriculum_item_statuses, {"query_params": query_params}, incident_number)


# GET /learning/odatav4/public/user/scheduledoffering-service/v1/ScheduledOfferings.
@mcp.tool(name="fetch_scheduled_offerings")
def get_scheduled_offerings(query_params: dict | None = None, incident_number: str | None = None) -> dict:
    """GET /learning/odatav4/public/user/scheduledoffering-service/v1/ScheduledOfferings"""
    return run_gateway(c2c.fetch_scheduled_offerings, {"query_params": query_params}, incident_number)


# GET /learning/odatav4/public/user/scheduledoffering-service/v1/EnrollmentListings.
@mcp.tool(name="fetch_enrollment_listings")
def get_enrollment_listings(query_params: dict | None = None, incident_number: str | None = None) -> dict:
    """GET /learning/odatav4/public/user/scheduledoffering-service/v1/EnrollmentListings"""
    return run_gateway(c2c.fetch_enrollment_listings, {"query_params": query_params}, incident_number)


# GET /learning/odatav4/public/user/learningHistory/v1/learninghistorys.
@mcp.tool(name="fetch_learning_history")
def get_learning_history(query_params: dict | None = None, incident_number: str | None = None) -> dict:
    """GET /learning/odatav4/public/user/learningHistory/v1/learninghistorys"""
    return run_gateway(c2c.fetch_learning_history, {"query_params": query_params}, incident_number)


# GET /learning/odatav4/searchCurriculum/v1/Curricula.
@mcp.tool(name="fetch_curricula")
def search_curricula(query_params: dict | None = None, incident_number: str | None = None) -> dict:
    """GET /learning/odatav4/searchCurriculum/v1/Curricula"""
    return run_gateway(c2c.fetch_curricula, {"query_params": query_params}, incident_number)


if __name__ == "__main__":
    configure_gateway_logging()
    mcp.run(transport="stdio")
