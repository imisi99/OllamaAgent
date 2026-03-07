from langchain.tools import tool


@tool(parse_docstring=True)
def get_user_info(user_id: str):
    """
    Retrieves details about the user from the db that you might have written in the past

    user_id: This is the user id
    """


@tool(parse_docstring=True)
def save_insight_about_user(user_id: str):
    """
    This saves important information about the user or things that you've noticed about the user

    user_id: This is the user id
    """


tools = [get_user_info, save_insight_about_user]
