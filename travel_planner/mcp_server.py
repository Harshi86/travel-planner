from mcp.server.fastmcp import FastMCP

mcp = FastMCP("travel-planner", stateless_http=True)


@mcp.tool()
def plan_trip(destination: str, nights: int, budget: int) -> str:
    """Plan a trip to a destination for a number of nights within a budget in rupees."""
    return f"Test: {nights} nights in {destination} with budget {budget}."


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
    