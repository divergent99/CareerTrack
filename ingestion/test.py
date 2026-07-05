import anthropic
import os
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

response = client.beta.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=500,
    messages=[{"role": "user", "content": "List the tables in my CockroachDB cluster"}],
    mcp_servers=[
        {
            "type": "url",
            "url": "https://cockroachlabs.cloud/mcp",
            "name": "cockroach-mcp",
            "authorization_token": os.environ["COCKROACH_MCP_KEY"]
        }
    ],
    extra_headers={
        "anthropic-beta": "mcp-client-2025-04-04"
    }
)
print(response.content)