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

if "user_id" not in st.session_state:
    try:
        user_req = requests.get(url="http://server:8000/user")

        if user_req.status_code == 200:
            st.session_state.user_id = user_req.json()["id"]
            st.rerun()
        elif user_req.status_code == 404:
            st.info(user_req.json()["msg"])
            if prompt := st.chat_input("Create a new user"):
                pass
        else:
            st.error("Failed to retrieve user.")
            st.stop()

    except Exception as e:
        logging.error(f"An error occured while making a request to the server -> {e}")
        st.error(f"Failed to complete request to server -> {e}")
        st.stop()


with st.sidebar:
    if st.button(
        "New Chat",
        icon=":material/add:",
        type="tertiary",
    ):
        st.session_state.session_id = ""
        st.session_state.session_uid = ""
        st.session_state.messages = []
        st.session_state.chat_holder = random.randint(0, len(chat_holders) - 1)
        st.rerun()

    if "sessions_fetched" not in st.session_state or st.session_state.get(
        "update_view"
    ):
        try:
            sessions_req = requests.get(url="http://server:8000/session/all/preview")
            if sessions_req.status_code == 404:
                st.info("you have no existing session \n start a new session")

            elif sessions_req.status_code != 200:
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

        st.session_state.sessions_fetched = True
        st.session_state.update_view = False

    if st.session_state.get("sessions"):
        for session in reversed(st.session_state.sessions):
            if st.button(session["name"], use_container_width=True):
                active_session = None
                try:
                    message_req = requests.get(
                        "http://server:8000/session/" + session["_id"]
                    )

                    if message_req.status_code == 404:
                        st.error(message_req.json()["msg"])
                        st.stop()

                    elif message_req.status_code != 200:
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
                st.session_state.session_uid = session["uuid"]
                st.session_state.chat_holder = -1
                st.session_state.messages = active_session["messages"]
                st.rerun()

if "chat_holder" not in st.session_state:
    st.session_state.chat_holder = random.randint(0, len(chat_holders) - 1)

if st.session_state.chat_holder != -1:
    st.subheader(chat_holders[st.session_state.chat_holder])

if "session_id" not in st.session_state:
    st.session_state.session_id = ""
    st.session_state.session_uid = ""
    st.session_state.messages = []

if "messages" in st.session_state:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

if prompt := st.chat_input("", key="chat", accept_file="multiple"):
    if st.session_state.session_id == "":
        try:
            new_session = requests.post(
                url="http://server:8000/session/create",
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
                st.error("Failed to start a new session.")
                st.stop()
        except Exception as e:
            logging.error(
                f"An error occured while making a request to the server -> {e}"
            )
            st.error(f"Failed to complete request to server -> {e}")
            st.stop()
        st.session_state.session_id = new_session.json()["id"]
        st.session_state.session_uid = new_session.json()["uid"]
        st.session_state.chat_holder = -1
        st.session_state.update_view = True

    with st.chat_message("user"):
        try:
            add_msg_response = requests.post(
                url="http://server:8000/session/msg/"
                + st.session_state.session_id
                + "/"
                + st.session_state.session_uid,
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
                url="http://server:8000/agent/chat",
                json={
                    "session_id": st.session_state.session_id,
                    "user_id": st.session_state.user_id,
                    "message": {
                        "role": "user",
                        "content": prompt.text,
                        "timestamp": datetime.now().isoformat(),
                    },
                },
            )

            if response.status_code != 200:
                st.error("Failed to communicate with agent.")
                st.stop()

            add_msg_response = requests.post(
                url="http://server:8000/session/msg/"
                + st.session_state.session_id
                + "/"
                + st.session_state.session_uid,
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

    if st.session_state.get("update_view"):
        st.rerun()
