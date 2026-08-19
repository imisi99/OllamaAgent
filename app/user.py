import requests
import streamlit as st
import time
import logging

API_URL = "http://localhost:8000"


@st.dialog("Change your username")
def rename_user():
    st.session_state.active_dialog = ""

    if st.button("Go to Settings", type="tertiary"):
        st.session_state.active_dialog = "view_settings"
        st.rerun()

    new_name = st.text_input("Enter New Username")
    if st.button("Confirm", key="confirm_user_rename"):
        if new_name:
            with st.spinner():
                try:
                    rename_user = requests.put(
                        url=f"{API_URL}/user/"
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
                            (resp["msg"] if "msg" in resp else resp["detail"]),
                            duration=6,
                        )
                except Exception as e:
                    logging.error(f"Failed to complete request to the server -> {e}")
                    st.error(
                        "Failed to change username \n couldn't communicate with the server."
                    )


@st.dialog("View Memory")
def user_memory():
    st.session_state.active_dialog = ""

    if st.button("Go to Settings", type="tertiary"):
        st.session_state.active_dialog = "view_settings"
        st.rerun()

    if "user_memory" not in st.session_state:
        st.session_state.user_memory = {}

    with st.spinner():
        try:
            memory_req = requests.get(
                url=f"{API_URL}/user/me/" + st.session_state.user_id
            )

            if memory_req.status_code == 404:
                st.toast("Unable to find user.")

            elif memory_req.status_code == 200:
                st.session_state.user_memory = memory_req.json()["user"]["memory"]

            else:
                resp = memory_req.json()
                st.toast(
                    resp["msg"] if "msg" in resp else resp["detail"],
                    duration=6,
                )

        except Exception as e:
            logging.error(f"Failed to complete request to the server -> {e}")
            st.error("Failed to fetch memory \n couldn't communicate with the server.")

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
                                url=f"{API_URL}/user/"
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
                                    (resp["msg"] if "msg" in resp else resp["detail"]),
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
                            url=f"{API_URL}/user/"
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
                                (resp["msg"] if "msg" in resp else resp["detail"]),
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
    st.session_state.active_dialog = ""

    if st.button("Go to Settings", type="tertiary"):
        st.session_state.active_dialog = "view_settings"
        st.rerun()

    key = st.text_input("Enter the key")
    value = st.text_input("Enter the value")

    if st.button("Add Memory"):
        if key and value:
            with st.spinner():
                try:
                    add_mem_req = requests.put(
                        url=f"{API_URL}/user/"
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
                            (resp["msg"] if "msg" in resp else resp["detail"]),
                            duration=6,
                        )

                except Exception as e:
                    logging.error(f"Failed to complete request to the server -> {e}")
                    st.error(
                        "Failed to create memory \n couldn't communicate with the server."
                    )
