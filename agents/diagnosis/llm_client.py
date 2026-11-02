# Diagnosis model requests; invoked through AgentRunner and ToolExecutor.
"""Diagnosis model requests; invoked through AgentRunner and ToolExecutor."""
import os
from functools import lru_cache

from openai import OpenAI


# Create and cache the configured LLM client for this module.
@lru_cache(maxsize=1)
def get_client():
    return OpenAI(base_url=os.getenv("LLM_MODEL_1_BASE_URL"),
                  api_key=os.getenv("LLM_MODEL_1_API_KEY", "not-required"),
                  timeout=30.0, max_retries=0)


# Ask the LLM for the next native function call, via the registered runtime.
def next_action(messages, tools):
    """Ask the LLM for the next native function call, via the registered runtime."""
    response = get_client().with_options(timeout=60).chat.completions.create(
        model=os.getenv("LLM_MODEL_1"), messages=messages, tools=tools,
        tool_choice="auto", parallel_tool_calls=False, reasoning_effort="none",
        temperature=0, max_tokens=1000,
    )
    choice = response.choices[0]
    if choice.finish_reason == "length":
        raise ValueError("Model response exceeded output limit")
    message = choice.message
    return {"content": message.content, "tool_calls": [
        {"id": call.id, "type": "function", "function": {"name": call.function.name, "arguments": call.function.arguments}}
        for call in message.tool_calls or []
    ], "total_tokens": response.usage.total_tokens if response.usage else 0,
        "prompt_tokens": getattr(response.usage, "prompt_tokens", 0) or 0,
        "completion_tokens": getattr(response.usage, "completion_tokens", 0) or 0,
        "cached_tokens": getattr(getattr(response.usage, "prompt_tokens_details", None), "cached_tokens", 0) or 0}
