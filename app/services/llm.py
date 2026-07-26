from functools import lru_cache

from langchain_openai import ChatOpenAI

from config import get_settings


@lru_cache(maxsize=None)
def get_chat_model(temperature: float = 0.0) -> ChatOpenAI:
    """The shared ChatOpenAI client, built once from settings.

    Every agent used to construct its own `ChatOpenAI(model=..., api_key=...)`;
    this centralises that so the model/key live in one place. Cached per
    temperature, so callers reuse one instance. Layer `.bind_tools(...)` or
    `.with_structured_output(...)` on top as needed — those return new runnables
    and never mutate the cached client, so sharing it is safe.

    Defaults to temperature=0 for deterministic, reproducible agent behaviour.
    """
    settings = get_settings()
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=temperature,
    )
