import logging
from typing import Optional
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import create_react_agent
from core.redis import (
    add_short_term_memory,
    clear_short_term_memory,
    get_short_term_memory,
)
from datetime import datetime
from schemas.agent import SessionState
from schemas.mongo import Message


GRAPH: Optional[CompiledStateGraph[SessionState, None, SessionState, SessionState]] = (
    None
)
LLM: Optional[ChatOllama] = None


def get_graph() -> CompiledStateGraph[SessionState, None, SessionState, SessionState]:
    if GRAPH is None:
        raise RuntimeError("The graph has not been built.")
    return GRAPH


def get_llm() -> ChatOllama:
    if LLM is None:
        raise RuntimeError("The LLM has not been initialized")
    return LLM


def summarize_messages(llm: ChatOllama, messages: list[Message]) -> str | None:
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


def build_agent(llm: ChatOllama, tools: list, prompt: SystemMessage):
    agent = create_agent(model=llm, tools=tools, system_prompt=prompt)
    return agent


def build_graph(agent):
    def update_memory(state: SessionState) -> SessionState:
        session_id = state["session_id"]
        message = state["message"]

        add_short_term_memory(session_id, message)

        return state

    def maybe_summarize(state: SessionState) -> SessionState:
        session_id = state["session_id"]
        msg = get_short_term_memory(session_id)
        if len(msg) > 15:
            summarized = summarize_messages(state["llm"], msg)
            if summarized is None:
                return state
            clear_short_term_memory(session_id)
            add_short_term_memory(
                session_id,
                {
                    "role": "system",
                    "content": f"SUMMARY: {summarized}",
                    "timestamp": datetime.now().isoformat(),
                },
            )
        return state

    def run_agent(state: SessionState) -> SessionState:
        session_id = state["session_id"]
        chat_history = get_short_term_memory(session_id)

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

        # TODO: Use a check for the token emitting for streaming messages with a check on the final output if it isn't then redisplay
        response = agent.invoke(
            {"session_id": state["session_id"], "messages": messages}
        )

        logging.info(response)

        add_short_term_memory(
            session_id,
            {
                "role": "system",
                "content": response["messages"][-1].content,
                "timestamp": datetime.now().isoformat(),
            },
        )

        state["response"] = response["messages"][-1].content
        return state

    graph = StateGraph(state_schema=SessionState)

    graph.add_node("maybe_summarize", maybe_summarize)
    graph.add_node("update_memory", update_memory)
    graph.add_node("run_agent", run_agent)

    graph.set_entry_point("maybe_summarize")
    graph.add_edge("maybe_summarize", "update_memory")
    graph.add_edge("update_memory", "run_agent")
    graph.add_edge("run_agent", END)

    return graph.compile()
