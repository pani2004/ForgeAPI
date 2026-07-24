from langchain_google_genai import ChatGoogleGenerativeAI
from app.config import GOOGLE_API_KEY, MODEL_NAME


def get_llm()-> ChatGoogleGenerativeAI:
    if not GOOGLE_API_KEY:
        raise ValueError("Google Api Key is not set")

    return ChatGoogleGenerativeAI(
        model=MODEL_NAME,
        google_api_key=GOOGLE_API_KEY,
    )