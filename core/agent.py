import logging
from datetime import datetime
from typing import Optional
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from db.redis import get_redis_database
from schemas.agent import SessionState
from schemas.mongo import Message


GRAPH: Optional[CompiledStateGraph[SessionState, None, SessionState, SessionState]] = (
    None
)
LLM: Optional[ChatOllama] = None
LLM_NO_REASONING: Optional[ChatOllama] = None


def get_graph() -> CompiledStateGraph[SessionState, None, SessionState, SessionState]:
    if GRAPH is None:
        raise RuntimeError("The graph has not been built.")
    return GRAPH


def get_llm_no_reasoning() -> ChatOllama:
    if LLM_NO_REASONING is None:
        raise RuntimeError("The LLM has not been initialized")
    return LLM_NO_REASONING


def get_llm_reasoniing() -> ChatOllama:
    if LLM is None:
        raise RuntimeError("The LLM has not been initialized")
    return LLM


def log_llm_response(response, label: str = "LLM"):
    reasoning = response.additional_kwargs.get("reasoning_content", None)
    content = response.content
    metadata = response.response_metadata

    if reasoning:
        logging.info(f"[{label}] THINKING: \n {reasoning}")

    if isinstance(content, str):
        logging.info(f"[{label}] RESPONSE: {content}")
    elif isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                logging.info(f"[{label}] RESPONSE: {block['text']}")

    logging.info(
        f"[{label}] TOKENS -> input: {metadata.get('prompt_eval_count')} "
        f"output: {metadata.get('eval_count')} "
        f"total_duration: {metadata.get('total_duration', 0) / 1e9:.3f}s"
    )


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
    log_llm_response(response, "SUMMARIZER")
    if isinstance(response.content, str):
        return response.content

    return None


def generate_title(content: str) -> str:
    prompt = (
        "Generate a title for a chat session not more than 5 words using the user first input. You respond should be the title ONLY (one title) without the string quote an example is \n Explaining Docker Compose \n \n\n\n"
        + content
    )
    title = "Untitled Session"

    try:
        response = get_llm_no_reasoning().invoke(prompt)
        log_llm_response(response, "TITLEGEN")
        if isinstance(response.content, str):
            title = response.content
    except Exception as e:
        logging.error(f"Failed to generate title -> {e}")
    return title


def build_agent(llm: ChatOllama, tools: list, prompt: SystemMessage):
    agent = create_agent(model=llm, tools=tools, system_prompt=prompt)
    return agent


def build_graph(agent):
    def update_memory(state: SessionState) -> SessionState:
        session_id = state["session_id"]
        message = state["message"]

        get_redis_database().add_short_term_memory(session_id, message)

        return state

    def maybe_summarize(state: SessionState) -> SessionState:
        session_id = state["session_id"]
        redDB = get_redis_database()
        msg = redDB.get_short_term_memory(session_id)
        if len(msg) > 25:
            summarized = summarize_messages(state["llm"], msg)
            if summarized is None:
                return state
            redDB.clear_short_term_memory(session_id)
            redDB.add_short_term_memory(
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
        chat_history = get_redis_database().get_short_term_memory(session_id)

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
            {
                "session_id": state["session_id"],
                "user_id": state["user_id"],
                "ghost_session": state["ghost_session"],
                "messages": messages,
            }
        )

        log_llm_response(response, "AGENT")

        get_redis_database().add_short_term_memory(
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
