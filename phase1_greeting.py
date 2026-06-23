"""
Phase 1 — The Birth of Spark
Concepts: query(), ClaudeAgentOptions, message streaming, response parsing, conditional routing
"""

import asyncio
import os
from dotenv import load_dotenv
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage
from claude_agent_sdk.types import StreamEvent
from workspace import CLAUDE_MD, write_claude_md
load_dotenv()

# FILL IN: Write Spark's personality and greeting instructions here
SYSTEM_PROMPT = """
You are Spark, the friendly AI support agent for EcoRide — a smart EV scooter startup.
Greet the customer warmly and respond directly to what they asked.

If their message clearly shows they are a new or prospective customer (e.g. asking about
products, pricing, or learning), help them as a guest — do NOT ask if they are new or existing.
Only ask for clarification if their intent is genuinely ambiguous and you truly cannot help without knowing.
"""

write_claude_md(CLAUDE_MD)  # write the system prompt to .claude/CLAUDE.md for project-wide access

env = {
    "ANTHROPIC_BASE_URL": "https://llm.keyvalue.systems",
    "ANTHROPIC_API_KEY": os.getenv("LITE_LLM_KEY"),
    "HOME": os.getenv("MY_HOME"),
}
async def stream_response(user_input: str) -> str:
    """Stream Spark's reply to stdout and return the full text for routing."""
    options = ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        setting_sources=['project'],
        tools=[],  # No tools in Phase 1 — pure conversation
        include_partial_messages=True,  # enables streaming chunks
        env=env,
    )

    full_text = []

    async for message in query(prompt=user_input, options=options):
        if isinstance(message, StreamEvent):
            event = message.event
            if event.get("type") == "content_block_delta":
                delta = event.get("delta", {})
                if delta.get("type") == "text_delta":
                    chunk = delta.get("text", "")
                    print(chunk, end="", flush=True)
                    full_text.append(chunk)
        elif isinstance(message, ResultMessage) and message.is_error:
            raise RuntimeError(f"Agent error: {message.result}")

    print()
    return "".join(full_text)

async def main():
    user_input = "Hi, Can you help me learn about your scooters?"
    print(f"Customer: {user_input}\n")

    print("Spark: ", end="", flush=True)
    reply = await stream_response(user_input)


if __name__ == "__main__":
    asyncio.run(main())