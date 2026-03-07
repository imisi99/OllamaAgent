from langchain_core.messages import SystemMessage


system_prompt = SystemMessage(
    content="""
        You are a helpful assistant and you have access to the following tools 
    """,
)
