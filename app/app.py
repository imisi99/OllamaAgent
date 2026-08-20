import base64
import logging
import json
from pathlib import Path
import time
from typing import cast
import httpx
import requests
import streamlit as st
import warnings

from session import (
    add_a_session_to_project,
    change_session_project,
    rename_sess,
    delete_sess,
    find_similar_sess,
)
from user import rename_user, user_memory, add_memory, view_settings
from project import (
    edit_project,
    view_project,
    view_projects,
    remove_session_from_project,
    add_session_to_project,
    delete_project,
    create_project,
)


from streamlit_float import float_init
from streamlit.elements.widgets.chat import ChatInputValue
from streamlit.runtime.uploaded_file_manager import UploadedFile

# TODO:
# Add a model picker for the app
# Add the audio functionality use a STT
# Add the audio implementatoin


warnings.filterwarnings("ignore", message=".*st.components.v1.html.*")
logging.basicConfig(level=logging.INFO)

float_init()

API_URL = "http://localhost:8000"
TEXT_EXTS = {
    ".py",
    ".txt",
    ".json",
    ".md",
    ".yaml",
    ".yml",
    ".toml",
    ".csv",
    ".js",
    ".ts",
    ".go",
    ".rs",
    ".java",
    ".html",
}


def user_bubble(content: str, images: list, files: list, audio: dict | None):
    with st.container(border=True, autoscroll=True):
        if images:
            cols = st.columns(min(len(images), 2))
            for idx, img in enumerate(images):
                with cols[idx % 2]:
                    try:
                        img_bytes = base64.b64decode(img["image"])
                        st.image(
                            img_bytes,
                            use_container_width=True,
                            output_format="auto",
                            caption=img["name"],
                        )
                    except Exception as e:
                        logging.info(f"Failed to render image err -> {e}")
                        st.caption("Failed to render image.")

        if files:
            for f in files:
                ext = Path(f["name"]).suffix.lower()
                with st.expander(f"{f['name']}", expanded=False, icon="spinner"):
                    if ext in TEXT_EXTS:
                        try:
                            text = base64.b64decode(f["file"]).decode(
                                "utf-8", errors="replace"
                            )
                            lang = ext.strip(".")
                            st.code(text, language=lang, line_numbers=True, height=300)
                        except Exception as e:
                            logging.info(f"Failed to render file err -> {e}")
                            st.caption("Error decoding file content.")
                    elif ext.strip(".") == "pdf":
                        st.pdf(base64.b64decode(f["file"]))
                    else:
                        st.caption("No preview available for this file type.")

        if audio:
            try:
                audio_bytes = base64.b64decode(audio["audio"])
                st.audio(audio_bytes, format=audio["mime"])
            except Exception as e:
                logging.info(f"Failed to play audio err -> {e}")
                st.caption("Failed to playback audio.")
        st.text(content)


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
        if st.button(st.session_state.user_name, use_container_width=True):
            st.session_state.active_dialog = "view_settings"
            st.rerun()


def display_session_actions():
    if not st.session_state.ghost_session and not st.session_state.show_header:

        name = (
            "Untitled"
            if "session_name" not in st.session_state
            else st.session_state.session_name
        )

        session_actions = st.container(key="floating_session_actions")

        with session_actions:
            with st.expander(name):
                rename, delete, find, project = st.columns(
                    [1, 1, 1, 1], vertical_alignment="center"
                )
                if rename.button("Rename"):
                    st.session_state.active_dialog = "rename_sess"
                    st.rerun()
                if find.button("Similar"):
                    st.session_state.active_dialog = "find_similar_sess"
                    st.rerun()
                if st.session_state.session_pid == "":
                    if project.button("Add Project"):
                        st.session_state.active_dialog = "add_a_session"
                        st.rerun()
                else:
                    view, change = project.columns([1, 1], vertical_alignment="center")
                    if view.button("View Project"):
                        st.session_state.active_dialog = "view_project"
                        st.rerun()
                    if change.button("Change Project"):
                        st.session_state.active_dialog = "change_project"
                        st.rerun()
                if delete.button("Delete", type="primary"):
                    st.session_state.active_dialog = "delete_sess"
                    st.rerun()

        session_actions.float(
            "top: 60px; left: 35%; right: 0; width: 30%; max-height: 220px; overflow-y: auto; "
            "background-color: rgba(38, 39, 48, 0.75); backdrop-filter: blur(8px); "
            "-webkit-backdrop-filter: blur(8px); z-index: 9999;"
        )


def get_or_create_user():
    if "user_id" not in st.session_state:
        with st.spinner():
            try:
                user_req = requests.get(url=f"{API_URL}/user")

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
                                    url=f"{API_URL}/user/create/" + username.strip()
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
                                        (
                                            resp["msg"]
                                            if "msg" in resp
                                            else resp["detail"]
                                        ),
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
        if st.button("Projects", use_container_width=True):
            st.session_state.active_dialog = "view_projects"
            st.rerun()

        if st.button(
            "New Chat",
            icon=":material/add:",
            type="tertiary",
        ):
            st.session_state.session_id = ""
            st.session_state.session_uid = ""
            st.session_state.session_pid = ""
            st.session_state.show_header = True
            st.session_state.messages = []
            st.rerun()

        if "sessions_fetched" not in st.session_state or st.session_state.get(
            "update_view"
        ):
            with st.spinner():
                try:
                    sessions_req = requests.get(url=f"{API_URL}/session/all/preview")

                    if sessions_req.status_code == 404:
                        st.session_state.sessions = []
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
                                f"{API_URL}/session/" + session["_id"]
                            )

                            if message_req.status_code == 200:
                                st.session_state.session_id = session["_id"]
                                st.session_state.session_uid = session["uuid"]
                                st.session_state.session_pid = session["project_id"]
                                st.session_state.ghost_session = False
                                st.session_state.show_header = False
                                st.session_state.messages = message_req.json()[
                                    "messages"
                                ]
                                logging.error(st.session_state.messages)
                                st.rerun()

                            elif message_req.status_code == 404:
                                st.toast("Session not found.")

                            else:
                                resp = message_req.json()
                                st.toast(
                                    resp["msg"] if "msg" in resp else resp["detail"],
                                    duration=7,
                                )

                        except Exception as e:
                            logging.error(
                                f"Failed to complete request to the server -> {e}"
                            )
                            st.error(
                                "Failed to fetch session \n couldn't communicate with the server."
                            )


def filter_files_audio(upload_file: list[UploadedFile], audio: UploadedFile | None):
    images = []
    files = []
    audio_info = None

    file_map = TEXT_EXTS | {".pdf", ".docx", "xlxs"}

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

    if audio:
        audio_info = {
            "audio": base64.b64encode(audio.read()).decode(),
            "mime": audio.type,
            "transcript": "",
        }

        try:
            audio_req = requests.post(
                url=f"{API_URL}/audio/transcribe",
                json=audio_info,
            )

            resp = audio_req.json()
            if audio_req.status_code != 200:
                st.toast(resp["msg"] if "msg" in resp else resp["detail"])
                st.stop()

            audio_info["transcript"] = resp["transcript"]

        except Exception as e:
            st.toast(f"Failed to transcribe audio -> {e}")
            st.stop()

    return files, images, audio_info


def chat():
    if (
        prompt := st.chat_input(
            "",
            key="chat",
            accept_file="multiple",
            max_upload_size=20,
            max_chars=5000,
            accept_audio=True,
            file_type=[f_type for f_type in TEXT_EXTS].extend([".png", ".jpeg"]),
        )
        or st.session_state.stored_prompt is not None
    ):
        prompt = cast(ChatInputValue, prompt)

        if st.session_state.stored_prompt is not None:
            prompt = st.session_state.stored_prompt
            st.session_state.stored_prompt = None

        if "skip_message" not in st.session_state:
            st.session_state.skip_message = False

        if not st.session_state.skip_message:
            (
                st.session_state.chat_files,
                st.session_state.chat_images,
                st.session_state.audio,
            ) = filter_files_audio(prompt.files, prompt.audio)

            if len(st.session_state.chat_images) > 2:
                st.toast("A maximum of 2 images is allowed per time!")
                st.stop()

            if len(st.session_state.chat_files) > 3:
                st.toast("A maximum of 3 files is allowed per time!")
                st.stop()

        if st.session_state.session_id == "" and not st.session_state.ghost_session:
            try:
                create_session = st.empty()
                create_session.markdown("*creating session...*")

                new_session = requests.post(
                    url=f"{API_URL}/session/create",
                    json={
                        "prompt": prompt.text,
                        "files": st.session_state.chat_files,
                        "images": st.session_state.chat_images,
                        "audio": st.session_state.audio,
                    },
                )

                if new_session.status_code != 201:
                    resp = new_session.json()
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

        if not st.session_state.skip_message:
            if not st.session_state.ghost_session:
                start_chat = st.empty()
                start_chat.markdown("*starting chat...*")
                try:
                    add_msg_response = requests.put(
                        url=f"{API_URL}/session/msg/"
                        + st.session_state.session_id
                        + "/"
                        + st.session_state.session_uid,
                        json={
                            "role": "user",
                            "content": prompt.text,
                            "audio": st.session_state.audio,
                            "thought": "",
                            "timestamp": "",
                            "session_id": st.session_state.session_id,
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

        user_bubble(
            prompt.text,
            st.session_state.chat_images,
            st.session_state.chat_files,
            st.session_state.audio,
        )

        st.session_state.messages.append(
            {
                "role": "user",
                "content": prompt.text,
                "images": st.session_state.chat_images,
                "files": st.session_state.chat_files,
                "audio": st.session_state.audio,
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
                            "audio": st.session_state.audio,
                            "thought": "",
                            "timestamp": "",
                            "session_id": st.session_state.session_id,
                            "files": st.session_state.chat_files,
                            "images": st.session_state.chat_images,
                        },
                        "ghost_session": st.session_state.ghost_session,
                    },
                    timeout=120,
                ) as r:
                    start_time = time.time()
                    for token in r.iter_text():
                        chunk = json.loads(token)

                        thought = "*pondering on it...*"

                        if chunk["type"] == "tool":
                            thought_placeholder.markdown(f"*{chunk['content']}*")
                        elif chunk["type"] == "text":
                            if response_text == "":
                                with thought_placeholder.popover(
                                    "*thought...*", type="tertiary"
                                ):
                                    st.write(thought_text)
                            response_text += chunk["content"]
                            response_placeholder.markdown(f"{response_text}" + "\u2502")
                        elif chunk["type"] == "reason":
                            curr_time = time.time()
                            if thought_text == "":
                                start_time = time.time()

                            if curr_time - start_time > 30:
                                thought = "*still pondering on it...*"
                            if curr_time - start_time > 60:
                                thought = "*gathering thoughts...*"
                            if curr_time - start_time > 120:
                                thought = "*please be patient...*"

                            thought_placeholder.markdown(thought)
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


def display_session_message():
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            user_bubble(msg["content"], msg["images"], msg["files"], msg["audio"])
        else:
            with st.popover("*thought...*", type="tertiary"):
                st.write(msg["thought"])
            st.markdown(msg["content"], text_alignment="justify")


def open_active_dialog():
    while st.session_state.get("active_dialog", "") != "":
        match st.session_state.active_dialog:
            case "view_settings":
                view_settings()
            case "rename_user":
                rename_user()
            case "user_memory":
                user_memory()
            case "add_memory":
                add_memory()
            case "rename_sess":
                rename_sess()
            case "find_similar_sess":
                find_similar_sess()
            case "add_a_session":
                add_a_session_to_project()
            case "delete_sess":
                delete_sess()
            case "change_project":
                change_session_project()
            case "view_projects":
                view_projects()
            case "view_project":
                view_project()
            case "create_project":
                create_project()
            case "edit_project":
                edit_project()
            case "remove_sessions":
                remove_session_from_project()
            case "add_sessions":
                add_session_to_project()
            case "add_a_session":
                add_a_session_to_project()
            case "delete_project":
                delete_project()
            case _:
                break


if "show_header" not in st.session_state:
    st.session_state.show_header = True


if "ghost_session" not in st.session_state:
    st.session_state.ghost_session = False

if "stored_prompt" not in st.session_state:
    st.session_state.stored_prompt = None

if "session_id" not in st.session_state:
    st.session_state.session_id = ""
    st.session_state.session_uid = ""
    st.session_state.session_pid = ""
    st.session_state.session_name = ""
    st.session_state.messages = []

if "active_dialog" not in st.session_state:
    st.session_state.active_dialog = ""


header()

open_active_dialog()

get_or_create_user()

user_profile()
session_sidebar()

display_session_actions()
display_session_message()

chat()
