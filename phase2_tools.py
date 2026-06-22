"""
Phase 2 — Giving Spark a Brain
Concepts: @tool decorator, create_sdk_mcp_server(), mcp_servers, allowed_tools
"""

import asyncio
import os
from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    ResultMessage,
    tool,
    create_sdk_mcp_server,
)
from claude_agent_sdk.types import StreamEvent
from dotenv import load_dotenv
from workspace import CLAUDE_MD, write_claude_md

load_dotenv()

env = {
    "ANTHROPIC_BASE_URL": "https://openrouter.ai/api",
    "ANTHROPIC_AUTH_TOKEN": os.getenv("OPENROUTER_API_KEY"),
    "ANTHROPIC_API_KEY": "",
    "HOME": os.getenv("MY_HOME"),
}

# ---------------------------------------------------------------------------
# Mock databases
# ---------------------------------------------------------------------------

ORDERS = {
    "ORD-001": {"status": "In Transit", "eta": "2 days"},
    "ORD-002": {"status": "Delivered", "eta": None},
    "ORD-003": {"status": "Processing", "eta": "5 days"},
}

WALLETS = {
    "CUST-001": {"balance": 120.50, "currency": "USD"},
    "CUST-042": {"balance": 45.00, "currency": "USD"},
}

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

# FILL IN: Add @tool("check_order_status", "<description>", {"order_id": str})
@tool("check_order_status", "Check the delivery status of an EcoRide order", {"order_id": str})
async def check_order_status(args: dict) -> dict:
    order_id = args["order_id"]
    order = ORDERS.get(order_id)
    if not order:
        return {"content": [{"type": "text", "text": f"Order {order_id} not found."}]}
    return {"content": [{"type": "text", "text": f"Order {order_id}: {order['status']}. ETA: {order.get('eta', 'N/A')}"}]}


# FILL IN: Add @tool("get_wallet_balance", "<description>", {"customer_id": str})
@tool("get_wallet_balance", "Get the wallet balance for an EcoRide customer", {"customer_id": str})
async def get_wallet_balance(args: dict) -> dict:
    customer_id = args["customer_id"]
    wallet = WALLETS.get(customer_id)
    if not wallet:
        return {"content": [{"type": "text", "text": f"No wallet found for {customer_id}."}]}
    return {"content": [{"type": "text", "text": f"Balance for {customer_id}: {wallet['balance']} {wallet['currency']}"}]}


# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------

# FILL IN: Add check_order_status and get_wallet_balance to the tools list
ecoride_server = create_sdk_mcp_server(
    name="ecoride",
    tools=[check_order_status, get_wallet_balance],
)

# ---------------------------------------------------------------------------
# Options & query
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """
You are Spark, the AI support agent for EcoRide.
Help customers check their order status and wallet balance using the available tools.
"""

write_claude_md(CLAUDE_MD)

async def stream_response(user_input: str) -> None:
    """Stream Spark's reply to stdout as chunks arrive, logging tool calls."""
    options = ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        setting_sources=['project'],
        # FILL IN: Register the MCP server — mcp_servers={"ecoride": ecoride_server}
        mcp_servers={"ecoride": ecoride_server},
        # FILL IN: Allow tools by name — allowed_tools=["mcp__ecoride__check_order_status", "mcp__ecoride__get_wallet_balance"]
        allowed_tools=["mcp__ecoride__check_order_status", "mcp__ecoride__get_wallet_balance"],
        include_partial_messages=True,  # enables streaming chunks
        env=env,
    )

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
                    print(delta.get("text", ""), end="", flush=True)

            elif event_type == "content_block_stop":
                if current_tool:
                    current_tool = None

        elif isinstance(message, ResultMessage) and message.is_error:
            raise RuntimeError(f"Agent error: {message.result}")

async def main():
    questions = [
        "Where is my order ORD-001?",
        "What is my wallet balance for my customer id  CUST-042?",
    ]
    for q in questions:
        print(f"\nCustomer: {q}")
        print("\nSpark: ", end="", flush=True)
        await stream_response(q)
        print()


if __name__ == "__main__":
    asyncio.run(main())