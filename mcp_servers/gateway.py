# Common MCP response envelope and incident-scoped server logging.
"""Common MCP response envelope and incident-scoped server logging."""
from contextlib import nullcontext
import sys

import httpx

from runtime import configure_logging, incident_scope


# Configure MCP process logging without writing transport noise to standard output.
def configure_gateway_logging():
    # stdout is reserved for MCP protocol messages.
    configure_logging(stream=sys.stderr)


# Run a backend operation in incident log scope and return a sanitized MCP result or error.
def run_gateway(function, arguments, incident_number=None):
    scope = incident_scope(incident_number) if incident_number else nullcontext()
    with scope:
        try:
            return {"result": function(**arguments)}
        except httpx.HTTPStatusError as error:
            try:
                body = error.response.json()
            except ValueError:
                body = None
            return {"error": "HTTPStatusError", "http_status": error.response.status_code, "body": body}
        except Exception as error:
            # Do not transmit exception strings that might contain credentials or payloads.
            return {"error": type(error).__name__}
