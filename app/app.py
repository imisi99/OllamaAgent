import base64
import logging
import time
from typing import cast
import requests
import streamlit as st

from datetime import datetime

from streamlit.elements.widgets.chat import ChatInputValue


# TODO:
# Moving between chats between conversations Doesn't get the chat stored (should a single API call be chained to use it ?)
# Adding the metrics (reasoning content, tool calls in the view also ? )

# DONE:
# Also add the session action to first be untitled.
# Have a toggle between ghost and normal chat before starting a session
# After deleting a session move back to the new chat
# Walk through the ghost session and see if it works
# Add a clear header if still show header after the first chat
# The Delete does work but it doesn't clear from the sidebar until refreshed also delete from cache also
# The Rename isn't doing anything
# Is it possible to clear the notification of info, error and warning
# Use Expanded for the user profile settings probably
# Fix the Update memory button to work with the new dialog rep
# Rewrite the pop up to use dialog for the collection of inputs (Can change the memory view)
# Rewrite the create user using dialog
# The name in the extend stuff doesn't show it after first instance


def header():
    if st.session_state.show_header:
        with st.header(""):
            col1, col2 = st.columns([3, 1.0])
            with col1:
                st.header(
                    ":red[Ollama] :grey[_Agent_]", divider="grey", width="content"
                )
            with col2:
                if (
                    "session_id" not in st.session_state
                    or st.session_state.session_id == ""
                ):
                    if st.toggle(
                        label="Ghost",
                        help="This creates a temporary chat that is not stored.",
                    ):
                        st.session_state.ghost_session = True
                    else:
                        st.session_state.ghost_session = False


def user_profile():
    with st.sidebar:
        with st.expander("⚙️ " + st.session_state.user_name, width=300):

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
        with st.expander(label=name, width=230):

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

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Rename"):
                    rename_sess()
            with col2:
                if st.button("Delete"):
                    delete_sess()


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
                        st.info("you have no existing session \n start a new session")

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
                        "Failed to fetch sessions \n couldn't communicate with the server."
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


def chat():
    if (
        prompt := st.chat_input("", key="chat", accept_file="multiple")
        or st.session_state.stored_prompt is not None
    ):
        prompt = cast(ChatInputValue, prompt)

        if st.session_state.show_header and (
            st.session_state.session_id == "" or st.session_state.ghost_session
        ):
            st.session_state.show_header = False
            st.session_state.stored_prompt = prompt
            st.rerun()

        if st.session_state.stored_prompt is not None:
            prompt = st.session_state.stored_prompt
            st.session_state.stored_prompt = None

        if st.session_state.session_id == "" and not st.session_state.ghost_session:
            with st.spinner():
                try:
                    new_session = requests.post(
                        url="http://localhost:8000/session/create",
                        json={"prompt": prompt.text},
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

                except Exception as e:
                    logging.error(f"Failed to complete request to the server -> {e}")
                    st.error(
                        "Failed to create session \n couldn't communicate with the server."
                    )
                    st.stop()

        with st.chat_message("user"):
            if not st.session_state.ghost_session:
                with st.spinner():
                    try:
                        add_msg_response = requests.put(
                            url="http://localhost:8000/session/msg/"
                            + st.session_state.session_id
                            + "/"
                            + st.session_state.session_uid,
                            json={
                                "role": "user",
                                "content": prompt.text,
                                "timestamp": datetime.now().isoformat(),
                                "files": [
                                    (base64.b64encode(file.read()).decode(), file.name)
                                    for file in prompt.files
                                ],
                                "images": [("", "")],
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
                        logging.error(
                            f"Failed to complete request to the server -> {e}"
                        )
                        st.error(
                            "Failed to send message \n couldn't communicate with the server."
                        )
                        st.stop()

            st.markdown(prompt.text)
            st.session_state.messages.append({"role": "user", "content": prompt.text})

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response = requests.post(
                        url="http://localhost:8000/agent/chat",
                        json={
                            "session_id": st.session_state.session_id,
                            "session_uid": st.session_state.session_uid,
                            "user_id": st.session_state.user_id,
                            "message": {
                                "role": "user",
                                "content": prompt.text,
                                "timestamp": datetime.now().isoformat(),
                                "images": [("", "")],
                                "files": [
                                    (base64.b64encode(file.read()).decode(), file.name)
                                    for file in prompt.files
                                ],
                            },
                            "ghost_session": st.session_state.ghost_session,
                        },
                    )

                    if response.status_code != 200:
                        st.toast(
                            f"Failed to communicate with agent -> {
                                response.json()['detail']
                            }"
                        )
                        st.stop()

                    if not st.session_state.ghost_session:
                        add_msg_response = requests.put(
                            url="http://localhost:8000/session/msg/"
                            + st.session_state.session_id
                            + "/"
                            + st.session_state.session_uid,
                            json={
                                "role": "assistant",
                                "content": response.json()["msg"],
                                "timestamp": datetime.now().isoformat(),
                                "images": [("", "")],
                                "files": [("", "")],
                            },
                        )

                        if add_msg_response.status_code != 202:
                            resp = add_msg_response.json()
                            st.toast(
                                resp["msg"] if "msg" in resp else resp["detail"],
                                duration=7,
                            )
                            st.stop()

                    st.markdown(response.json()["msg"])
                    st.session_state.messages.append(
                        {"role": "assistant", "content": response.json()["msg"]}
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
        with st.chat_message(msg["role"]):
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
