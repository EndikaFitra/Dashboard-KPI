"""
Ollama Service — HTTP calls to local Ollama instance.
"""
import logging
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:4b-instruct")

logger = logging.getLogger(__name__)


async def generate_response(prompt: str) -> str:
    """
    Call Ollama /api/generate endpoint.
    Returns the model's response text.
    """
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.3,
            "num_predict": 512,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "").strip()
    except httpx.ConnectError:
        logger.error("Cannot connect to Ollama. Is it running at %s?", OLLAMA_URL)
        return "I'm unable to connect to the AI backend right now. Please ensure Ollama is running."
    except httpx.TimeoutException:
        logger.error("Ollama request timed out")
        return "The AI request timed out. Please try again."
    except Exception as e:
        logger.error("Ollama error: %s", e, exc_info=True)
        return f"An error occurred while processing your request: {str(e)}"
