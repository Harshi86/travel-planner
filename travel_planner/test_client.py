import asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def main():
    async with streamablehttp_client("http://127.0.0.1:8000/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("Tools:", [t.name for t in tools.tools])
            result = await session.call_tool(
                "plan_trip",
                {
                    "destination": "Goa",
                    "nights": 5,
                    "budget": 22000,
                    "start_date": "2026-12-20",
                    "preferences": ["beaches", "food", "no early mornings"],
                },
            )
            print("Result:", result.content[0].text)


asyncio.run(main())
