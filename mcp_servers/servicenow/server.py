# Explicit ServiceNow MCP tools; client.py performs the HTTP API calls.
"""Explicit ServiceNow MCP tools; client.py performs the HTTP API calls."""
from mcp.server import MCPServer
from mcp_servers import servicenow as sn
from mcp_servers.gateway import configure_gateway_logging, run_gateway
from tools import read_incident_screenshots

mcp = MCPServer("servicenow")


# GET /api/now/table/incident/{sys_id}, including journals when requested.
@mcp.tool(name="fetch_incident")
def get_incident(sys_id: str, display_value: bool = False, include_journal: bool = True,
                 incident_number: str | None = None) -> dict:
    """GET /api/now/table/incident/{sys_id}, including journals when requested."""
    return run_gateway(sn.fetch_incident_by_sys_id, {
        "sys_id": sys_id, "display_value": display_value, "include_journal": include_journal,
    }, incident_number)


# GET /api/now/table/sys_user/{sys_id}: read the approved identity field.
@mcp.tool(name="fetch_caller_global_id")
def get_caller_global_id(sys_id: str, incident_number: str | None = None) -> dict:
    """GET /api/now/table/sys_user/{sys_id}: read the approved identity field."""
    return run_gateway(sn.fetch_caller_global_id, {"sys_id": sys_id}, incident_number)


# GET /api/now/attachment: list image attachments for this incident.
@mcp.tool(name="list_screenshots")
def get_screenshots(incident_sys_id: str, incident_number: str | None = None) -> dict:
    """GET /api/now/attachment: list image attachments for this incident."""
    return run_gateway(sn.list_screenshots, {"incident_sys_id": incident_sys_id}, incident_number)


# GET /api/now/table/sys_journal_field: new comments from the verified caller.
@mcp.tool()
def fetch_caller_replies(incident_sys_id: str, caller_user_name: str, since: str,
                        incident_number: str | None = None) -> dict:
    """GET /api/now/table/sys_journal_field: new comments from the verified caller."""
    return run_gateway(sn.fetch_caller_replies, {
        'incident_sys_id': incident_sys_id, 'caller_user_name': caller_user_name, 'since': since,
    }, incident_number)


# GET /api/now/attachment/{attachment_id}/file, then extract screenshot text.
@mcp.tool(name="read_incident_screenshots")
def read_screenshot_text(incident_sys_id: str, incident_number: str | None = None) -> dict:
    """GET /api/now/attachment/{attachment_id}/file, then extract screenshot text."""
    return run_gateway(read_incident_screenshots, {"incident_sys_id": incident_sys_id}, incident_number)


# PUT /api/now/table/incident/{sys_id}: apply orchestrator-controlled fields.
@mcp.tool()
def update_incident(sys_id: str, fields: dict, incident_number: str | None = None) -> dict:
    """PUT /api/now/table/incident/{sys_id}: apply orchestrator-controlled fields."""
    return run_gateway(sn.update_incident, {"sys_id": sys_id, "fields": fields}, incident_number)


if __name__ == "__main__":
    configure_gateway_logging()
    mcp.run(transport="stdio")
