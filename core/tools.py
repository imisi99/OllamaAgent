import json
from typing import Any
from langchain.tools import tool

from db.mongo import get_mongo_database


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


tools = [get_user_info, save_insight_about_user]
