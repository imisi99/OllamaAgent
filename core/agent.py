import base64
import logging
import os
import tempfile
from datetime import datetime
from typing import Optional, cast
from langchain_core.documents import Document
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
    AIMessageChunk,
)
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool
from langchain_community.document_loaders.generic import GenericLoader
from langchain_community.document_loaders.parsers.language import LanguageParser
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader, UnstructuredHTMLLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter, Language
from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from langgraph.graph import StateGraph, END
from pathlib import Path

from core.qdrant import Qdrant
from db.redis import get_redis_database
from schemas.agent import SessAgentState, SessionState
from schemas.mongo import File, Message

# TODO:
# The prompt length is a factor causing slow response from the agent (reduce it)
# Fix the retrieval quality of the qdrant file chunks


class Model:
    def __init__(
        self,
        llm_no_reason: ChatOllama,
        llm_reason: ChatOllama,
        tool: list[BaseTool],
        prompt: SystemMessage,
        qdrant_client: Qdrant,
    ) -> None:
        self.no_reason = llm_no_reason
        self.reason = llm_reason
        self.graph = self.build_graph(self.build_agent(tool, prompt))
        self.qdrant_client = qdrant_client

    def build_agent(self, tools: list[BaseTool], prompt: SystemMessage):
        agent = create_agent(
            model=self.reason,
            tools=tools,
            system_prompt=prompt,
            state_schema=SessAgentState,
        )

        return agent

    def build_graph(self, agent):
        def update_memory(state: SessionState) -> SessionState:
            get_redis_database().add_short_term_memory(
                state["session_id"], state["message"], True
            )

            return state

        async def embed_and_retrieve_chunks(state: SessionState) -> SessionState:
            if len(state["message"]["files"]) > 0:
                chunks = self.load_document(state["message"]["files"])
                await self.embed_and_store_chunks(state["session_uid"], chunks)

            retrieved_chunks = await self.qdrant_client.retrieve_file_chunks(
                state["message"]["content"], state["session_uid"]
            )

            state["chunks"] = retrieved_chunks

            return state

        def maybe_summarize(state: SessionState) -> SessionState:
            session_id = state["session_id"]
            redDB = get_redis_database()
            msg = redDB.get_short_term_memory(session_id)
            images = []
            if len(msg) > 30:
                for m in msg:
                    if len(m["images"]) > 0:
                        images.extend(m["images"])

                summarized = self.summarize_messages(msg)
                if summarized is None:
                    return state
                redDB.clear_short_term_memory(session_id)
                redDB.add_short_term_memory(
                    session_id,
                    {
                        "role": "system",
                        "thought": "",
                        "content": f"SUMMARY OF THE CHAT SO FAR: {summarized}",
                        "timestamp": datetime.now().isoformat(),
                        "images": images,
                        "files": [],
                    },
                    True,
                )
            return state

        async def run_agent(state: SessionState) -> SessionState:
            session_id = state["session_id"]
            chat_history = get_redis_database().get_short_term_memory(session_id)

            messages = []
            if chat_history:
                for msg in chat_history:
                    role = msg["role"]
                    if role == "system":
                        messages.append(SystemMessage(content=msg["content"]))
                    elif role == "user":
                        is_current = msg is chat_history[-1]
                        if is_current:
                            if len(msg["images"]) > 0:
                                content: list[str | dict] = [
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:{image['mime']};base64,{image['image']}"
                                        },
                                    }
                                    for image in msg["images"]
                                ]
                                content.append({"type": "text", "text": msg["content"]})
                                messages.append(HumanMessage(content=content))
                            else:
                                messages.append(HumanMessage(content=msg["content"]))
                        else:
                            image_count = len(msg["images"])
                            placeholder = (
                                (
                                    f"[{image_count} image(s) attached] \n {msg['content']}"
                                )
                                if image_count > 0
                                else msg["content"]
                            )
                            messages.append(HumanMessage(content=placeholder))
                    elif role == "assistant":
                        messages.append(AIMessage(content=msg["content"]))

            prompt = f"""
            Use the following documents to answer the user question.
            <document>
            {state["chunks"]}
            </document>

            User Question:
            {state["message"]["content"]}
            """

            if len(state["chunks"]) > 0:
                messages[-1].content = prompt

            response = await agent.ainvoke(
                {
                    "session_id": session_id,
                    "session_uid": state["session_uid"],
                    "user_id": state["user_id"],
                    "ghost_session": state["ghost_session"],
                    "messages": messages,
                }
            )

            self.log_llm_response(response["messages"], "AGENT")

            get_redis_database().add_short_term_memory(
                session_id,
                {
                    "role": "assistant",
                    "thought": "",
                    "content": response["messages"][-1].content,
                    "timestamp": datetime.now().isoformat(),
                    "images": [],
                    "files": [],
                },
            )

            state["response"] = response["messages"][-1].content
            return state

        graph = StateGraph(state_schema=SessionState)

        graph.add_node("maybe_summarize", maybe_summarize)
        graph.add_node("update_memory", update_memory)
        graph.add_node("embed_retrieve_file_chunks", embed_and_retrieve_chunks)
        graph.add_node("run_agent", run_agent)

        graph.set_entry_point("maybe_summarize")
        graph.add_edge("maybe_summarize", "update_memory")
        graph.add_edge("update_memory", "embed_retrieve_file_chunks")
        graph.add_edge("embed_retrieve_file_chunks", "run_agent")
        graph.add_edge("run_agent", END)

        return graph.compile()

    def chat(self, prompt: SessionState):
        return self.graph.ainvoke(prompt)

    async def stream_chat(self, prompt: SessionState):
        """Yields token strings as they are generated."""
        suppressing = False
        async for event in self.graph.astream_events(prompt, version="v2"):
            checkpoint = event.get("metadata", {}).get("langgraph_checkpoint_ns", "")
            match event["event"]:
                case "on_chat_model_stream":
                    if not suppressing and "run_agent" in checkpoint:
                        chunk = cast(AIMessageChunk, event["data"].get("chunk"))
                        if chunk.content:
                            yield {"type": "text", "content": chunk.content}
                        elif chunk.additional_kwargs.get("reasoning_content"):
                            yield {
                                "type": "reason",
                                "content": chunk.additional_kwargs.get(
                                    "reasoning_content"
                                ),
                            }
                case "on_tool_start":
                    tool_name = event["name"]
                    match tool_name:
                        case "get_user_info":
                            yield {
                                "type": "tool",
                                "content": "fetching user information...",
                            }
                        case "get_user_location":
                            yield {
                                "type": "tool",
                                "content": "fetching user location...",
                            }
                        case "get_current_time":
                            yield {
                                "type": "tool",
                                "content": "fetching user local time",
                            }
                        case "get_time_and_location":
                            yield {
                                "type": "tool",
                                "content": "fetching user location and time...",
                            }
                        case "web_search":
                            yield {"type": "tool", "content": "searching the web..."}
                        case "find_related_sessions":
                            suppressing = True
                            yield {
                                "type": "tool",
                                "content": "searching for related chats...",
                            }
                        case "save_insight_about_user":
                            yield {
                                "type": "tool",
                                "content": "updating user memory...",
                            }
                        case "remove_insight_about_user":
                            yield {
                                "type": "tool",
                                "content": "updating user memory...",
                            }
                case "on_tool_end":
                    if event["name"] == "find_related_sessions":
                        suppressing = False
                    yield {"type": "tool_end", "content": ""}

    # TODO: Add the source of the code and also the lines or something of the file.
    #
    def load_document(self, files: list[File]) -> list[Document]:
        loaders = {
            ".pdf": PyPDFLoader,
            ".docx": Docx2txtLoader,
            ".html": UnstructuredHTMLLoader,
        }

        plain_text_exts = {".txt", ".yaml", ".yml", ".toml", ".json", ".csv", ".md"}

        language_map = {
            ".go": Language.GO,
            ".py": Language.PYTHON,
            ".java": Language.JAVA,
            ".js": Language.JS,
            ".rs": Language.RUST,
            ".ts": Language.TS,
        }

        def get_splitter(ext: str) -> RecursiveCharacterTextSplitter:
            lang = language_map.get(ext)
            if lang:
                return RecursiveCharacterTextSplitter.from_language(
                    language=lang, chunk_size=1024, chunk_overlap=100
                )
            return RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=50)

        chunks: list[Document] = []
        for file in files:
            ext = Path(file["name"]).suffix.lower()
            loader = loaders.get(ext) or (TextLoader if ext in language_map else None)
            if not loader:
                raise ValueError(f"Unsupported file type: {ext}")
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                tmp.write(base64.b64decode(file["file"]))
                tmp_path = tmp.name

            try:
                lang = language_map.get(ext)
                if lang:
                    loader = 
                docs = loader(tmp_path).load()
                splitter = get_splitter(ext)
                chunks.extend(splitter.split_documents(docs))
            finally:
                os.unlink(tmp_path)

        return chunks

    async def embed_and_store_chunks(self, session_uid: str, chunks: list[Document]):
        if len(chunks) > 0:
            await self.qdrant_client.embed_chunks(session_uid, chunks)

    def log_llm_response(self, response, label: str = "LLM"):
        reasoning = response[-1].additional_kwargs.get("reasoning_content", None)
        content = response[-1].content
        metadata = response[-1].response_metadata

        if reasoning:
            thoughts = []
            tools_to_call = []
            tools = []
            for thought in reversed(response):
                if isinstance(thought, HumanMessage):
                    break

                elif isinstance(thought, ToolMessage):
                    tools.append((thought.name, thought.content))
                    continue

                elif isinstance(thought, AIMessage):
                    reason = thought.additional_kwargs.get("reasoning_content", None)
                    calls = thought.tool_calls
                    if len(calls) > 0:
                        for call in calls:
                            tools_to_call.append((call["name"], call["args"]))
                    if reason:
                        thoughts.append(reason)

            logging.info(f"[{label}] THINKING: \n{'\n'.join(reversed(thoughts))}")

            logging.info(
                f"[{label}] TOOLS CALLED: \n{'\n'.join(f'{tool[0]}: \n{"\n".join(f"{param} -> {arg}" for param, arg in tool[1].items())}' for tool in tools_to_call)}"
            )
            logging.info(
                f"[{label}] TOOLS RESPONSE: \n{'\n'.join(f'{name} -> {resp}' for name, resp in tools)}"
            )

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

    def generate_title(self, content: str) -> str:
        prompt = (
            "Generate a title for a chat session not more than 5 words using the user first input. Your response should be the title ONLY (one title) without the string quote or any tags an example is (Explaining Docker Compose) "
            + content
        )
        title = "Untitled Session"

        try:
            response = self.no_reason.invoke(prompt)
            self.log_llm_response([response], "TITLEGEN")
            if isinstance(response.content, str):
                title = response.content
        except Exception as e:
            logging.error(f"Failed to generate title -> {e}")
        return title

    def summarize_messages(self, messages: list[Message]) -> str | None:
        conversation = "\n".join(f"{m['role']}: {m['content']}" for m in messages)

        prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(
                    content="Summarize the following conversation concisely, preserving key facts and context."
                ),
                HumanMessage(content=conversation),
            ]
        )

        chain = prompt | self.no_reason
        response = chain.invoke({})
        self.log_llm_response([response], "SUMMARIZER")
        if isinstance(response.content, str):
            return response.content

        return None


MODEL: Optional[Model] = None


def get_model() -> Model:
    if MODEL is None:
        raise RuntimeError("Failed to initialize the model")
    return MODEL


def create_model(
    llm_no_reason: ChatOllama,
    llm_reason: ChatOllama,
    tool: list[BaseTool],
    prompt: SystemMessage,
    qdrant_client: Qdrant,
) -> Model:
    return Model(llm_no_reason, llm_reason, tool, prompt, qdrant_client)
