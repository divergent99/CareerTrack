import os
import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

response = client.beta.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=200,
    messages=[{"role": "user", "content": "What tools do you have?"}],
    mcp_servers=[
        {
            "type": "url",
            "url": "https://cockroachlabs.cloud/mcp",
            "name": "cockroach-mcp",
            "authorization_token": os.environ["COCKROACH_MCP_KEY"],
        }
    ],
    tools=[
        {
            "type": "mcp_toolset",
            "mcp_server_name": "cockroach-mcp"
            # no allowed_tools here = everything enabled, this is just discovery
        }
    ],
    betas=["mcp-client-2025-11-20"],
)
print(response.content)