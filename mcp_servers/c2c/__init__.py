# C2C connector operations; MCP server registration is an explicit entry point.
"""C2C connector operations; MCP server registration is an explicit entry point."""
from .auth import C2C_URL, create_client
from .client import (
    fetch_catalog_items, fetch_curricula, fetch_curriculum_item_statuses,
    fetch_curriculum_statuses, fetch_enrollment_listings, fetch_items,
    fetch_learning_history, fetch_learning_item_details, fetch_scheduled_offerings,
    fetch_students, fetch_user_information, fetch_user_todo_learning_items,
)

__all__ = [
    "C2C_URL", "create_client", "fetch_catalog_items", "fetch_curricula",
    "fetch_curriculum_item_statuses", "fetch_curriculum_statuses",
    "fetch_enrollment_listings", "fetch_items", "fetch_learning_history",
    "fetch_learning_item_details", "fetch_scheduled_offerings", "fetch_students",
    "fetch_user_information", "fetch_user_todo_learning_items",
]
