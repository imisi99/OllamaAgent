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
.gitignore
docker-compose.yml
LICENSE
main.py
README.md
```

# Files

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

## File: schemas/agent.py
```python
from typing import TypedDict

from langchain_ollama import ChatOllama
from mongo import Message


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
        You are a helpful assistant and you have access to the following tools 
    """,
)
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

## File: db/redis.py
```python
import os
from typing import Optional
import redis

REDIS_HOST = os.getenv("REDIS_HOST", "")
REDIS_PORT = int(os.getenv("REDIS_PORT", "0"))
REDIS_CLIENT: Optional[redis.Redis] = None


def connect_redis() -> redis.Redis:
    """Connect and returns a redis connection client"""
    client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
    return client


def get_redis_client() -> redis.Redis:
    """Returns a pre-initialized redis client"""
    if REDIS_CLIENT is None:
        raise RuntimeError("Redis client is not initialized")
    return REDIS_CLIENT
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

## File: db/mongo.py
```python
import os
from typing import Dict, Optional, Any
from pymongo import MongoClient

from core.mongo import Database
from schemas.mongo import Session, User


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
```

## File: docker-compose.yml
```yaml
services:
  qdrant:
    image: qdrant/qdrant:v1.16.3
    container_name: agent_qdrant
    restart: always
    ports:
      - "6333:6333"
      - "6334:6334"
    environment:
      - QDRANT__SERVICE__API_KEY=${QDRANT_API_KEY}
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
  app:
    build:
      context: .
      dockerfile: DockerFile
    container_name: agent_app
    restart: always
    environment:
      - MONGO_USERNAME=${MONGO_USERNAME}
    depends_on:
      mongo:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "http://localhost:"]
      interval: 10s
      timeout: 5s
      retries: 5
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
from langchain_ollama import ChatOllama
from contextlib import asynccontextmanager
from fastapi import FastAPI
from core.tools import tools
from core.prompt import system_prompt
from db import mongo, qdrant, redis
from core import agent


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan for app"""
    try:
        qdrant.QDRANT_CLIENT = qdrant.connect_qdrant()
        qdrant.ensure_collections()
        mongo.MONGO_CLIENT = mongo.connect_mongo()
        redis.REDIS_CLIENT = redis.connect_redis()

        mongo.MONGO_DATABASE = mongo.create_mongo_database()

        agent.LLM = ChatOllama(model="qwen2.5-coder")
        agent_graph = agent.build_agent(agent.LLM, tools, system_prompt)
        agent.GRAPH = agent.build_graph(agent_graph)

    except Exception as e:
        logging.error("An error occured while trying startup app -> %s", e)
    yield
    qdrant.QDRANT_CLIENT.close() if qdrant.QDRANT_CLIENT is not None else qdrant.QDRANT_CLIENT
    mongo.MONGO_CLIENT.close() if mongo.MONGO_CLIENT is not None else mongo.MONGO_CLIENT
    redis.REDIS_CLIENT.close() if redis.REDIS_CLIENT is not None else redis.REDIS_CLIENT


app = FastAPI(lifespan=lifespan)
```

## File: app/app.py
```python
import random
import streamlit as st

st.header(":red[Ollama] :rainbow[_Agent_]", divider="grey", width="content")

chat_holders = [
    "What's on your mind ?",
    "How can i help you today ?",
    "Hey Imisioluwa",
    "Back at it again !",
]

st.subheader(chat_holders[random.randint(0, len(chat_holders) - 1)])

if prompt := st.chat_input(
    "",
    key="chat",
    accept_file="multiple",
):
    st.rerun()
```
