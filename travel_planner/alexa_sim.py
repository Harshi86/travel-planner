import json
import os
from datetime import date
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from openai import AsyncOpenAI
from pydantic import BaseModel

load_dotenv()

MCP_URL = os.getenv("MCP_URL", "http://127.0.0.1:8000/mcp")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

llm = AsyncOpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

app = FastAPI()


def system_prompt() -> str:
    return (
        "You are a simulated Alexa+ voice assistant. Speak in short, friendly, "
        "natural sentences, because your answer will be read aloud. No markdown, "
        "no bullet points, no emojis. Use the available tools to plan and change "
        "trips, and never invent trip details. Trips start from Bengaluru and only "
        "Goa, Jaipur and Kochi are supported. Always remember the trip ID from "
        "earlier tool results so the user can ask follow-up questions. "
        f"Today's date is {date.today().isoformat()}."
    )


def clean_schema(s):
    """Make the MCP tool schema simple enough for Gemini."""
    if isinstance(s, dict):
        if "anyOf" in s:
            options = [o for o in s["anyOf"] if o.get("type") != "null"]
            if options:
                return clean_schema(options[0])
        return {k: clean_schema(v) for k, v in s.items() if k not in ("title", "default")}
    if isinstance(s, list):
        return [clean_schema(x) for x in s]
    return s


class ChatRequest(BaseModel):
    messages: list[dict]


@app.get("/", response_class=HTMLResponse)
async def home():
    return (Path(__file__).parent / "alexa_sim.html").read_text(encoding="utf-8")


@app.post("/chat")
async def chat(req: ChatRequest):
    calls: list[dict] = []
    try:
        async with streamablehttp_client(MCP_URL) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                listed = await session.list_tools()
                tools = [
                    {
                        "type": "function",
                        "function": {
                            "name": t.name,
                            "description": t.description or "",
                            "parameters": clean_schema(t.inputSchema),
                        },
                    }
                    for t in listed.tools
                ]
                messages = [{"role": "system", "content": system_prompt()}] + req.messages

                for _ in range(6):
                    resp = await llm.chat.completions.create(
                        model=MODEL, messages=messages, tools=tools
                    )
                    msg = resp.choices[0].message
                    if not msg.tool_calls:
                        return {"reply": msg.content or "", "tool_calls": calls}

                    messages.append(msg.model_dump(exclude_none=True))
                    for tc in msg.tool_calls:
                        args = json.loads(tc.function.arguments or "{}")
                        result = await session.call_tool(tc.function.name, args)
                        text = "\n".join(c.text for c in result.content if hasattr(c, "text"))
                        calls.append({"name": tc.function.name, "args": args, "result": text})
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tc.id,
                                "name": tc.function.name,
                                "content": text,
                            }
                        )
                return {"reply": "Sorry, that took too many steps.", "tool_calls": calls}
    except Exception as e:
        while isinstance(e, BaseExceptionGroup) and e.exceptions:
            e = e.exceptions[0]
        return {
            "reply": f"Sorry, something went wrong: {type(e).__name__}: {e}",
            "tool_calls": calls,
        }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
    