import asyncio
from google.antigravity import Agent, LocalAgentConfig
from google.antigravity.hooks.policy import allow, ask_user, deny
from google.antigravity.types import McpStdioServer

async def stream_antigravity_agent(user_message: str):
    safety_policies = [
        deny("shell_execution"),
        allow("read_file"),
        ask_user("run_command", handler=lambda ctx: True),
    ]

    # Filesystem MCP server pointing to ./shared_data
    filesystem_mcp = McpStdioServer(
        name="filesystem",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "./shared_data"]
    )

    config = LocalAgentConfig(
        system_instructions=(
            "You are an autonomous AI assistant powered by Google Antigravity. "
            "You have access to a filesystem MCP server pointing to the './shared_data' directory. "
            "When users upload files, they are placed in './shared_data'. Use your filesystem tools to inspect, "
            "read, or process files when requested."
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