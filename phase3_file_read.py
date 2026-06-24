"""
Phase 4 — The Grumpy Customer (ReAct)
Concepts: ClaudeSDKClient, multi-turn session, ToolUseBlock tracing, max_turns
"""

import asyncio
import os
from claude_agent_sdk import (
    ClaudeAgentOptions,
    ResultMessage,
    tool,
    create_sdk_mcp_server,
    query,
)
from claude_agent_sdk.types import StreamEvent
from dotenv import load_dotenv
from workspace import CLAUDE_MD, write_claude_md

load_dotenv()
env = {
    "ANTHROPIC_BASE_URL": "https://llm.keyvalue.systems",
    "ANTHROPIC_API_KEY": os.getenv("LITE_LLM_KEY"),
    "HOME": os.getenv("MY_HOME"),
}

# ---------------------------------------------------------------------------
# Mock databases (carried over)
# ---------------------------------------------------------------------------

ORDERS = {
    "ORD-001": {"status": "In Transit", "eta": "2 days"},
    "ORD-002": {"status": "Delivered", "eta": None},
}

WALLETS = {
    "CUST-001": {"balance": 120.50, "currency": "USD"},
    "CUST-042": {"balance": 45.00, "currency": "USD"},
}

# ---------------------------------------------------------------------------
# Tools (same as Phase 3)
# ---------------------------------------------------------------------------

@tool("check_order_status", "Check the delivery status of an EcoRide order", {"order_id": str})
async def check_order_status(args: dict) -> dict:
    order_id = args["order_id"]
    order = ORDERS.get(order_id)
    if not order:
        return {"content": [{"type": "text", "text": f"Order {order_id} not found."}]}
    return {"content": [{"type": "text", "text": f"Order {order_id}: {order['status']}. ETA: {order.get('eta', 'N/A')}"}]}


@tool("get_wallet_balance", "Get the wallet balance for an EcoRide customer", {"customer_id": str})
async def get_wallet_balance(args: dict) -> dict:
    customer_id = args["customer_id"]
    wallet = WALLETS.get(customer_id)
    if not wallet:
        return {"content": [{"type": "text", "text": f"No wallet found for {customer_id}."}]}
    return {"content": [{"type": "text", "text": f"Balance for {customer_id}: {wallet['balance']} {wallet['currency']}"}]}


ecoride_server = create_sdk_mcp_server(
    name="ecoride",
    tools=[check_order_status, get_wallet_balance],
)


SYSTEM_PROMPT = """
You are Spark, the AI support agent for EcoRide.
For complex problems, reason step by step before calling any tool.
Think: what do I need to find out first? Act by calling the right tool.
Observe the result, then decide what to do next.
Read the manual for any product questions, and check order/wallet tools for account issues.
"""

write_claude_md(CLAUDE_MD)

async def file_read(user_input: str) -> str:
    options = ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        setting_sources=['project'],
        mcp_servers={"ecoride": ecoride_server},
        # TODO: add allowed_tools — include both mcp tools and built-in file tools
        # https://code.claude.com/docs/en/agent-sdk/python#claudeagentoptions
        allowed_tools=...,  # FILL IN
        include_partial_messages=True,  # enables streaming chunks
        env=env,
    )

    full_text = []
    current_tool = None

    async for message in query(prompt=user_input, options=options):
        if isinstance(message, StreamEvent):
            event = message.event
            event_type = event.get("type")

            if event_type == "content_block_start":
                content_block = event.get("content_block", {})
                if content_block.get("type") == "tool_use":
                    current_tool = content_block.get("name")
                    print(f"\n  [TOOL CALL]  {current_tool}", flush=True)

            elif event_type == "content_block_delta":
                delta = event.get("delta", {})
                if delta.get("type") == "text_delta":
                    chunk = delta.get("text", "")
                    print(chunk, end="", flush=True)
                    full_text.append(chunk)

            elif event_type == "content_block_stop":
                if current_tool:
                    current_tool = None

        elif isinstance(message, ResultMessage) and message.is_error:
            raise RuntimeError(f"Agent error: {message.result}")

    print()
    return "".join(full_text)


async def main():
    user_input = (
        "My scooter won't start and I need to get to work! "
        "Is there a known battery issue, and what is the refund policy if I return it?"
    )
    print(f"Customer: {user_input}\n")
    print("--- File Read trace ---")
    await file_read(user_input)
    print("-------------------")


if __name__ == "__main__":
    asyncio.run(main())