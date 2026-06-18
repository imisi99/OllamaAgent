import json
import logging
import ollama
import random
import zoneinfo
from tavily import TavilyClient
from datetime import datetime
from typing import Annotated, Any
from langchain.tools import InjectedState, tool
from zoneinfo import ZoneInfo
import requests


from core.agent import get_model
from db.mongo import get_mongo_database
from db.qdrant import get_qdrant_database
from schemas.agent import SessAgentState
from schemas.mongo import Session

# TODO:
# The web search works for only the bing engine the duckduckgo (timeout), google (request denied) (What's the score for and should it be added ?)
# The web search could also work by adding a search url for more content ?


@tool
def get_current_time(timezone: str = "UTC") -> str:
    """
    Get the current date and time. Optionally pass a timezone (e.g. 'Africa/Lagos').
    """
    try:
        now = datetime.now(ZoneInfo(timezone))
        return now.strftime("%A, %B %d %Y %I:%M %p %Z")
    except zoneinfo.ZoneInfoNotFoundError:
        return f"Unknown timezone '{timezone}'. Defaulting to UTC: {datetime.now(ZoneInfo('UTC')).strftime('%Y-%m-%d %H:%M:%S UTC')}"


@tool
def get_user_location() -> str:
    """
    Get the user approximate location based on their IP address.
    """
    try:
        response = requests.get("http://ip-api.com/json/", timeout=5)
        data = response.json()
        if data.get("status") == "success":
            return (
                f"City: {data.get('city')}, "
                f"Region: {data.get('regionName')}, "
                f"Country: {data.get('country')}, "
                f"Timezone: {data.get('timezone')}"
            )
        return "Could not determine location."
    except Exception as e:
        return f"Location lookup failed: {e}"


@tool
def get_time_and_location() -> str:
    """
    Get the user approximate location and local time based on the location
    """
    location_info = get_user_location.invoke({})

    timezone = "UTC"
    for part in location_info.split(", "):
        if part.startswith("Timezone:"):
            timezone = part.replace("Timezone: ", "").strip()
            break

    time_info = get_current_time.invoke({"timezone": timezone})
    return f"Location -> {location_info} \n Local Time -> {time_info}"


@tool
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
    This makes a web search using the query and max results (The max results is 10 it defaults to 5)

    Args:
        query: The search query to use for the web search
        max_results: The maximum number of contents to return from the web search
    """

    def ollama_search(query: str, max_results: int = 5):
        response = ollama.web_search(query, max_results)
        response.results

    def tavily_search(query: str, max_results: int = 5):
        tavily_client = TavilyClient(api_key="")
        response = tavily_client.search(
            query,
        )

    rand = random.randint(0, 1)

    try:
        if rand == 0:
            ollama_search(query, max_results)
        else:
            tavily_search(query, max_results)
    except Exception as e:
        pass


@tool(parse_docstring=True)
def web_fetch(url: str) -> dict | str:
    """
    This makes a web fetch using the url provided to fetch the page content for that url

    Args:
        url: The url to fetch the page content
    """

    def ollama_fetch(url: str):
        response = ollama.web_fetch(url)
        return {
            "title": response.title,
            "content": response.content,
            "links_found_on_page": response.links,
        }

    try:
        return ollama_fetch(url)
    except Exception as e:
        pass

    return ""


@tool(parse_docstring=True)
async def find_related_sessions(
    state: Annotated[SessAgentState, InjectedState],
    use_query: bool = False,
    query: str = "",
    score_threshold: float = 0.50,
    limit: int = 2,
    summarize_chat: bool = True,
) -> str:
    """
    This finds past sessions that might be related to the current chat for more context
    either using the whole current session content or a query for specific search

    Args:
        use_query: This indicates whether to use a query for the similarity search (this defaults to False)
        query: This is the field to use for search (when use_query is True a query is required otherwise the whole session content is used)
        score_threshold: This is the threshold for the similarity score (this defaults to 0.50)
        limit: This is the limit for the number of sessions to retrieve it might retrieve lower than the limit if few document pass the threshold (this defaults to 2)
        summarize_chat: This indicates whether to summarize the retrieved chats if the number of retrieved chat is high (limit >= 2 then it should be True) (this defaults to True)
    """
    result = await get_qdrant_database().get_related_points(
        state["session_uid"], query, score_threshold, use_query, limit
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
                f"{session['name']}: \nSUMMARY: \n{get_model().summarize_messages(session['messages'])}"
            )
    else:
        for session in sessions:
            msg = "\n".join(
                f"{msg['role']}: {msg['content']}" for msg in session["messages"]
            )
            chats.append(f"{session['name']}: \n{msg}")

    logging.info(f"Retrieval information for session with id {state['session_id']}")

    logging.info(
        f"SCORE THRESHOLD -> {score_threshold}, LIMIT -> {limit}, AVERAGE SCORE -> {avg_score}, QUERY -> {query}, USE QUERY -> {use_query}"
    )

    logging.info(
        f"RELEVANCE: \n{'\n'.join(f'ID -> {sess["_id"]}, NAME -> {sess["name"]}, SCORE -> {score}' for sess, score in result[0])}"
    )

    if summarize_chat:
        logging.info(f"SUMMARY: \n{'\n'.join(chats)}")

    return f"RETRIEVED CHATS: {'\n'.join(chats)}"


tools = [
    get_user_info,
    get_user_location,
    get_current_time,
    get_time_and_location,
    save_insight_about_user,
    web_search,
    find_related_sessions,
    remove_insight_about_user,
]
