from datetime import datetime
from starlette import status
import logging
import random
import requests
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
        st.session_state.messages = []
        st.session_state.chat_holder = random.randint(0, len(chat_holders) - 1)
        st.rerun()

    else:
        sessions_req = requests.get(url="http://localhost:8000/session/all")
        if sessions_req.status_code == status.HTTP_404_NOT_FOUND:
            st.info("you have no existing session \n start a new session !")

        elif sessions_req.status_code != 200:
            logging.error(
                f"Failed to fetch available sessions from db, status_code -> {sessions_req.status_code}, json -> {sessions_req.json()}"
            )
            st.error("Failed to fetch sessions.")

        else:
            sessions = sessions_req.json()["sessions"]
            for session in sessions:
                if st.button(session["name"]):
                    st.session_state.session_id = session["_id"]
                    st.session_state.chat_holder = -1
                    st.session_state.messages = session["messages"]
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
    # New chat will have a empty session id in the state
    if st.session_state.session_id == "":
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

        if new_session.status_code != status.HTTP_200_OK:
            logging.error(
                f"Failed to create a new session, status_code -> {new_session.status_code}, json -> {new_session.json()}"
            )
            st.error("Failed to start a new session.")
            st.stop()
        st.session_state.session_id = new_session.json()["id"]

    st.session_state.messages.append({"role": "user", "content": prompt.text})
    with st.chat_message("user"):
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
        st.markdown(prompt.text)

    with st.chat_message("assistant"):
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

        st.markdown(response.json()["msg"])

    st.session_state.messages.append(
        {"role": "assistant", "content": response.json()["msg"]}
    )
