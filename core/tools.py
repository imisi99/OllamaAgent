import json
import logging
import httpx
from typing import Annotated, Any
from langchain.tools import InjectedState, tool

from core.agent import get_model
from db.mongo import get_mongo_database
from db.qdrant import get_qdrant_database
from schemas.agent import SessAgentState
from schemas.mongo import Session

# TODO:
# The web search error should be clear about user being offline
# DONE:
# Also allow for the model to choose to summarize the chat ?


@tool()
def get_user_info(state: Annotated[SessAgentState, InjectedState]) -> str:
    """
    Retrieves details about the user from the db that you might have written in the past.
    """
    user = get_mongo_database().fetch_user(state["user_id"])
    if user is None:
        return "The user was not found"
    return json.dumps(user)


@tool(parse_docstring=True)
def save_insight_about_user(
    key: str, value: Any, state: Annotated[SessAgentState, InjectedState]
) -> str:
    """
    This saves important information about the user or things that you've noticed about the user
    The memory is of type dict[str, Any] so a key is needed for the insight discovered
    You can view the current state using get_user_info.

    Args:
        key: The key of the value to store.
        value: The value being stored.
    """
    updated = get_mongo_database().update_user_memory(state["user_id"], key, value)
    if updated:
        return "Operation was successful"
    return "Operation was unsuccessful"


@tool(parse_docstring=True)
def remove_insight_about_user(
    key: str, state: Annotated[SessAgentState, InjectedState]
) -> str:
    """
    This removes information about the user or things that you've noticed about the user
    The memory is of type dict[str, Any] so a key is needed for the insight to remove
    You can view the current state using get_user_info.

    Args:
        key: The key of the value to remove.
    """
    removed = get_mongo_database().remove_user_memory(state["user_id"], key)
    if not removed:
        return "Operation was unsuccessful"
    return "Operation was successful"


@tool(parse_docstring=True)
def web_search(query: str, max_results: int = 5) -> list[dict] | str:
    """
    This make a web search using the query and max results (The max results defaults to 5)

    Args:
        query: The search query to use for the web search
        max_results: The maximum number of contents to return from the web search
    """
    try:
        resp = httpx.get(
            "http://searxng:8080/search",
            params={"q": query, "format": "json", "engines": "google,bing,duckduckgo"},
        )
    except Exception as e:
        logging.info(
            f"[TOOL WEB_SEARCH] Failed to search the web most likely due to being offline -> {e}"
        )
        return "The user is offline and web search is currently unavailable"

    logging.info(resp.json())
    results = resp.json().get("results", [])

    if len(results) == 0:
        return "The web search didn't return any result"

    return [
        {"title": r["title"], "url": r["url"], "content": r.get("content", "")}
        for r in results[:max_results]
    ]


@tool(parse_docstring=True)
async def find_related_sessions(
    state: Annotated[SessAgentState, InjectedState],
    query: str = "",
    use_query: bool = False,
    score_threshold: float = 50.0,
    limit: int = 2,
    summarize_chat: bool = True,
) -> str:
    """
    This finds past sessions that might be related to the current chat for more context
    either using the whole current session or a query for specific search

    Args:
        query: This is the optional field to use for particular keyword search (it defaults to "" )
        use_query: This indicates whether to use a query for the similarity search (this defaults to False)
        score_threshold: This is the threshold for the similarity score (this defaults to 50.0)
        limit: This is the limit for the number of sessions to retrieve it might retrieve lower than the limit if few document pass the threshold (this defaults to 2)
        summarize_chat: This indicates whether to summarize the retrieved chats if the number of retrieved chat is high (limit >= 2 then it should be True) (this defaults to True )
    """
    result = await get_qdrant_database().get_related_points(
        state["session_id"], query, score_threshold, use_query, limit
    )

    if result is None:
        return "Unable to get related sessions "

    avg_score = result[1]

    sessions: list[Session] = []

    for session, _ in result[0]:
        sessions.append(session)

    chats = []
    if summarize_chat:
        for session in sessions:
            chats.append(
                f"{session['name']}: \n SUMMARY: \n {get_model().summarize_messagess(session['messages'])}"
            )
    else:
        for session in sessions:
            chats.append(f"{session['name']}: \n")
            chats.append(
                {"role": msg["role"], "content": msg["content"]}
                for msg in session["messages"]
            )

    logging.info(
        f"SCORE THRESHOLD: {score_threshold} \n LIMIT: {limit} \n AVERAGE SCORE: {avg_score} \n QUERY: {query} \n USE QUERY: {use_query}"
    )

    logging.info(
        f"RELEVANCE: {'\n'.join(f'ID -> {sess["_id"]}, NAME -> {sess["name"]} SCORE -> {score}' for sess, score in result[0])}"
    )

    if summarize_chat:
        logging.info(f"SUMMARY: \n {'\n'.join(chats)}")

    return f"RETRIEVED CHATS: \n {'\n'.join(chats)}"


tools = [
    get_user_info,
    save_insight_about_user,
    web_search,
    find_related_sessions,
    remove_insight_about_user,
]
