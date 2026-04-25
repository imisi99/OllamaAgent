import logging
import os
import tempfile
from datetime import datetime
from typing import Optional
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    UnstructuredHTMLLoader,
    UnstructuredMarkdownLoader,
    Docx2txtLoader,
    UnstructuredExcelLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter, Language
from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from langgraph.graph import StateGraph, END
from pathlib import Path
from streamlit.runtime.uploaded_file_manager import UploadedFile
from core.qdrant import Qdrant
from db.redis import get_redis_database
from schemas.agent import SessAgentState, SessionState
from schemas.mongo import Message

# TODO:
# The agent logging for the reasoning doesn't work with tool calls cause reasoning is done then
# The prompt length is a factor causing slow response from the agent (reduce it)
# Add parameters to the agent also like the session id and user id
# Work on the streaming of the response
# Work on adding the files also for the agent
# Add a tool logging procedure also


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
                chunks = self.load_document([])
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
            if len(msg) > 30:
                summarized = self.summarize_messagess(msg)
                if summarized is None:
                    return state
                redDB.clear_short_term_memory(session_id)
                redDB.add_short_term_memory(
                    session_id,
                    {
                        "role": "system",
                        "content": f"SUMMARY: {summarized}",
                        "timestamp": datetime.now().isoformat(),
                        "images": [("", "")],
                        "files": [("", "")],
                    },
                    True,
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

            # TODO: Use a check for the token emitting for streaming messages with a check on the final output if it isn't then redisplay
            response = agent.invoke(
                {
                    "session_id": session_id,
                    "user_id": state["user_id"],
                    "ghost_session": state["ghost_session"],
                    "messages": messages,
                }
            )

            logging.info(response)
            self.log_llm_response(response["messages"], "AGENT")

            get_redis_database().add_short_term_memory(
                session_id,
                {
                    "role": "assistant",
                    "content": response["messages"][-1].content,
                    "timestamp": datetime.now().isoformat(),
                    "images": [("", "")],
                    "files": [("", "")],
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
        return self.graph.invoke(prompt)

    def load_document(self, files: list[tuple[bytes, str]]) -> list[Document]:
        loaders = {
            ".pdf": PyPDFLoader,
            ".docx": Docx2txtLoader,
            ".txt": TextLoader,
            ".md": UnstructuredMarkdownLoader,
            ".html": UnstructuredHTMLLoader,
            ".xlsx": UnstructuredExcelLoader,
        }

        language_map = {
            ".go": Language.GO,
            ".py": Language.PYTHON,
            ".java": Language.JAVA,
            ".js": Language.JS,
            ".rs": Language.RUST,
        }

        def get_splitter(ext: str) -> RecursiveCharacterTextSplitter:
            lang = language_map.get(ext)
            if lang:
                return RecursiveCharacterTextSplitter.from_language(
                    language=lang, chunk_size=512, chunk_overlap=50
                )
            return RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=50)

        chunks: list[Document] = []
        for file, name in files:
            ext = Path(name).suffix.lower()
            loader = loaders.get(ext) or (TextLoader if ext in language_map else None)
            if not loader:
                raise ValueError(f"Unsupported file type: {ext}")
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                tmp.write(file)
                tmp_path = tmp.name

            try:
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
        content = response.content
        metadata = response.response_metadata

        if reasoning:
            thoughts = []
            for thought in reversed(response):
                if isinstance(thought, HumanMessage):
                    break
                reason = thought.additional_kwargs.get("reasoning_content", None)
                if reason:
                    thoughts.append(reason)

            logging.info(f"[{label}] THINKING: \n {'\n'.join(reversed(thoughts))}")

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
            "Generate a title for a chat session not more than 5 words using the user first input. Your response should be the title ONLY (one title) without the string quote or any tags an example is \n Explaining Docker Compose \n \n\n\n"
            + content
        )
        title = "Untitled Session"

        try:
            response = self.no_reason.invoke(prompt)
            self.log_llm_response(response, "TITLEGEN")
            if isinstance(response.content, str):
                title = response.content
        except Exception as e:
            logging.error(f"Failed to generate title -> {e}")
        return title

    def summarize_messagess(self, messages: list[Message]) -> str | None:
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
        self.log_llm_response(response, "SUMMARIZER")
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
