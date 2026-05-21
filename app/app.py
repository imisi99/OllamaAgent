import base64
import logging
import json
from pathlib import Path
import time
from typing import cast
import httpx
import requests
import streamlit as st


from streamlit.elements.widgets.chat import ChatInputValue
from streamlit.runtime.uploaded_file_manager import UploadedFile


# TODO:
# Fix the loading of file back for streamlit and also the images let it be empty if not in use


# DONE:
# It doesn't affect other windows the change
# Moving between chats between conversations Doesn't get the chat stored (should a single API call be chained to use it ?)
# (Or use a queue sort of to add messages to the stuff ? )
# Adding the metrics (reasoning content, tool calls in the view also ? )
# Getting a reasoning error after streaming ends ?


API_URL = "http://localhost:8000"

st.markdown(
    """
    <style>
    .bubble-wrapper {
        display: flex;
        margin: 12px 0;
        gap: 8px;
    }
    .bubble-wrapper.user {
        justify-content: flex-end;
    }
    .bubble {
        padding: 10px 16px;
        border-radius: 18px;
        font-size: 0.95rem;
        line-height: 1.4;
        word-wrap: break-word;
    }
    .bubble.user {
        max-width: 75%;
        background-color: black;
        color: #e8eaf0;
        border-bottom-right-radius: 4px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def user_bubble(content: str, images: list):
    def get_mime(img: str) -> str:
        if img.startswith("ivBOR"):
            return "image/png"
        return "image/jpeg"

    images_html = ""
    if images:
        for img in images:
            images_html += f'<img src="data:{get_mime};base64,{img}" style="max-width:100%; border-radius:10px; margin-bottom:6px; display:block;"/>'
    st.markdown(
        f"""
        <div class="bubble-wrapper user">
            <div class="bubble user">{content}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def header():
    if st.session_state.show_header:
        with st.header(""):
            col1, col2 = st.columns([0.7, 0.1])
            with col1:
                st.header(
                    ":red[Ollama] :grey[_Agent_]", divider="grey", width="content"
                )
            with col2:
                if (
                    "session_id" not in st.session_state
                    or st.session_state.session_id == ""
                ):
                    if not st.session_state.ghost_session:
                        if st.button(
                            "Ghost",
                            help="This creates a temporary chat that doesn't persist",
                            type="tertiary",
                        ):
                            st.session_state.ghost_session = True
                            st.rerun()
                    else:
                        if st.button(
                            "Norm",
                            help="This creates a normal chat that will persist",
                            type="tertiary",
                        ):
                            st.session_state.ghost_session = False
                            st.rerun()


def user_profile():
    with st.sidebar:
        with st.expander(st.session_state.user_name, width=300):

            @st.dialog("Change your username")
            def rename_user():
                new_name = st.text_input("Enter New Username")
                if st.button("Confirm", key="confirm_user_rename"):
                    if new_name:
                        with st.spinner():
                            try:
                                rename_user = requests.put(
                                    url="http://server:8000/user/"
                                    + st.session_state.user_id
                                    + "/update/"
                                    + new_name.strip()
                                )
                                if rename_user.status_code == 202:
                                    st.toast("Username updated successfully.")
                                    st.session_state.user_name = new_name.strip()
                                    time.sleep(0.5)
                                    st.rerun()

                                else:
                                    resp = rename_user.json()
                                    st.toast(
                                        resp["msg"]
                                        if "msg" in resp
                                        else resp["detail"],
                                        duration=6,
                                    )
                            except Exception as e:
                                logging.error(
                                    f"Failed to complete request to the server -> {e}"
                                )
                                st.error(
                                    "Failed to change username \n couldn't communicate with the server."
                                )

            @st.dialog("View Memory")
            def user_memory():
                if "user_memory" not in st.session_state:
                    st.session_state.user_memory = {}

                with st.spinner():
                    try:
                        memory_req = requests.get(
                            url="http://localhost:8000/user/me/"
                            + st.session_state.user_id
                        )

                        if memory_req.status_code == 404:
                            st.toast("Unable to find user.")

                        elif memory_req.status_code == 200:
                            st.session_state.user_memory = memory_req.json()["user"][
                                "memory"
                            ]

                        else:
                            resp = memory_req.json()
                            st.toast(
                                resp["msg"] if "msg" in resp else resp["detail"],
                                duration=6,
                            )

                    except Exception as e:
                        logging.error(
                            f"Failed to complete request to the server -> {e}"
                        )
                        st.error(
                            "Failed to fetch memory \n couldn't communicate with the server."
                        )

                for key, value in st.session_state.user_memory.items():
                    col1, col2, col3 = st.columns([0.6, 0.30, 0.20])
                    with col1:
                        with st.popover(key):
                            st.markdown(value)
                    with col2:
                        with st.popover("Update"):
                            newValue = st.text_input(
                                label="Nil", value=value, label_visibility="hidden"
                            )
                            if st.button("Confirm") and newValue:
                                with st.spinner():
                                    try:
                                        update_req = requests.put(
                                            url="http://localhost:8000/user/"
                                            + st.session_state.user_id
                                            + "/update/memory",
                                            json={
                                                "key": key,
                                                "value": newValue,
                                            },
                                        )

                                        if update_req.status_code == 202:
                                            st.toast("Memory updated successfully.")
                                            st.session_state.user_memory[key] = value
                                            time.sleep(0.5)
                                            st.rerun()

                                        else:
                                            resp = update_req.json()
                                            st.toast(
                                                resp["msg"]
                                                if "msg" in resp
                                                else resp["detail"],
                                                duration=6,
                                            )
                                    except Exception as e:
                                        logging.error(
                                            f"Failed to complete request to the server -> {e}"
                                        )
                                        st.error(
                                            "Failed to update memory \n couldn't communicate with the server."
                                        )
                    with col3:
                        if st.button("Delete"):
                            with st.spinner():
                                try:
                                    delete_req = requests.delete(
                                        url="http://localhost:8000/user/"
                                        + st.session_state.user_id
                                        + "/delete/memory/"
                                        + key
                                    )

                                    if delete_req.status_code == 202:
                                        st.toast("Memory deleted successfully.")
                                        st.session_state.user_memory.pop(key)
                                        time.sleep(0.5)
                                        st.rerun()

                                    else:
                                        resp = delete_req.json()
                                        st.toast(
                                            resp["msg"]
                                            if "msg" in resp
                                            else resp["detail"],
                                            duration=6,
                                        )

                                except Exception as e:
                                    logging.error(
                                        f"Failed to complete request to the server -> {e}"
                                    )
                                    st.error(
                                        "Failed to delete memory \n couldn't communicate with the server."
                                    )

            @st.dialog("Add a memory")
            def add_memory():
                key = st.text_input("Enter the key")
                value = st.text_input("Enter the value")

                if st.button("Add Memory"):
                    if key and value:
                        with st.spinner():
                            try:
                                add_mem_req = requests.put(
                                    url="http://localhost:8000/user/"
                                    + st.session_state.user_id
                                    + "/update/memory",
                                    json={"key": key, "value": value},
                                )

                                if add_mem_req.status_code == 202:
                                    st.toast("Memory added successfully.")
                                    st.session_state.user_memory[key] = value
                                    time.sleep(0.5)
                                    st.rerun()

                                else:
                                    resp = add_mem_req.json()
                                    st.toast(
                                        resp["msg"]
                                        if "msg" in resp
                                        else resp["detail"],
                                        duration=6,
                                    )

                            except Exception as e:
                                logging.error(
                                    f"Failed to complete request to the server -> {e}"
                                )
                                st.error(
                                    "Failed to create memory \n couldn't communicate with the server."
                                )

            if st.button("Rename"):
                rename_user()

            memCol, addCol = st.columns(2)

            with memCol:
                if st.button("Memory"):
                    user_memory()

            with addCol:
                if st.button("Add"):
                    add_memory()


def display_session_actions():
    if not st.session_state.ghost_session and not st.session_state.show_header:
        name = ""
        if st.session_state.session_id == "":
            name = "Untitled"
        else:
            name = st.session_state.session_name
        with st.expander(label=name, width=350):

            @st.dialog("Rename Session")
            def rename_sess():
                new_name = st.text_input(
                    "Enter New Name", value=st.session_state.session_name
                )
                if st.button("Confirm", key="confirm_rename"):
                    if new_name:
                        with st.spinner():
                            try:
                                rename_req = requests.put(
                                    url="http://localhost:8000/session/rename/"
                                    + st.session_state.session_id
                                    + "/"
                                    + st.session_state.session_uid
                                    + "?name="
                                    + new_name
                                )

                                if rename_req.status_code == 202:
                                    st.toast("Session renamed successfully.")
                                    st.session_state.session_name = new_name
                                    st.session_state.update_view = True
                                    time.sleep(0.5)
                                    st.rerun()
                                else:
                                    resp = rename_req.json()
                                    st.toast(
                                        resp["msg"]
                                        if "msg" in resp
                                        else resp["detail"],
                                        duration=6,
                                    )

                            except Exception as e:
                                logging.error(
                                    f"Failed to complete request to the server -> {e}"
                                )
                                st.error(
                                    "Failed to rename session \n couldn't communicate with the server."
                                )

            @st.dialog("Delete Session")
            def delete_sess():
                if st.button("Confirm", key="confirm_delete"):
                    with st.spinner():
                        try:
                            delete_req = requests.delete(
                                url="http://localhost:8000/session/delete/"
                                + st.session_state.session_id
                                + "/"
                                + st.session_state.session_uid,
                            )

                            if delete_req.status_code == 200:
                                st.toast("Session deleted successfully")
                                st.session_state.update_view = True
                                remove_active_session_from_sessions()
                                st.session_state.session_id = ""
                                st.session_state.session_uid = ""
                                st.session_state.messages = []
                                st.session_state.session_name = ""
                                st.session_state.show_header = True
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                resp = delete_req.json()
                                st.toast(
                                    resp["msg"] if "msg" in resp else resp["detail"],
                                    duration=6,
                                )

                        except Exception as e:
                            logging.error(
                                f"Failed to complete request to the server -> {e}"
                            )
                            st.error(
                                "Failed to delete session \n couldn't communicate with the server."
                            )

            @st.dialog("Find Similar Sessions")
            def find_similar_sess():
                threshold = st.number_input(
                    "Enter threshold", min_value=0.0, max_value=1.0, value=0.5
                )
                limit = st.number_input(
                    "Enter limit", min_value=1, max_value=100, value=5
                )
                if st.button("Find Sessions") or st.session_state.get("find_session"):
                    st.session_state.find_session = True
                    with st.spinner("Finding sessions..."):
                        try:
                            similar_req = requests.get(
                                url=f"{API_URL}/session/find/similar",
                                json={
                                    "uid": st.session_state.session_uid,
                                    "threshold": threshold,
                                    "limit": limit,
                                },
                            )

                            if similar_req.status_code == 200:
                                sessions, avgScore = (
                                    similar_req.json()["sessions"],
                                    similar_req.json()["score"],
                                )

                                st.write(
                                    f" Retrieved {len(sessions)} sessions with an average score of -> {avgScore}"
                                )

                                similar_col1, similar_col2 = st.columns([0.8, 0.2])
                                for sess in sessions:
                                    with similar_col1:
                                        load_sess_id = sess[0]["_id"]
                                        load_sess_uid = sess[0]["uuid"]
                                        if st.button(sess[0]["name"]):
                                            try:
                                                message_req = requests.get(
                                                    url=f"{API_URL}/session/"
                                                    + load_sess_id,
                                                )

                                                resp = message_req.json()

                                                if message_req.status_code == 200:
                                                    st.session_state.session_id = (
                                                        load_sess_id
                                                    )
                                                    st.session_state.session_uid = (
                                                        load_sess_uid
                                                    )
                                                    st.session_state.ghost_session = (
                                                        False
                                                    )
                                                    st.session_state.show_header = False
                                                    st.session_state.messages = resp[
                                                        "session"
                                                    ]["messages"]
                                                    st.session_state.find_session = (
                                                        False
                                                    )
                                                    st.session_state.session_name = (
                                                        resp["session"]["name"]
                                                    )
                                                    st.rerun()
                                                else:
                                                    st.toast(
                                                        resp["msg"]
                                                        if "msg" in resp
                                                        else resp["detail"],
                                                        duration=7,
                                                    )
                                            except Exception as e:
                                                st.toast("Unable to load the session.")
                                                logging.error(
                                                    f"Failed to load session with id -> {load_sess_id}, err -> {e}"
                                                )

                                    with similar_col2:
                                        st.write(sess[1])

                            else:
                                st.session_state.find_session = False
                                resp = similar_req.json()
                                st.info(
                                    resp["msg"] if "msg" in resp else resp["detail"]
                                )
                        except Exception as e:
                            logging.error(
                                f"Failed to complete request to the server -> {e}"
                            )
                            st.error(
                                "Failed to find similar sessions, couldn't communicate with the server."
                            )

            col1, col2, col3 = st.columns([0.34, 0.3, 0.37])
            with col1:
                if st.button("Rename"):
                    rename_sess()
            with col2:
                if st.button("Delete"):
                    delete_sess()
            with col3:
                if st.button("Similar"):
                    find_similar_sess()


def get_or_create_user():
    if "user_id" not in st.session_state:
        with st.spinner():
            try:
                user_req = requests.get(url="http://localhost:8000/user")

                if user_req.status_code == 200:
                    st.session_state.user_id = user_req.json()["id"]
                    st.session_state.user_name = user_req.json()["name"]
                    st.rerun()
                elif user_req.status_code == 404:

                    @st.dialog("Create a new user.", dismissible=False)
                    def create_user():
                        username = st.text_input("Create user")
                        if st.button("Create") and username:
                            try:
                                new_user_req = requests.post(
                                    url="http://localhost:8000/user/create/"
                                    + username.strip()
                                )

                                if new_user_req.status_code == 201:
                                    st.toast("User created successfully.")
                                    st.session_state.user_id = new_user_req.json()["id"]
                                    st.session_state.user_name = username.strip()
                                    time.sleep(0.5)
                                    st.rerun()
                                else:
                                    resp = new_user_req.json()
                                    st.toast(
                                        resp["msg"]
                                        if "msg" in resp
                                        else resp["detail"],
                                        duration=6,
                                    )
                            except Exception as e:
                                logging.error(
                                    f"Failed to complete request to the server -> {e}"
                                )
                                st.error(
                                    "Failed to create a new user \n couldn't communicate with the server."
                                )
                        st.info("You have to create a new user")
                        st.stop()

                    create_user()

                else:
                    resp = user_req.json()
                    st.toast(
                        resp["msg"] if "msg" in resp else resp["detail"],
                        duration=6,
                    )
                    st.stop()

            except Exception as e:
                logging.error(f"Failed to complete request to the server -> {e}")
                st.error(
                    "Failed to fetch user \n couldn't communicate with the server."
                )
                st.stop()


def session_sidebar():
    with st.sidebar:
        if st.button(
            "New Chat",
            icon=":material/add:",
            type="tertiary",
        ):
            st.session_state.session_id = ""
            st.session_state.session_uid = ""
            st.session_state.show_header = True
            st.session_state.messages = []
            st.rerun()

        if "sessions_fetched" not in st.session_state or st.session_state.get(
            "update_view"
        ):
            with st.spinner():
                try:
                    sessions_req = requests.get(
                        url="http://localhost:8000/session/all/preview"
                    )

                    if sessions_req.status_code == 404:
                        st.info("you have no existing session start a new session")

                    elif sessions_req.status_code == 200:
                        st.session_state.sessions = sessions_req.json()["sessions"]

                    else:
                        resp = sessions_req.json()
                        st.toast(
                            resp["msg"] if "msg" in resp else resp["detail"],
                            duration=7,
                        )

                except Exception as e:
                    logging.error(f"Failed to complete request to the server -> {e}")
                    st.error(
                        "Failed to fetch sessions couldn't communicate with the server."
                    )

            st.session_state.sessions_fetched = True
            st.session_state.update_view = False

        if st.session_state.get("sessions"):
            for session in reversed(st.session_state.sessions):
                if st.button(session["name"], use_container_width=True):
                    st.session_state.session_name = session["name"]
                    with st.spinner():
                        try:
                            message_req = requests.get(
                                "http://localhost:8000/session/" + session["_id"]
                            )

                            if message_req.status_code == 200:
                                st.session_state.session_id = session["_id"]
                                st.session_state.session_uid = session["uuid"]
                                st.session_state.ghost_session = False
                                st.session_state.show_header = False
                                st.session_state.messages = message_req.json()[
                                    "session"
                                ]["messages"]
                                st.rerun()

                            elif message_req.status_code == 404:
                                st.toast("Session not found.")

                            else:
                                resp = message_req.json()
                                st.toast(
                                    resp["msg"] if "msg" in resp else resp["detail"],
                                    duration=7,
                                )
                            st.stop()

                        except Exception as e:
                            logging.error(
                                f"Failed to complete request to the server -> {e}"
                            )
                            st.error(
                                "Failed to fetch session \n couldn't communicate with the server."
                            )
                            st.stop()


def filter_files(upload_file: list[UploadedFile]):
    images = []
    files = []

    file_map = set(
        [
            ".pdf",
            ".docx",
            ".txt",
            ".md",
            ".html",
            ".xlsx",
            ".go",
            ".py",
            ".java",
            ".js",
            ".rs",
        ]
    )

    image_map = set([".png", ".jpeg"])

    for file in upload_file:
        ext = Path(file.name).suffix.lower()
        if ext in file_map:
            files.append(
                {
                    "file": base64.b64encode(file.read()).decode(),
                    "name": file.name,
                }
            )
        elif ext in image_map:
            images.append(
                {
                    "image": base64.b64encode(file.read()).decode(),
                    "mime": file.type,
                    "name": file.name,
                }
            )
        else:
            st.toast(f"Failed to upload file -> {file.name} type not supported")

    return files, images


def chat():
    if (
        prompt := st.chat_input("", key="chat", accept_file="multiple")
        or st.session_state.stored_prompt is not None
    ):
        prompt = cast(ChatInputValue, prompt)

        if st.session_state.stored_prompt is not None:
            prompt = st.session_state.stored_prompt
            st.session_state.stored_prompt = None

        if "skip_message" not in st.session_state:
            st.session_state.skip_message = False

        if st.session_state.session_id == "" and not st.session_state.ghost_session:
            try:
                create_session = st.empty()
                create_session.markdown("*creating session...*")

                new_session = requests.post(
                    url="http://localhost:8000/session/create",
                    json={
                        "prompt": prompt.text,
                        "files": st.session_state.chat_files,
                        "images": st.session_state.chat_images,
                    },
                )

                if new_session.status_code != 201:
                    resp = new_session.json()
                    logging.error(resp)
                    st.toast(
                        resp["msg"] if "msg" in resp else resp["detail"],
                        duration=7,
                    )
                    st.stop()

                st.session_state.session_id = new_session.json()["id"]
                st.session_state.session_uid = new_session.json()["uid"]
                st.session_state.session_name = new_session.json()["title"]
                st.session_state.update_view = True
                st.session_state.stored_prompt = prompt
                st.session_state.show_header = False
                st.session_state.skip_message = True
                create_session.empty()
                st.rerun()

            except Exception as e:
                logging.error(f"Failed to complete request to the server -> {e}")
                st.error(
                    "Failed to create session \n couldn't communicate with the server."
                )
                st.stop()

        st.session_state.chat_files, st.session_state.chat_images = filter_files(
            prompt.files
        )

        if not st.session_state.skip_message:
            if not st.session_state.ghost_session:
                start_chat = st.empty()
                start_chat.markdown("*starting chat...*")
                try:
                    add_msg_response = requests.put(
                        url="http://localhost:8000/session/msg/"
                        + st.session_state.session_id
                        + "/"
                        + st.session_state.session_uid,
                        json={
                            "role": "user",
                            "content": prompt.text,
                            "thought": "",
                            "timestamp": "",
                            "files": st.session_state.chat_files,
                            "images": st.session_state.chat_images,
                        },
                    )

                    if add_msg_response.status_code != 202:
                        resp = add_msg_response.json()
                        st.toast(
                            resp["msg"] if "msg" in resp else resp["detail"],
                            duration=7,
                        )
                        st.stop()

                except Exception as e:
                    logging.error(f"Failed to complete request to the server -> {e}")
                    st.error(
                        "Failed to send message \n couldn't communicate with the server."
                    )
                    st.stop()

                start_chat.empty()

        user_bubble(prompt.text, st.session_state.chat_images)
        st.session_state.messages.append(
            {
                "role": "user",
                "content": prompt.text,
                "images": st.session_state.chat_images,
            }
        )

        if st.session_state.skip_message:
            st.session_state.skip_message = False

        try:

            def stream_response() -> tuple[str, str]:
                thought_placeholder = st.empty()
                response_placeholder = st.empty()

                thought_placeholder.markdown("*pondering on it...*")
                if len(st.session_state.chat_images) > 0:
                    thought_placeholder.markdown("*Analyzing image...*")

                response_text = ""
                thought_text = ""

                with httpx.stream(
                    "POST",
                    f"{API_URL}/agent/chat/stream",
                    json={
                        "session_id": st.session_state.session_id,
                        "session_uid": st.session_state.session_uid,
                        "user_id": st.session_state.user_id,
                        "message": {
                            "role": "user",
                            "content": prompt.text,
                            "thought": "",
                            "timestamp": "",
                            "files": st.session_state.chat_files,
                            "images": st.session_state.chat_images,
                        },
                        "ghost_session": st.session_state.ghost_session,
                    },
                    timeout=120,
                ) as r:
                    for token in r.iter_text():
                        chunk = json.loads(token)

                        if chunk["type"] == "tool":
                            response_placeholder.markdown(f"*{chunk['content']}*")
                        elif chunk["type"] == "text":
                            if response_text == "":
                                with thought_placeholder.popover(
                                    "*thought...*", type="tertiary"
                                ):
                                    st.write(thought_text)
                            response_text += chunk["content"]
                            response_placeholder.markdown(f"{response_text}" + "\u2502")
                        elif chunk["type"] == "reason":
                            thought_placeholder.markdown("*pondering on it...*")
                            thought_text += chunk["content"]
                        elif chunk["type"] == "tool_end":
                            response_placeholder.markdown("*working on it...*")

                with thought_placeholder.popover("*thought...*", type="tertiary"):
                    st.write(thought_text)
                response_placeholder.markdown(response_text)

                return response_text, thought_text

            full_response, full_thought = stream_response()
            st.session_state.messages.append(
                {"role": "assistant", "content": full_response, "thought": full_thought}
            )

        except Exception as e:
            logging.error(f"Failed to complete request to the server -> {e}")
            st.error(
                "Failed to chat with agent \n couldn't communicate with the server."
            )
            st.stop()

        if st.session_state.get("update_view"):
            st.rerun()


def remove_active_session_from_sessions():
    for session in st.session_state.sessions:
        if session["_id"] == st.session_state.session_id:
            st.session_state.sessions.remove(session)


def display_session_message():
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            user_bubble(msg["content"], msg["images"])
        else:
            with st.popover("*thought...*", type="tertiary"):
                st.write(msg["thought"])
            st.markdown(msg["content"])


if "show_header" not in st.session_state:
    st.session_state.show_header = True


if "ghost_session" not in st.session_state:
    st.session_state.ghost_session = False

if "stored_prompt" not in st.session_state:
    st.session_state.stored_prompt = None

if "session_id" not in st.session_state:
    st.session_state.session_id = ""
    st.session_state.session_uid = ""
    st.session_state.session_name = ""
    st.session_state.messages = []


header()


get_or_create_user()
user_profile()
session_sidebar()

display_session_actions()
display_session_message()

chat()
