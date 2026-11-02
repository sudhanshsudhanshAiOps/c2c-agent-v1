# Fetch incident screenshots and extract their text with Tesseract OCR.
import os
import shutil
import subprocess

from mcp_servers import servicenow


# Locate and validate the Tesseract executable used for screenshot OCR.
def _tesseract_command() -> str:
    command = os.getenv("TESSERACT_CMD") or shutil.which("tesseract")
    if not command and os.name == "nt":
        command = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if not command or not os.path.isfile(command):
        raise RuntimeError("Tesseract OCR is not installed or TESSERACT_CMD is invalid")
    return command


# Read one incident screenshot without saving the image to disk.
def read_screenshot(incident_sys_id: str, attachment_sys_id: str) -> dict:
    """Read one incident screenshot without saving the image to disk."""
    screenshot = servicenow.fetch_screenshot(incident_sys_id, attachment_sys_id)
    completed = subprocess.run(
        [_tesseract_command(), "stdin", "stdout", "-l", "eng"],
        input=screenshot["image"],
        capture_output=True,
        timeout=20,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError("Tesseract could not read the screenshot")

    text = completed.stdout.decode("utf-8", errors="replace").strip()[:4000]
    return {
        "attachment_sys_id": attachment_sys_id,
        "file_name": screenshot["file_name"],
        "status": "read" if text else "unreadable",
        "text": text,
    }


# OCR up to three image attachments on an incident.
def read_incident_screenshots(incident_sys_id: str) -> dict:
    """OCR up to three image attachments on an incident."""
    attachments = sorted(servicenow.list_screenshots(incident_sys_id),
                         key=lambda row: row.get('sys_created_on', ''), reverse=True)[:3]
    if not attachments:
        return {"status": "not_provided", "screenshots": []}

    results = []
    for attachment in attachments:
        try:
            results.append(read_screenshot(incident_sys_id, attachment["sys_id"]))
        except (RuntimeError, ValueError, subprocess.TimeoutExpired):
            results.append(
                {
                    "attachment_sys_id": attachment.get("sys_id"),
                    "file_name": attachment.get("file_name"),
                    "status": "unreadable",
                    "text": "",
                }
            )
        results[-1].update({key: attachment.get(key) for key in ('sys_created_on', 'sys_updated_on', 'size_bytes')})
    return {
        "status": "read" if any(item["status"] == "read" for item in results) else "unreadable",
        "screenshots": results,
    }
