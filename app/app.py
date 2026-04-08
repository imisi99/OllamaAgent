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

# TODO: Use Expanded for the user profile settings probably


if "user_id" not in st.session_state:
    try:
        user_req = requests.get(url="http://server:8000/user")

        if user_req.status_code == 200:
            st.session_state.user_id = user_req.json()["id"]
            st.rerun()
        elif user_req.status_code == 404:
            st.info(user_req.json()["msg"])
            if prompt := st.chat_input("Create a new user"):
                try:
                    new_user_req = requests.post(
                        url="http://server:8000/user/create/" + prompt
                    )

                    if new_user_req.status_code == 200:
                        st.session_state.user_id = new_user_req.json()["id"]
                        st.rerun()
                    else:
                        st.error(new_user_req.json()["msg"])
                        st.stop()
                except Exception as e:
                    logging.error(
                        f"An error occured while making a request to the server -> {e}"
                    )
                    st.error("Failed to create a new user")
                    st.stop()
            else:
                st.info("You have to create a new user")
                st.stop()

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

    if st.button(
        "Ghost Chat",
        icon=":material/add:",
        type="tertiary",
        help="A new temporary session not stored",
    ):
        st.session_state.session_id = ""
        st.session_state.session_uid = ""
        st.session_state.ghost_session = True
        st.session_state.messages = []
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
                st.session_state.session_name = session["name"]
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
                        st.session_state.session_id = session["_id"]
                        st.session_state.session_uid = session["uuid"]
                        st.session_state.chat_holder = -1
                        st.session_state.messages = message_req.json()["session"][
                            "messages"
                        ]
                        st.rerun()

                except Exception as e:
                    logging.error(
                        f"An error occured while making a request to the server -> {e}"
                    )
                    st.error(f"Failed to complete request to server -> {e}")
                    st.stop()


if "chat_holder" not in st.session_state:
    st.session_state.chat_holder = random.randint(0, len(chat_holders) - 1)

if "ghost_session" not in st.session_state:
    st.session_state.ghost_session = False

if st.session_state.chat_holder != -1:
    st.subheader(chat_holders[st.session_state.chat_holder])

if "session_id" not in st.session_state:
    st.session_state.session_id = ""
    st.session_state.session_uid = ""
    st.session_state.session_name = ""
    st.session_state.messages = []

if st.session_state.session_id != "" and not st.session_state.ghost_session:
    with st.expander(label=st.session_state.session_name):
        if st.button("Rename"):
            if prompt := st.chat_input("Enter New Name"):
                try:
                    rename_req = requests.put(
                        url="http://server:8000/session/rename/"
                        + st.session_state.session_id
                        + "/"
                        + st.session_state.session_uid
                        + "?name="
                        + prompt
                    )

                    if rename_req.status_code == 202:
                        st.session_state.session_name = prompt
                        st.session_state.update_view = True
                        st.rerun()
                    else:
                        st.error(
                            f"Failed to rename session -> {rename_req.json()['msg']}"
                        )
                        st.stop()

                except Exception as e:
                    logging.error(
                        f"An error occured while making a request to the server -> {e}"
                    )
                    st.error(f"Failed to complete request to server -> {e}")
                    st.stop()

        if st.button("Delete"):
            try:
                delete_req = requests.delete(
                    url="http://server:8000/session/delete/"
                    + st.session_state.session_id
                    + "/"
                    + st.session_state.session_uid,
                )

                if delete_req.status_code == 200:
                    st.session_state.update_view = True
                    st.session_state.session_id = ""
                    st.session_state.session_uid = ""
                    st.session_state.messages = []
                    st.session_state.session_name = ""
                    st.rerun()
                else:
                    st.error(f"Failed to delete session -> {delete_req.json()['msg']}")
                    st.stop()

            except Exception as e:
                logging.error(
                    f"An error occured while making a request to the server -> {e}"
                )
                st.error(f"Failed to complete request to server -> {e}")
                st.stop()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("", key="chat", accept_file="multiple"):
    if st.session_state.session_id == "" and not st.session_state.ghost_session:
        try:
            new_session = requests.post(
                url="http://server:8000/session/create",
                json={"prompt": prompt.text},
            )

            if new_session.status_code != 201:
                st.error(f"Failed to start a new session, json -> {new_session.json()}")
                st.stop()

            st.session_state.session_id = new_session.json()["id"]
            st.session_state.session_uid = new_session.json()["uid"]
            st.session_state.chat_holder = -1
            st.session_state.update_view = True

        except Exception as e:
            logging.error(
                f"An error occured while making a request to the server -> {e}"
            )
            st.error(f"Failed to complete request to server -> {e}")
            st.stop()

    with st.chat_message("user"):
        if not st.session_state.ghost_session:
            try:
                add_msg_response = requests.put(
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

                if add_msg_response.status_code != 202:
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
                    "ghost_session": st.session_state.ghost_session,
                },
            )

            if response.status_code != 200:
                st.error("Failed to communicate with agent.")
                st.stop()

            if not st.session_state.ghost_session:
                add_msg_response = requests.put(
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

                if add_msg_response.status_code != 202:
                    st.error("Failed to communicate with agent.")
                    st.stop()

            st.markdown(response.json()["msg"])
            st.session_state.messages.append(
                {"role": "assistant", "content": response.json()["msg"]}
            )

        except Exception as e:
            logging.error(
                f"An error occured while making a request to the server -> {e}"
            )
            st.error(f"Failed to complete request to server -> {e}")
            st.stop()

    if st.session_state.get("update_view"):
        st.rerun()
