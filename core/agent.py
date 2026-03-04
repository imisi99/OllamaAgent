import json
import logging
from os import stat
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from langgraph.graph import StateGraph, END
from core.redis import (
    add_short_term_memory,
    clear_short_term_memory,
    get_short_term_memory,
)
from datetime import date, datetime
from models.mongo import Message, Session

llm = ChatOllama(model="qwen2.5-coder")


def summarize_messages(messages: list[Message]) -> str | None:
    conversation = "\n".join(f"{m['role']}: {m['content']}" for m in messages)

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(
                content="Summarize the following conversation concisely, preserving key facts and context."
            ),
            HumanMessage(content=conversation),
        ]
    )

    chain = prompt | llm
    response = chain.invoke({})
    logging.info(response)
    logging.info(response.content)
    print(type(response.content))
    if isinstance(response.content, str):
        return response.content

    return None


def build_graph():
    def update_memory(state):
        user_id = state.user_id
        session_id = state.session_id
        message = state.message

        add_short_term_memory(session_id, message)

        return state

    def maybe_summarize(state):
        session_id = state.session_id
        msg = get_short_term_memory(session_id)
        if len(msg) > 15:
            summarized = summarize_messages(msg)
            if summarized is None:
                return state
            clear_short_term_memory(session_id)
            add_short_term_memory(
                session_id,
                {
                    "role": "system",
                    "content": f"SUMMARY: {summarized}",
                    "timestamp": datetime.now(),
                },
            )
        return state

    def run_agent(state):
        session_id = state.session_id
        chat_history = get_short_term_memory(session_id)
        logging.info(chat_history)

        messages = []
        if chat_history:
            for msg in chat_history:
                role = msg["role"]
                if role == "system":
                    messages.append(SystemMessage(content=msg["content"]))
                elif role == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif role == "assistant":
                    messages.append(AIMessage(content=msg["content"]))

        agent = create_agent(model=llm)

        response = agent.invoke(
            {"messages": messages + [HumanMessage(content=json.dumps(state.message))]}
        )

        logging.info(response)

        add_short_term_memory(
            session_id,
            {
                "role": "system",
                "content": response["messages"][-1].content,
                "timestamp": datetime.now(),
            },
        )

        state.response = response["messages"][-1].content
        return state

    graph = StateGraph(state_schema=Session)

    graph.add_node("maybe_summarize", maybe_summarize)
