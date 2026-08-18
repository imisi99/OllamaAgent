import streamlit as st
import requests
import time
import logging

API_URL = "http://localhost:8000"


@st.dialog("Rename Session")
def rename_sess():
    new_name = st.text_input("Enter New Name", value=st.session_state.session_name)
    if st.button("Confirm", key="confirm_rename"):
        if new_name:
            with st.spinner():
                try:
                    rename_req = requests.put(
                        url=f"{API_URL}/session/rename/"
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
                            resp["msg"] if "msg" in resp else resp["detail"],
                            duration=6,
                        )

                except Exception as e:
                    logging.error(f"Failed to complete request to the server -> {e}")
                    st.error("Failed to rename session... server error")


@st.dialog("Delete Session")
def delete_sess():
    if st.button("Confirm", key="confirm_delete"):
        with st.spinner():
            try:
                delete_req = requests.delete(
                    url=f"{API_URL}/session/delete/"
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
                logging.error(f"Failed to complete request to the server -> {e}")
                st.error("Failed to delete session... server error")


@st.dialog("Find Similar Sessions")
def find_similar_sess():
    threshold = st.number_input(
        "Enter threshold", min_value=0.0, max_value=1.0, value=0.5
    )
    limit = st.number_input("Enter limit", min_value=1, max_value=100, value=5)
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

                    similar_col1, similar_col2 = st.columns([4, 1])
                    for sess in sessions:
                        with similar_col1:
                            load_sess_id = sess[0]["_id"]
                            load_sess_uid = sess[0]["uuid"]
                            if st.button(sess[0]["name"]):
                                try:
                                    message_req = requests.get(
                                        url=f"{API_URL}/session/" + load_sess_id,
                                    )

                                    resp = message_req.json()

                                    if message_req.status_code == 200:
                                        st.session_state.session_id = load_sess_id
                                        st.session_state.session_uid = load_sess_uid
                                        st.session_state.ghost_session = False
                                        st.session_state.show_header = False
                                        st.session_state.messages = resp["session"][
                                            "messages"
                                        ]
                                        st.session_state.find_session = False
                                        st.session_state.session_name = resp["session"][
                                            "name"
                                        ]
                                        st.rerun()
                                    else:
                                        st.toast(
                                            (
                                                resp["msg"]
                                                if "msg" in resp
                                                else resp["detail"]
                                            ),
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
                    st.info(resp["msg"] if "msg" in resp else resp["detail"])
            except Exception as e:
                logging.error(f"Failed to complete request to the server -> {e}")
                st.error("Failed to find similar sessions... server error")


def remove_active_session_from_sessions():
    for session in st.session_state.sessions:
        if session["_id"] == st.session_state.session_id:
            st.session_state.sessions.remove(session)
