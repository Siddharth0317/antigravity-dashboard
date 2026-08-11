import asyncio
import os
import streamlit as st
from dotenv import load_dotenv
from config import GEMINI_API_KEY
from google.antigravity import Agent, LocalAgentConfig
from google.antigravity.hooks.policy import allow, ask_user, deny
from google.antigravity.types import McpStdioServer

async def handle_ask_user_policy(action_context):
    """
    Policy handler that pauses execution and waits for 
    user interaction on the Streamlit frontend.
    """
    tool_name = getattr(action_context, "tool_name", "Sensitive Action")
    details = str(action_context)

    # Store pending request in Streamlit session state
    st.session_state.pending_approval = {
        "tool_name": tool_name,
        "details": details,
        "status": "pending"  # pending, approved, or rejected
    }

    # Poll session state until the user clicks Approve or Reject in the UI
    while st.session_state.get("pending_approval") and st.session_state.pending_approval.get("status") == "pending":
        await asyncio.sleep(0.5)

    approved = bool(st.session_state.get("pending_approval") and st.session_state.pending_approval.get("status") == "approved")
    
    # Clear the pending flag after decision
    st.session_state.pending_approval = None
    return approved

async def stream_antigravity_agent(user_message: str):
    load_dotenv(override=True)
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("API_KEY") or GEMINI_API_KEY

    if not api_key:
        raise ValueError(
            "Gemini API key is missing! Please set GEMINI_API_KEY=your_key in your .env file."
        )

    # Configure policies: require approval for system commands/tool calls
    safety_policies = [
        deny("dangerous_system_delete"),
        allow("read_file"),
        ask_user("run_command", handler=handle_ask_user_policy),
        ask_user("write_file", handler=handle_ask_user_policy),
    ]

    # Filesystem MCP server pointing to ./shared_data
    filesystem_mcp = McpStdioServer(
        name="filesystem",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "./shared_data"]
    )

    config = LocalAgentConfig(
        api_key=api_key,
        system_instructions=(
            "You are an autonomous AI assistant powered by Google Antigravity. "
            "You have access to a filesystem MCP server pointing to the './shared_data' directory. "
            "When users upload files, they are placed in './shared_data'. Use your filesystem tools to inspect, "
            "read, or process files when requested. "
            "Sensitive actions like modifying files or running commands require user approval via UI."
        ),
        mcp_servers=[filesystem_mcp],
        policies=safety_policies,
    )

    async with Agent(config) as agent:
        response = await agent.chat(user_message)
        async for chunk in response:
            yield chunk

def generate_agent_stream(prompt: str):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    gen = stream_antigravity_agent(prompt)
    try:
        while True:
            chunk = loop.run_until_complete(gen.__anext__())
            yield chunk
    except StopAsyncIteration:
        pass
    finally:
        loop.close()