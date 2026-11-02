# Readable console output and append-only, incident-scoped diagnostic logs.
"""Readable console output and append-only, incident-scoped diagnostic logs."""
from contextlib import contextmanager
from contextvars import ContextVar
from copy import copy
import logging
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

current_incident = ContextVar("log_incident", default=None)
current_agent = ContextVar("log_agent", default="Workflow")
NETWORK_LOGGERS = ("httpx", "httpcore", "urllib3", "openai", "uvicorn.access", "mcp")


# Set the incident logging context and restore the previous context on exit.
@contextmanager
def incident_scope(number):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", number):
        raise ValueError("Invalid incident number for logging")
    token = current_incident.set(number)
    try:
        yield
    finally:
        current_incident.reset(token)


class ConsoleFilter(logging.Filter):
    # Exclude transport noise and token-usage details from the console.
    def filter(self, record):
        return not record.name.startswith(NETWORK_LOGGERS) and "Model usage:" not in str(record.msg)


class IncidentLogHandler(logging.Handler):
    # Initialize IncidentLogHandler with its dependencies and configuration.
    def __init__(self, directory):
        super().__init__()
        self.directory = Path(directory)

    # Append a sanitized log record to the current incident file without saving transport payloads.
    def emit(self, record):
        number = current_incident.get()
        if not number:
            return
        try:
            safe = copy(record)
            # httpx INFO includes the URL: omit credentials and query values.
            if record.name.startswith("httpx"):
                if not record.msg.startswith("HTTP Request:") or len(record.args) != 5:
                    return
                method, url, version, status, reason = record.args
                parsed = urlsplit(str(url))
                safe.msg = "API call: %s %s://%s%s -> %s"
                safe.args = (method, parsed.scheme, parsed.netloc.rsplit("@", 1)[-1], parsed.path, status)
            elif record.name.startswith(("httpcore", "urllib3", "openai", "uvicorn.access", "mcp")):
                return  # Internal transport traces can contain headers or bodies.
            self.directory.mkdir(parents=True, exist_ok=True)
            with (self.directory / f"{number}_log.txt").open("a", encoding="utf-8") as stream:
                stream.write(self.format(safe) + "\n")
        except Exception:
            self.handleError(record)


# Install readable console output and sanitized per-incident file logging.
def configure_logging(*, directory=None, stream=None):
    root = logging.getLogger()
    if directory is None and any(isinstance(h, IncidentLogHandler) for h in root.handlers):
        return
    directory = directory or Path(__file__).resolve().parents[1] / "logs" / "incidents"
    console = logging.StreamHandler(stream if stream is not None else sys.stdout)
    console.addFilter(ConsoleFilter())
    console.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"))
    incident_file = IncidentLogHandler(directory)
    incident_file.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] [%(name)s] %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[console, incident_file], force=True)
    logging.getLogger("httpx").setLevel(logging.INFO)
    for name in ("httpcore", "urllib3", "openai"):
        logging.getLogger(name).setLevel(logging.WARNING)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True

