# Draft orchestrator-selected communication; never send or choose ticket state.
"""Draft orchestrator-selected communication; never send or choose ticket state."""
from functools import lru_cache
import json
import logging
import os

from openai import OpenAI

logger = logging.getLogger(__name__)


# Create and cache the configured LLM client for this module.
@lru_cache(maxsize=1)
def get_client():
    return OpenAI(base_url=os.getenv("LLM_MODEL_1_BASE_URL"),
                  api_key=os.getenv("LLM_MODEL_1_API_KEY", "not-required"),
                  timeout=30.0, max_retries=0)


# Ask the LLM to draft the selected message channels and record model token usage.
def compose_message(number, channels, rules, action='request_screenshot', request=None):
    response = get_client().chat.completions.create(
        model=os.getenv("LLM_MODEL_1"), temperature=0, max_tokens=512,
        response_format={"type": "json_object"}, reasoning_effort="none",
        messages=[{"role": "system", "content": rules}, {"role": "user", "content": json.dumps({
            "action": action, "incident_number": number, "channels": channels,
            "request": request,
        })}],
    )
    usage = response.usage
    logger.info("[%s] Model usage: input=%s output=%s cached_input=%s total=%s", number,
                getattr(usage, "prompt_tokens", 0) or 0, getattr(usage, "completion_tokens", 0) or 0,
                getattr(getattr(usage, "prompt_tokens_details", None), "cached_tokens", 0) or 0,
                getattr(usage, "total_tokens", 0) or 0)
    if response.choices[0].finish_reason != "stop":
        raise ValueError("Communication response was incomplete")
    return json.loads(response.choices[0].message.content)
