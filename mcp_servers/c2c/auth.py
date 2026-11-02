# Create C2C HTTP clients with OAuth or the configured temporary dummy authentication mode.
import os
import threading
import time

import httpx
from dotenv import load_dotenv

load_dotenv()

C2C_URL = os.getenv("C2C_INSTANCE_URL", "").rstrip("/")
C2C_CLIENT_ID = os.getenv("C2C_CLIENT_ID", "")
C2C_CLIENT_SECRET = os.getenv("C2C_CLIENT_SECRET", "")

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

        with httpx.Client(base_url=C2C_URL, timeout=30.0) as token_client:
            response = token_client.post(
                "/oauth/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": C2C_CLIENT_ID,
                    "client_secret": C2C_CLIENT_SECRET,
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                },
            )
            response.raise_for_status()
            token_data = response.json()

        access_token = token_data.get("access_token")
        if not access_token:
            raise RuntimeError("C2C OAuth response did not include an access_token")

        _token = access_token
        expires_in = int(token_data.get("expires_in", 0))
        _token_expires_at = time.monotonic() + max(expires_in - 60, 0)
        return _token


# Create the service HTTP client with the configured base URL and authentication headers.
def create_client() -> httpx.Client:
    # Temporary dummy-server fallback. Set C2C_AUTH_MODE=oauth to restore OAuth.
    if os.getenv("C2C_AUTH_MODE", "oauth").lower() == "none":
        if not C2C_URL:
            raise RuntimeError("Missing required C2C configuration: C2C_INSTANCE_URL")
        return httpx.Client(base_url=C2C_URL, headers={"Accept": "application/json"}, timeout=30.0)

    missing = [
        name
        for name, value in (
            ("C2C_INSTANCE_URL", C2C_URL),
            ("C2C_CLIENT_ID", C2C_CLIENT_ID),
            ("C2C_CLIENT_SECRET", C2C_CLIENT_SECRET),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(f"Missing required C2C configuration: {', '.join(missing)}")

    return httpx.Client(
        base_url=C2C_URL,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {_access_token()}",
        },
        timeout=30.0,
    )
