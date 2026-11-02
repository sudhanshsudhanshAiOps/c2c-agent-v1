# Create authenticated ServiceNow HTTP clients and cache OAuth tokens.
import os
import threading
import time

import httpx
from dotenv import load_dotenv

load_dotenv()

SN_URL = os.getenv("SN_INSTANCE_URL", "").rstrip("/")
SN_CLIENT_ID = os.getenv("SN_CLIENT_ID", "")
SN_CLIENT_SECRET = os.getenv("SN_CLIENT_SECRET", "")

_token = ""
_token_expires_at = 0.0
_token_lock = threading.Lock()


# Obtain or reuse a cached OAuth access token for this service.
def _access_token() -> str:
    global _token, _token_expires_at

    now = time.monotonic()
    if _token and now < _token_expires_at:
        return _token

    with _token_lock:
        now = time.monotonic()
        if _token and now < _token_expires_at:
            return _token

        with httpx.Client(base_url=SN_URL, timeout=30.0) as token_client:
            response = token_client.post(
                "/oauth_token.do",
                data={
                    "grant_type": "client_credentials",
                    "client_id": SN_CLIENT_ID,
                    "client_secret": SN_CLIENT_SECRET,
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json"
                },
            )
            response.raise_for_status()
            token_data = response.json()

        access_token = token_data.get("access_token")
        if not access_token:
            raise RuntimeError("ServiceNow OAuth response did not include an access_token")

        _token = access_token
        expires_in = int(token_data.get("expires_in", 0))
        _token_expires_at = time.monotonic() + max(expires_in - 60, 0)
        return _token


# Create the service HTTP client with the configured base URL and authentication headers.
def create_client() -> httpx.Client:
    missing = [
        name
        for name, value in (
            ("SN_INSTANCE_URL", SN_URL),
            ("SN_CLIENT_ID", SN_CLIENT_ID),
            ("SN_CLIENT_SECRET", SN_CLIENT_SECRET),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(f"Missing required ServiceNow configuration: {', '.join(missing)}")

    return httpx.Client(
        base_url=SN_URL,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {_access_token()}",
        },
        timeout=30.0,
    )