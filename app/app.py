from datetime import datetime
import logging
import random
import requests
import streamlit as st


st.header(":red[Ollama] :grey[_Agent_]", divider="grey", width="content")

chat_holders = [
    "What's on your mind ?",
    "How can i help you today ?",
    "Back at it again !",
]


with st.sidebar:
    if st.button(
        "New Chat",
        icon=":material/add:",
        type="tertiary",
    ):
        st.session_state.session_id = ""
        st.session_state.messages = []
        st.session_state.chat_holder = random.randint(0, len(chat_holders) - 1)
        st.rerun()

    if (
        "sessions" not in st.session_state
        or len(st.session_state.sessions) == 0
        or ("update_view" in st.session_state and st.session_state.update_view)
    ):
        try:
            sessions_req = requests.get(url="http://localhost:8000/session/all/preview")
            if sessions_req.status_code == 404:
                st.info("you have no existing session \n start a new session")
                st.session_state.sessions = []

            elif sessions_req.status_code != 200:
                logging.error(
                    f"Failed to fetch available sessions from db, status_code -> {sessions_req.status_code}, json -> {sessions_req.json()}"
                )
                st.error("Failed to fetch sessions.")
                st.stop()

            else:
                st.session_state.sessions = sessions_req.json()["sessions"]

        except Exception as e:
            logging.error(
                f"An error occured while making a request to the server -> {e}"
            )
            st.error(f"Failed to complete request to server -> {e}")
            st.stop()

        st.session_state.update_view = False

    for session in reversed(st.session_state.sessions):
        if st.button(session["name"], use_container_width=True):
            active_session = None
            try:
                message_req = requests.get(
                    "http://localhost:8000/session/" + session["_id"]
                )

                if message_req.status_code == 404:
                    st.error("This session does not exist")
                    st.stop()

                elif message_req.status_code != 200:
                    logging.error(
                        f"Failed to fetch single sesion from db, status_code -> {message_req.status_code}, json -> {message_req.json()}"
                    )
                    st.error("Failed to fetch session.")
                    st.stop()
                else:
                    active_session = message_req.json()["session"]

            except Exception as e:
                logging.error(
                    f"An error occured while making a request to the server -> {e}"
                )
                st.error(f"Failed to complete request to server -> {e}")
                st.stop()

            st.session_state.session_id = session["_id"]
            st.session_state.chat_holder = -1
            st.session_state.messages = active_session["messages"]
            st.rerun()


if "chat_holder" not in st.session_state:
    st.session_state.chat_holder = random.randint(0, len(chat_holders) - 1)

if st.session_state.chat_holder != -1:
    st.subheader(chat_holders[st.session_state.chat_holder])

if "session_id" not in st.session_state:
    st.session_state.session_id = ""
    st.session_state.messages = []

if "messages" in st.session_state:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

if prompt := st.chat_input("", key="chat", accept_file="multiple"):
    if st.session_state.session_id == "":
        try:
            new_session = requests.post(
                url="http://localhost:8000/session/create",
                json={
                    "session_id": "",
                    "message": {
                        "role": "user",
                        "content": prompt.text,
                        "timestamp": datetime.now().isoformat(),
                    },
                },
            )

            if new_session.status_code != 200:
                logging.error(
                    f"Failed to create a new session, status_code -> {new_session.status_code}, json -> {new_session.json()}"
                )
                st.error("Failed to start a new session.")
                st.stop()
        except Exception as e:
            logging.error(
                f"An error occured while making a request to the server -> {e}"
            )
            st.error(f"Failed to complete request to server -> {e}")
            st.stop()
        st.session_state.session_id = new_session.json()["id"]
        st.session_state.chat_holder = -1
        st.session_state.update_view = True

    with st.chat_message("user"):
        try:
            add_msg_response = requests.post(
                url="http://localhost:8000/session/msg/" + st.session_state.session_id,
                json={
                    "role": "user",
                    "content": prompt.text,
                    "timestamp": datetime.now().isoformat(),
                },
            )

            if add_msg_response.status_code != 200:
                st.error("Failed to send message to agent.")
                st.stop()

        except Exception as e:
            logging.error(
                f"An error occured while making a request to the server -> {e}"
            )
            st.error(f"Failed to complete request to server -> {e}")
            st.stop()

        st.markdown(prompt.text)
    st.session_state.messages.append({"role": "user", "content": prompt.text})

    with st.chat_message("assistant"):
        try:
            response = requests.post(
                url="http://localhost:8000/agent/chat",
                json={
                    "session_id": st.session_state.session_id,
                    "message": {
                        "role": "user",
                        "content": prompt.text,
                        "timestamp": datetime.now().isoformat(),
                    },
                },
            )

            if response.status_code != 200:
                logging.error(
                    f"An error occured while trying to chat with agent, status_code -> {response.status_code}, json -> {response.json()}"
                )
                st.error("Failed to communicate with agent.")
                st.stop()

            add_msg_response = requests.post(
                url="http://localhost:8000/session/msg/" + st.session_state.session_id,
                json={
                    "role": "assistant",
                    "content": response.json()["msg"],
                    "timestamp": datetime.now().isoformat(),
                },
            )

            if add_msg_response.status_code != 200:
                st.error("Failed to communicate with agent.")
                st.stop()

        except Exception as e:
            logging.error(
                f"An error occured while making a request to the server -> {e}"
            )
            st.error(f"Failed to complete request to server -> {e}")
            st.stop()

        st.markdown(response.json()["msg"])

    st.session_state.messages.append(
        {"role": "assistant", "content": response.json()["msg"]}
    )

    if "update_view" in st.session_state and st.session_state.update_view:
        st.rerun()
