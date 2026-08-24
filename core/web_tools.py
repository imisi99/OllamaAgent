from tavily import TavilyClient

TAVILY_CLIENT: TavilyClient | None = None


def create_tavily(api_key: str) -> TavilyClient:
    return TavilyClient(api_key)


def get_tavily() -> TavilyClient:
    if not TAVILY_CLIENT:
        raise Exception("Tavily client not initialized.")
    return TAVILY_CLIENT
