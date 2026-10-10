import os

from agents import OpenAIChatCompletionsModel, set_tracing_disabled
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()
set_tracing_disabled(True)  # tracing would otherwise try to contact OpenAI

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


def get_model() -> OpenAIChatCompletionsModel:
    client = AsyncOpenAI(
        api_key=os.environ["GEMINI_API_KEY"],
        base_url=GEMINI_BASE_URL,
    )
    return OpenAIChatCompletionsModel(
        model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
        openai_client=client,
    )
