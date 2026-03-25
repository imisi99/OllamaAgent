import json
import httpx
from typing import Any
from langchain.tools import tool

from db.mongo import get_mongo_database
from db.qdrant import get_qdrant_database


@tool(parse_docstring=True)
def get_user_info(user_id: str) -> str:
    """
    Retrieves details about the user from the db that you might have written in the past.

    Args:
        user_id: This is the user id.
    """
    user = get_mongo_database().fetch_user(user_id)
    if user is None:
        return "The user was not found"
    return json.dumps(user)


@tool(parse_docstring=True)
def save_insight_about_user(user_id: str, key: str, value: Any) -> str:
    """
    This saves important information about the user or things that you've noticed about the user
    The memory is of type dict[str, Any] so a key is needed for the insight discovered
    You can view the current state using get_user_info.

    Args:
        user_id: This is the user id.
        key: The key of the value to store.
        value: The value being stored.
    """
    updated = get_mongo_database().update_user_memory(user_id, key, value)
    if updated:
        return "Operation was successful"
    return "Operation was unsuccessful"


@tool(parse_docstring=True)
def web_search(query: str, max_results: int = 5) -> list[dict]:
    """
    This make a web search using the query and max results (The max results defaults to 5)

    Args:
        query: The search query to use for the web search
        max_results: The maximum number of contents to return from the web search
    """
    resp = httpx.get(
        "http://searxng:8080/search",
        params={"q": query, "format": "json", "engines": "google,bing,duckduckgo"},
    )

    results = resp.json().get("results", [])
    return [
        {"title": r["title"], "url": r["url"], "content": r.get("content", "")}
        for r in results[:max_results]
    ]


# TODO: Also allow for the model to choose to summarize the chat ?
@tool(parse_docstring=True)
def find_related_sessions(
    session_id: str,
    query: str = "",
    use_query: bool = False,
    score_threshold: float = 50.0,
    limit: int = 2,
) -> str:
    """
    This finds past sessions that might be related to the current chat for more context
    either using the whole current session or a query for specific search

    Args:
        session_id: This is the current session id.
        query: This is the optional field to use for particular keyword search (it defaults to "" )
        use_query: This indicates whether to use a query for the similarity search (this defaults to False)
        score_threshold: This is the threshold for the similarity score (this defaults to 50.0)
        limit: This is the limit for the number of sessions to retrieve it might retrieve lower than the limit if few document pass the threshold (this defaults to 2)
    """
    result = get_qdrant_database().get_related_points(
        session_id, query, score_threshold, use_query, limit
    )

    if result is None:
        return "An error occured while trying to perform similarity search"
    points, score = result
    return f"Found {len(points)} chats {points} with an average score of {score}"


tools = [get_user_info, save_insight_about_user, web_search, find_related_sessions]
