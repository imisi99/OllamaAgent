This file is a merged representation of the entire codebase, combined into a single document by Repomix.

# File Summary

## Purpose
This file contains a packed representation of the entire repository's contents.
It is designed to be easily consumable by AI systems for analysis, code review,
or other automated processes.

## File Format
The content is organized as follows:
1. This summary section
2. Repository information
3. Directory structure
4. Repository files (if enabled)
5. Multiple file entries, each consisting of:
  a. A header with the file path (## File: path/to/file)
  b. The full contents of the file in a code block

## Usage Guidelines
- This file should be treated as read-only. Any changes should be made to the
  original repository files, not this packed version.
- When processing this file, use the file path to distinguish
  between different files in the repository.
- Be aware that this file may contain sensitive information. Handle it with
  the same level of security as you would the original repository.

## Notes
- Some files may have been excluded based on .gitignore rules and Repomix's configuration
- Binary files are not included in this packed representation. Please refer to the Repository Structure section for a complete list of file paths, including binary files
- Files matching patterns in .gitignore are excluded
- Files matching default ignore patterns are excluded
- Files are sorted by Git change count (files with more changes are at the bottom)

# Directory Structure
```
app/
  app.py
  server.py
core/
  agent.py
  mongo.py
  prompt.py
  redis.py
  tools.py
db/
  mongo.py
  qdrant.py
  redis.py
schemas/
  agent.py
  mongo.py
searxng/
  settings.yml
.gitignore
docker-compose.yml
Dockerfile.app
Dockerfile.server
LICENSE
main.py
README.md
requirements.txt
```

# Files

## File: searxng/settings.yml
```yaml
use_default_setting: true

server:
  secret_key: "${SEARXNG_SECRET_KEY}"
  limiter: false
  image_proxy: false

search:
  formats:
    - html
    - json

engines:
  - name: google
    engine: google
    disabled: false
  - name: bing
    engine: bing
    disabled: false
  - name: duckduckgo
    engine: duckduckgo
    disabled: false
```

## File: app/server.py
```python
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from core.agent import get_graph, get_llm
from schemas.agent import SessionConversation, SessionState
from db.mongo import get_mongo_database

serve = APIRouter()


@serve.post("/agent/chat")
async def chat_agent(input: SessionConversation):
    db = get_mongo_database()
    if input["session_id"] == "":
        db.create_session({"messages": [], "created_at": datetime.now(), "name": ""})

    session = SessionState(
        {
            "llm": get_llm(),
            "message": input["message"],
            "session_id": input["session_id"],
            "response": "",
        }
    )
    response = await get_graph().ainvoke(session)

    return JSONResponse(status_code=200, content={"msg": response["response"]})


@serve.post("session/create")
async def create_session(input: SessionConversation):
    db = get_mongo_database()

    prompt = (
        "Generate a casual title for a chat session not more than 5 words using the user first input. You respond should be the title ONLY (one title) \n\n\n"
        + input["message"]["content"]
    )

    response = get_llm().invoke(prompt)
    title = "The LLM did a bad job"

    if isinstance(response.content, str):
        title = response.content

    created, id = db.create_session(
        {"messages": [], "created_at": datetime.now(), "name": title}
    )

    if not created:
        raise HTTPException(
            status_code=500, detail={"msg": "Failed to create the session."}
        )

    return JSONResponse(status_code=200, content={"id": id, "msg": "Success."})
```

## File: .gitignore
```
# Byte-compiled / optimized / DLL files
__pycache__/
*.py[codz]
*$py.class

# C extensions
*.so

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# PyInstaller
#  Usually these files are written by a python script from a template
#  before PyInstaller builds the exe, so as to inject date/other infos into it.
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt

# Unit test / coverage reports
htmlcov/
.tox/
.nox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.py.cover
.hypothesis/
.pytest_cache/
cover/

# Translations
*.mo
*.pot

# Django stuff:
*.log
local_settings.py
db.sqlite3
db.sqlite3-journal

# Flask stuff:
instance/
.webassets-cache

# Scrapy stuff:
.scrapy

# Sphinx documentation
docs/_build/

# PyBuilder
.pybuilder/
target/

# Jupyter Notebook
.ipynb_checkpoints

# IPython
profile_default/
ipython_config.py

# pyenv
#   For a library or package, you might want to ignore these files since the code is
#   intended to run in multiple environments; otherwise, check them in:
# .python-version

# pipenv
#   According to pypa/pipenv#598, it is recommended to include Pipfile.lock in version control.
#   However, in case of collaboration, if having platform-specific dependencies or dependencies
#   having no cross-platform support, pipenv may install dependencies that don't work, or not
#   install all needed dependencies.
#Pipfile.lock

# UV
#   Similar to Pipfile.lock, it is generally recommended to include uv.lock in version control.
#   This is especially recommended for binary packages to ensure reproducibility, and is more
#   commonly ignored for libraries.
#uv.lock

# poetry
#   Similar to Pipfile.lock, it is generally recommended to include poetry.lock in version control.
#   This is especially recommended for binary packages to ensure reproducibility, and is more
#   commonly ignored for libraries.
#   https://python-poetry.org/docs/basic-usage/#commit-your-poetrylock-file-to-version-control
#poetry.lock
#poetry.toml

# pdm
#   Similar to Pipfile.lock, it is generally recommended to include pdm.lock in version control.
#   pdm recommends including project-wide configuration in pdm.toml, but excluding .pdm-python.
#   https://pdm-project.org/en/latest/usage/project/#working-with-version-control
#pdm.lock
#pdm.toml
.pdm-python
.pdm-build/

# pixi
#   Similar to Pipfile.lock, it is generally recommended to include pixi.lock in version control.
#pixi.lock
#   Pixi creates a virtual environment in the .pixi directory, just like venv module creates one
#   in the .venv directory. It is recommended not to include this directory in version control.
.pixi

# PEP 582; used by e.g. github.com/David-OConnor/pyflow and github.com/pdm-project/pdm
__pypackages__/

# Celery stuff
celerybeat-schedule
celerybeat.pid

# SageMath parsed files
*.sage.py

# Environments
.env
.envrc
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# Spyder project settings
.spyderproject
.spyproject

# Rope project settings
.ropeproject

# mkdocs documentation
/site

# mypy
.mypy_cache/
.dmypy.json
dmypy.json

# Pyre type checker
.pyre/

# pytype static type analyzer
.pytype/

# Cython debug symbols
cython_debug/

# PyCharm
#  JetBrains specific template is maintained in a separate JetBrains.gitignore that can
#  be found at https://github.com/github/gitignore/blob/main/Global/JetBrains.gitignore
#  and can be added to the global gitignore or merged into this file.  For a more nuclear
#  option (not recommended) you can uncomment the following to ignore the entire idea folder.
#.idea/

# Abstra
# Abstra is an AI-powered process automation framework.
# Ignore directories containing user credentials, local state, and settings.
# Learn more at https://abstra.io/docs
.abstra/

# Visual Studio Code
#  Visual Studio Code specific template is maintained in a separate VisualStudioCode.gitignore 
#  that can be found at https://github.com/github/gitignore/blob/main/Global/VisualStudioCode.gitignore
#  and can be added to the global gitignore or merged into this file. However, if you prefer, 
#  you could uncomment the following to ignore the entire vscode folder
# .vscode/

# Ruff stuff:
.ruff_cache/

# PyPI configuration file
.pypirc

# Cursor
#  Cursor is an AI-powered code editor. `.cursorignore` specifies files/directories to
#  exclude from AI features like autocomplete and code analysis. Recommended for sensitive data
#  refer to https://docs.cursor.com/context/ignore-files
.cursorignore
.cursorindexingignore

# Marimo
marimo/_static/
marimo/_lsp/
__marimo__/
```

## File: Dockerfile.app
```
FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir streamlit==1.51.0

COPY /app/app.py .

EXPOSE 8501

CMD [ "streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

## File: Dockerfile.server
```
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD [ "uvicorn", "main:app", "--host", " 0.0.0.0", "--port", "8000" ]
```

## File: LICENSE
```
MIT License

Copyright (c) 2026 Imisioluwa Isong

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## File: README.md
```markdown
# OllamaAgent
```

## File: db/qdrant.py
```python
import logging
import os
from typing import Optional
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

QDRANT_CLIENT: Optional[QdrantClient] = None
VECTORSIZE = 768
QDRANT_HOST = os.getenv("QDRANT_HOST")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "0"))


def connect_qdrant() -> QdrantClient:
    """Connects and returns a qdrant connection client"""
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    return client


def ensure_collections():
    collections = get_qdrant_client().get_collections().collections
    existing = {c.name for c in collections}

    if "projects" not in existing:
        logging.info("[QDRANT] Creating the projects collection  as it didn't exist.")
        try:
            get_qdrant_client().create_collection(
                collection_name="projects",
                vectors_config={
                    "readme": VectorParams(
                        size=VECTORSIZE, distance=Distance.COSINE
                    )  # Might have to add some other vector later on
                },
            )

            logging.info("[QDRANT] Projects collection created.")
        except Exception as e:
            logging.error("[QDRANT] Failed to create the projects collection -> %s", e)
            raise


def get_qdrant_client() -> QdrantClient:
    """Returns a pre-initialized qdrant client"""
    if QDRANT_CLIENT is None:
        raise RuntimeError("Qdrant client is not initialized.")
    return QDRANT_CLIENT
```

## File: schemas/agent.py
```python
from typing import TypedDict

from langchain_ollama import ChatOllama
from .mongo import Message


class SessionConversation(TypedDict):
    session_id: str
    message: Message


class SessionState(SessionConversation):
    llm: ChatOllama
    response: str
```

## File: schemas/mongo.py
```python
from datetime import datetime
from typing import Any, TypedDict


class Message(TypedDict):
    role: str
    content: str
    timestamp: datetime


class Session(TypedDict):
    name: str
    created_at: datetime
    messages: list[Message]


class User(TypedDict):
    name: str
    memory: dict[str, Any]
```

## File: requirements.txt
```
fastapi==0.121.2
langgraph==1.0.10
langchain==1.2.10
langchain-core==1.2.17
langchain-ollama==1.0.1
pymongo==4.16.0
qdrant-client==1.16.2
redis==7.3.0
uvicorn==0.40.0
```

## File: core/agent.py
```python
import logging
from typing import Optional
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
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
                    "timestamp": datetime.now(),
                },
            )
        return state

    def run_agent(state: SessionState) -> SessionState:
        session_id = state["session_id"]
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

        response = agent.invoke(
            {"session_id": state["session_id"], "messages": messages}
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
```

## File: core/prompt.py
```python
from langchain_core.messages import SystemMessage


system_prompt = SystemMessage(
    content="""
        <identity>
        You are an elite personal AI agent built exclusively for your user — a backend software engineer
        with deep expertise in Go, Python, FastAPI, PostgreSQL, Redis, Docker, and gRPC, and an active
        interest in ML infrastructure, vector embeddings, and distributed systems.

        You run locally on the user's machine via Ollama. You are not a generic assistant — you are a
        personalized engineering partner with persistent memory, access to the filesystem, and deep
        familiarity with their ongoing projects. You think like a senior engineer, not a help desk.
        </identity>

        <persona>
        - You are direct, confident, and concise. You don't over-explain things they already know.
        - You adapt your depth to the complexity of the question — quick answers for quick questions,
        thorough breakdowns when the problem warrants it.
        - You don't pad responses with disclaimers, caveats, or unnecessary preamble. Get to the point.
        - You treat the user as a peer, not a beginner. You can use technical shorthand freely.
        - When you are uncertain about something, say so clearly rather than hallucinating.
        - You have a personality — you're allowed to be direct, occasionally opinionated, and technically
        enthusiastic. You are not robotic.
        </persona>

        <core_capabilities>
        You are capable of helping with the following and should proactively use the right tool for
        each task without being asked:

        1. **Code & Engineering**
        - Writing, reviewing, debugging, and refactoring code across Go, Python, Bash, SQL, and more.
        - Designing APIs, data models, system architectures, and infrastructure.
        - Explaining complex technical concepts clearly and accurately.
        - Reviewing code for correctness, performance, security, and idiomatic style.

        2. **Project Assistance**
        - Deeply familiar with the user's active projects (see <projects> section).
        - Can reason about architecture decisions and tradeoffs in context of their actual stack.
        - Can help brainstorm, plan, and break down new project ideas into actionable steps.

        3. **Filesystem & Local Context** (when file tools are available)
        - Can browse, read, and reason about files on the user's machine.
        - When asked to look at a file or directory, use the appropriate tool — don't ask for
            the content to be pasted manually if you can access it directly.
        - Never modify or delete files without explicit confirmation.

        4. **Memory & Personalization**
        - You maintain memory across sessions via persistent storage (MongoDB + Redis).
        - Use `get_user_info` to recall things you've previously learned about the user before
            answering questions where past context is relevant (preferences, decisions, project state).
        - Use `save_insight_about_user` proactively when you learn something significant:
            a new preference, a key architectural decision, a project milestone, a tool they've adopted,
            or a personal detail worth remembering. Don't ask permission — just save it.
        - When referencing past memory, be natural about it. Don't announce "I retrieved your memory."
            Just use the information.

        5. **Vector Search & Semantic Context** (when Qdrant tools are available)
        - In future: use vector embeddings to semantically search across all of the user's
            project codebases, notes, and documentation to provide deeply contextual answers.
        - Treat Qdrant as a long-term semantic memory layer — not just a database.
        </core_capabilities>

        <projects>
        These are the user's known active and past projects. Use this as background context:

        **OllamaAgent** (this system — current)
        - Personal AI agent running locally via Ollama.
        - Stack: FastAPI backend, Streamlit UI, LangGraph ReAct agent, MongoDB (session persistence),
        Redis (short-term memory / summarization buffer), Qdrant (vector store, future use).
        - Model: qwen2.5-coder via Ollama.
        - Key architecture: outer StateGraph (maybe_summarize → update_memory → run_agent) wrapping
        an inner LangChain ReAct agent. Memory is managed in Redis with a 15-message rolling window
        that summarizes when exceeded.
        - Future roadmap: filesystem browsing tools, vector embedding of all projects, semantic search
        over personal knowledge base.

        **FindMe** (prior — Go, production)
        - Platform for connecting users with collaborative projects.
        - Stack: Go, PostgreSQL, Redis, Docker Compose, Nginx, Let's Encrypt SSL, Oracle Cloud ARM VPS.
        - Key subsystems: Paystack payment integration (webhooks, HMAC-SHA512, cron reminders),
        gRPC ML service (Python, Ollama nomic-embed-text, Qdrant named vectors), GitHub OAuth,
        Redis cache-aside pattern.
        - Status: deployed and running.
        </projects>

        <technical_profile>
        The user's stack and preferences — factor this into every response:

        - **Primary languages**: Go (production APIs), Python (ML, scripting, agents)
        - **Databases**: PostgreSQL (primary), MongoDB (document store), Redis (cache/queue)
        - **Infrastructure**: Docker, Docker Compose, Nginx, Oracle Cloud ARM (free tier)
        - **ML/AI**: Ollama (local inference), nomic-embed-text (embeddings), Qdrant (vector search),
        LangChain, LangGraph, FastAPI
        - **OS**: Pop!_OS Linux (primary), dual-boot Windows 11, Victus 15 laptop
        - **Editor workflow**: Neovim with LazyVim, terminal-first
        - **Preferred style**:
        - Go: idiomatic, minimal abstractions, explicit error handling
        - Python: typed (TypedDict, dataclasses), clean separation of concerns
        - SQL: raw queries preferred over heavy ORM magic
        - APIs: RESTful with clear contracts; gRPC for internal services
        - **Personality of their code**: production-grade, not throwaway — they care about correctness,
        observability (logging), and clean architecture even in personal projects.
        </technical_profile>

        <memory_protocol>
        You have two tools for managing memory:

        `get_user_info(user_id)` — retrieves the persistent memory dict for the user.
        `save_insight_about_user(user_id, key, value)` — stores a key-value insight.

        **When to call `get_user_info`:**
        - At the start of conversations where context about past decisions, preferences, or project
        state would meaningfully improve your response.
        - When answering questions about ongoing projects, personal preferences, or anything that
        might have been discussed before.

        **When to call `save_insight_about_user`:**
        - When the user makes a significant architectural or technical decision.
        - When they express a clear preference ("I prefer X over Y", "I've switched to Z").
        - When they mention a new project, idea, or tool they're adopting.
        - When something important about their context changes (new job, new machine, new stack).
        - When they share a personal detail that would be useful to recall in future sessions.

        **Keys to use** (be consistent so memory is queryable):
        - `projects.<name>.status` — current state of a project
        - `projects.<name>.stack` — tech decisions
        - `projects.<name>.notes` — important decisions or context
        - `preferences.languages` — language preferences
        - `preferences.tools` — tool preferences
        - `preferences.style` — code style preferences
        - `personal.<key>` — personal details
        - `goals.<key>` — goals and aspirations
        - `insights.<key>` — anything else worth remembering

        Do not ask for permission before saving. If something is clearly worth remembering, save it.
        </memory_protocol>

        <tool_use_guidelines>
        You are a ReAct agent. You have access to tools and should use them autonomously to fulfill
        requests. Follow these principles:

        1. **Think before acting.** For multi-step tasks, reason about the full plan before executing
        the first tool call. Consider what could go wrong and how to handle it.

        2. **Use the right tool for the job.** Don't ask the user to paste file contents if you
        can read the file directly. Don't ask for context that's already in memory.

        3. **Be decisive.** If you have enough information to proceed, proceed. Don't ask clarifying
        questions for things you can reasonably infer.

        4. **Confirm before destructive actions.** Never delete files, overwrite data, or make
        irreversible changes without explicit confirmation.

        5. **Report tool failures clearly.** If a tool fails or returns unexpected output, say so
        and explain what you tried and what went wrong. Don't silently retry in loops.

        6. **Chain tools efficiently.** When a task requires multiple steps, plan the full sequence
        and execute it without unnecessary back-and-forth.
        </tool_use_guidelines>

        <response_format>
        - **Default**: Clean prose or code. No unnecessary headers or bullet forests.
        - **Code**: Always use fenced code blocks with the correct language identifier.
        - **For architecture / system design**: A brief prose explanation followed by a structured
        breakdown is fine. Don't over-format simple answers.
        - **For debugging**: State your hypothesis first, then show the fix, then briefly explain why.
        - **For comparisons**: A concise table is acceptable when options are genuinely parallel.
        - **Length**: Match the complexity of the question. A one-liner question gets a concise answer.
        A deep architectural question gets a thorough response. Never pad.
        - **Never start a response with**: "Certainly!", "Of course!", "Great question!", "Sure!",
        or any other filler affirmation. Start with the actual answer.
        </response_format>

        <coding_standards>
        When writing or reviewing code, adhere to these standards:

        **Go:**
        - Follow standard Go idioms (errors as values, no panic in library code, table-driven tests)
        - Use `fmt.Errorf("context: %w", err)` for error wrapping
        - Prefer explicit over clever
        - Use struct embedding sparingly and intentionally
        - Always handle the error return from `defer` calls if it matters

        **Python:**
        - Use type hints everywhere — `TypedDict` for structured dicts, dataclasses or Pydantic for models
        - Prefer `async`/`await` consistently — don't mix sync and async carelessly
        - Use `logging` not `print` in production code
        - FastAPI: use dependency injection, lifespan context managers, and proper status codes
        - LangChain/LangGraph: keep node functions pure where possible — side effects go in dedicated nodes

        **General:**
        - When suggesting a fix, show the full corrected block, not just the changed line in isolation
        - When introducing a new pattern or library, briefly explain *why* it's the right choice here
        - Flag potential performance issues or security concerns proactively, even if not asked
        </coding_standards>

        <known_context>
        Additional context about the user that should inform your responses:

        - They run a dual-boot setup: Pop!_OS Linux as primary, Windows 11 secondary. Default to Linux
        for all system-level advice unless they specify otherwise.
        - They are comfortable with terminal workflows — prefer CLI solutions over GUI when both exist.
        - They have an Oracle Cloud Always Free ARM tier VPS running FindMe in production.
        - They use Docker Compose for local dev and production deployments.
        - They are a beginner guitarist (Squier Starcaster, learning via Justin Guitar) — this is
        personal context, not technical.
        - They have interest in ML infrastructure beyond just using models: embedding pipelines,
        vector search internals (HNSW), re-ranking (cross-encoders, ColBERT), GNNs.
        - They have studied algorithms actively: Bellman-Ford, Dijkstra, topological sort, greedy
        algorithms, DFS/BFS graph traversal — they can follow algorithmic reasoning.
        - They value understanding the *why* behind solutions, not just the how. When a concept
        has a non-obvious reason behind it, explain it.
        </known_context>

        <boundaries>
        - Do not make up APIs, function signatures, or library behavior you're not confident about.
        Say "I'm not sure, let me reason through this" or "you should verify this in the docs."
        - Do not hallucinate file contents — if you haven't read a file, say so.
        - Do not be sycophantic. If the user's approach has a problem, say so directly and explain why.
        - Do not over-caveat. The user is a professional. Trust them to handle nuanced information.
        </boundaries>
    """
)
```

## File: core/redis.py
```python
import json
from db import redis
from schemas.mongo import Message


def add_short_term_memory(session_id: str, message: Message):
    redis.get_redis_client().rpush(session_id, json.dumps(message))


def get_short_term_memory(session_id: str) -> list[Message]:
    msg = redis.get_redis_client().lrange(session_id, 0, -1)

    if isinstance(msg, list):
        return [json.loads(m) for m in msg]
    else:
        raise RuntimeError("Got an async response expected sync redis client")


def clear_short_term_memory(session_id: str):
    redis.get_redis_client().delete(session_id)
```

## File: db/redis.py
```python
import os
from typing import Optional
import redis

REDIS_HOST = os.getenv("REDIS_HOST", "")
REDIS_PORT = int(os.getenv("REDIS_PORT", "0"))
REDIS_PASS = os.getenv("REDIS_PASS", "")
REDIS_CLIENT: Optional[redis.Redis] = None


def connect_redis() -> redis.Redis:
    """Connect and returns a redis connection client"""
    client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASS)
    return client


def get_redis_client() -> redis.Redis:
    """Returns a pre-initialized redis client"""
    if REDIS_CLIENT is None:
        raise RuntimeError("Redis client is not initialized")
    return REDIS_CLIENT
```

## File: core/mongo.py
```python
from typing import Any, cast
from bson import ObjectId
from pymongo import MongoClient
from schemas.mongo import Message, Session, User


class Database:
    def __init__(
        self, db: str, session: str, user: str, client: MongoClient[dict[str, Any]]
    ) -> None:
        self.db = db
        self.session = session
        self.user = user
        self.client = client
        self.session_collection = self.client[self.db][self.session]
        self.user_collection = self.client[self.db][self.user]

    def create_session(self, session: Session) -> tuple[bool, str]:
        result = self.session_collection.insert_one(
            {
                "name": session["name"],
                "created_at": session["created_at"],
                "messages": session["messages"],
            }
        )
        if not result.acknowledged:
            return False, ""

        return True, str(result.inserted_id)

    def fetch_session(self, session_id: str) -> Session | None:
        result = self.session_collection.find_one({"_id": ObjectId(session_id)})
        if result is not None:
            if not all(k in result for k in ("name", "created_at", "messages")):
                return None
            return cast(Session, result)
        return None

    def fetch_all_session(self) -> list[Session] | None:
        sessions = []

        with self.session_collection.find() as cursor:
            for doc in cursor:
                sessions.append(doc)

        return sessions

    def add_messages(self, session_id: str, message: Message) -> bool:
        result = self.session_collection.update_one(
            {"_id": ObjectId(session_id)}, {"$push": {"messages": message}}
        )

        return result.acknowledged

    def delete_session(self, session_id: str) -> bool:
        result = self.session_collection.delete_one({"_id": ObjectId(session_id)})

        return result.acknowledged

    def fetch_user(self, user_id: str) -> User | None:
        result = self.user_collection.find_one({"_id": ObjectId(user_id)})
        if result is not None:
            if not all(k in result for k in ("name", "memory")):
                return None
            return cast(User, result)

        return None

    def update_user_memory(self, user_id: str, key: str, value: Any) -> bool:
        result = self.user_collection.update_one(
            {"_id": ObjectId(user_id)}, {"$set": {f"memory.{key}": value}}
        )

        return result.acknowledged
```

## File: core/tools.py
```python
import json
import httpx
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


@tool(parse_docstring=True)
def web_search(query: str, max_results: int = 5) -> list[dict]:
    """
    This make a web search using the query and max results (The max results defaults to 5)

    Args:
        query: The search query to use for the web search
        max_results: The maximum number of contents to return from the web search
    """
    resp = httpx.get(
        "http://searxng:8080/search",
        params={"q": query, "format": "json", "engines": "google,bing,duckduckgo"},
    )

    results = resp.json().get("results", [])
    return [
        {"title": r["title"], "url": r["url"], "content": r.get("content", "")}
        for r in results[:max_results]
    ]


tools = [get_user_info, save_insight_about_user, web_search]
```

## File: db/mongo.py
```python
import os
from typing import Dict, Optional, Any
from pymongo import MongoClient

from core.mongo import Database
from schemas.mongo import Session


MONGO_CLIENT: Optional[MongoClient[Dict[str, Any]]] = None
MONGO_HOST = os.getenv("MONGO_HOST")
MONGO_PORT = os.getenv("MONGO_PORT")
DB_NAME = "agent"
SESSISON = "sessions"
USER = "user"
MONGO_DATABASE: Optional[Database] = None


def connect_mongo() -> MongoClient[Session]:
    """Connects and returns a mongo connection client"""
    username = os.getenv("MONGO_USERNAME")
    password = os.getenv("MONGO_PASSWORD")
    uri = f"mongodb://{username}:{password}@{MONGO_HOST}:{MONGO_PORT}/?authSource=admin"

    client = MongoClient(uri)
    return client


def get_mongo_client() -> MongoClient[Dict[str, Any]]:
    """Returns a pre-initialized mongo client"""
    if MONGO_CLIENT is None:
        raise RuntimeError("[MONGO] Mongo client is not initialized.")
    return MONGO_CLIENT


def create_mongo_database() -> Database:
    database = Database(DB_NAME, SESSISON, USER, get_mongo_client())
    return database


def get_mongo_database() -> Database:
    if MONGO_DATABASE is None:
        raise RuntimeError("[MONGO] Mongo database is not initialized.")
    return MONGO_DATABASE
```

## File: docker-compose.yml
```yaml
services:
  search:
    image: searxng/searxng:2026.3.12-3d3a78f3a
    container_name: agent_search
    restart: always
    ports:
      - "9090:8080"
    environment:
      - SEARXNG_BASE_URL=${SEARXNG_BASE_URL}
      - SEARXNG_SECRET_KEY=${SEARXNG_SECRET_KEY}
    volumes:
      - ./searxng:/etc/searxng
  qdrant:
    image: qdrant/qdrant:v1.16.3
    container_name: agent_qdrant
    restart: always
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant:/qdrant/storage
    healthcheck:
      test:
        [
          "CMD",
          "bash",
          "-c",
          "exec 3<>/dev/tcp/127.0.0.1/6333 && echo -e 'GET /readyz HTTP/1.1\\r\\nHost: localhost\\r\\nConnection: close\\r\\n\\r\\n' >&3 && grep -q 'HTTP/1.1 200' <&3",
        ]
      interval: 10s
      timeout: 3s
      retries: 3
      start_period: 10s
    networks:
      - agent-shared-network
  mongo:
    image: mongo:8.2.6-rc0
    container_name: agent_mongo
    restart: always
    ports:
      - "27017:27017"
    environment:
      - MONGO_INITDB_ROOT_USERNAME=${MONGO_USERNAME}
      - MONGO_INITDB_ROOT_PASSWORD=${MONGO_PASSWORD}
    volumes:
      - mongodb-data:/data/db
    healthcheck:
      test:
        [
          "CMD",
          "mongosh",
          "--eval",
          "db.adminCommand('ping')",
          "--username",
          "${MONGO_USERNAME}",
          "--password",
          "${MONGO_PASSWORD}",
          "--authenticationDatabase",
          "admin",
        ]
      interval: 10s
      timeout: 5s
      retries: 2
      start_period: 15s
    networks:
      - agent-shared-network
  redis:
    image: redis:8.2.3
    container_name: agent_redis
    restart: always
    command:
      [
        "redis-server",
        "--appendonly",
        "yes",
        "--requirepass",
        "${REDIS_PASS}",
        "--maxmemory",
        "50mb",
        "--maxmemory-policy",
        "volatile-ttl",
      ]
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/redis/storage
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5
    networks:
      - agent-shared-network
  server:
    build:
      context: .
      dockerfile: Dockerfile.server
    container_name: agent_server
    restart: no
    extra_hosts:
      - "host.docker.internal:host-gateway"
    environment:
      - MONGO_USERNAME=${MONGO_USERNAME}
      - REDIS_HOST=${REDIS_HOST}
      - REDIS_PORT=${REDIS_PORT}
      - REDIS_PASS=${REDIS_PASS}
      - QDRANT_HOST=${QDRANT_HOST}
      - QDRANT_PORT=${QDRANT_PORT}
      - MONGO_HOST=${MONGO_HOST}
      - MONGO_PORT=${MONGO_PORT}
      - MONGO_PASSWORD=${MONGO_PASSWORD}
      - OLLAMA_BASE_URL=${OLLAMA_BASE_URL}
    # depends_on:
    #   mongo:
    #     condition: service_healthy
    #   redis:
    #     condition: service_healthy
    # healthcheck:
    #   test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    #   interval: 10s
    #   timeout: 5s
    #   retries: 4
    networks:
      - agent-shared-network
  app:
    build:
      context: .
      dockerfile: Dockerfile.app
    container_name: agent_app
    restart: always
    # depends_on:
    #   server:
    #     condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8501/_stcore/health"]
      interval: 10s
      timeout: 5s
      retries: 4
    networks:
      - agent-shared-network
networks:
  agent-shared-network:
    external: true

volumes:
  qdrant:
  mongodb-data:
  redis-data:
```

## File: main.py
```python
import logging
import os
from langchain_ollama import ChatOllama
from contextlib import asynccontextmanager
from fastapi import FastAPI
from core.tools import tools
from core.prompt import system_prompt
from db import mongo, qdrant, redis
from core import agent
from app.server import serve

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan for app"""
    try:
        qdrant.QDRANT_CLIENT = qdrant.connect_qdrant()
        qdrant.ensure_collections()
        mongo.MONGO_CLIENT = mongo.connect_mongo()
        redis.REDIS_CLIENT = redis.connect_redis()

        mongo.MONGO_DATABASE = mongo.create_mongo_database()

        OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "")

        agent.LLM = ChatOllama(model="qwen2.5-coder", base_url=OLLAMA_BASE_URL)
        agent_graph = agent.build_agent(agent.LLM, tools, system_prompt)
        agent.GRAPH = agent.build_graph(agent_graph)

    except Exception as e:
        logging.error(
            "An error occured while trying startup app -> %s", e, exc_info=True
        )
    yield
    qdrant.QDRANT_CLIENT.close() if qdrant.QDRANT_CLIENT is not None else qdrant.QDRANT_CLIENT
    mongo.MONGO_CLIENT.close() if mongo.MONGO_CLIENT is not None else mongo.MONGO_CLIENT
    redis.REDIS_CLIENT.close() if redis.REDIS_CLIENT is not None else redis.REDIS_CLIENT


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(serve)
```

## File: app/app.py
```python
import random
import streamlit as st

st.header(":red[Ollama] :grey[_Agent_]", divider="grey", width="content")

chat_holders = [
    "What's on your mind ?",
    "How can i help you today ?",
    "Hey Imisioluwa",
    "Back at it again !",
]

with st.sidebar:
    if st.button("+ New Chat"):
        st.session_state.session_id = ""
        st.session_state.messages = [{"role": "assistant", "content": "yeah"}]
        st.session_state.chat_holder = random.randint(0, len(chat_holders) - 1)
        st.rerun()

    sessions = [{"name": "stuff", "id": "stuff"}]
    for session in sessions:
        if st.button(session["name"], key=session["id"]):
            st.session_state.session_id = ""
            st.session_state.chat_holder = -1
            st.session_state.messages = []
            st.rerun()

if "chat_holder" not in st.session_state:
    st.session_state.chat_holder = random.randint(0, len(chat_holders) - 1)

if st.session_state.chat_holder != -1:
    st.subheader(chat_holders[st.session_state.chat_holder])

if "session_id" not in st.session_state:
    st.session_state.session_id = ""
    st.session_state.messages = []

if st.session_state.messages is not None:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

if prompt := st.chat_input("", key="chat", accept_file="multiple"):
    st.session_state.messages.append({"role": "user", "content": prompt.text})
    with st.chat_message("user"):
        st.markdown(prompt.text)

    with st.chat_message("assistant"):
        response = "response"
        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
```
