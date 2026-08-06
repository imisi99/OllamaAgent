import requests
import streamlit as st
import logging

from .app import API_URL


@st.dialog("Projects")
def view_projects():
    if "projects" not in st.session_state or st.session_state.get(
        "update_project_view"
    ):
        with st.spinner():
            try:
                projects_req = requests.get(url=f"{API_URL}/session/project/all")

                match projects_req.status_code:
                    case 404:
                        st.info("You have no existing project create one.")
                    case 200:
                        st.session_state.projects = projects_req.json()["projects"]
                        st.session_state.update_project_view = False
                    case _:
                        resp = projects_req.json()
                        st.toast(
                            (resp["msg"] if "msg" in resp else resp["detail"]),
                            duration=6,
                        )

            except Exception as e:
                logging.error(f"Failed to complete request to the server -> {e}")
                st.error(
                    "Failed to view projects \n couldn't communicate with the server."
                )

    if st.session_state.get("projects"):
        for project in st.session_state.projects:
            with st.expander(project["name"]):
                goal, open_sess = st.columns([4, 1], vertical_alignment="center")
                goal.write(project["goal"])
                if open_sess.button(
                    "view",
                    key=project["_id"],
                    type="primary",
                    use_container_width=True,
                ):
                    st.session_state.project_id = project["_id"]
                    st.session_state.view_project_dialog = True
                    st.rerun()


@st.dialog("Project")
def view_project():
    if st.session_state.get("loaded_project_id") != st.session_state.project_id:
        with st.spinner():
            try:
                project_req = requests.get(
                    url=f"{API_URL}/session/project/{st.session_state.project_id}"
                )

                match project_req.status_code:
                    case 404:
                        st.info("This project doesn't exist")
                    case 200:
                        (
                            st.session_state.loaded_project_id,
                            st.session_state.project_session,
                        ) = (
                            project_req.json()["project"]["_id"],
                            project_req.json()["sessions"],
                        )
                    case _:
                        resp = project_req.json()
                        st.toast(
                            (resp["msg"] if "msg" in resp else resp["detail"]),
                            duration=6,
                        )
            except Exception as e:
                logging.error(f"Failed to complete request to the server -> {e}")
                st.error(
                    "Failed to view project \n couldn't communicate with the server."
                )

    st.session_state.view_project_dialog = False

    if st.session_state.get("project_session"):
        for session in st.session_state.project_session:
            if st.button(session["name"]):
                pass


@st.dialog("Create Project")
def create_project():
    name = st.text_input("Project name")
    goal = st.text_input("Project goal")

    # TODO: Maybe add a view sessions ? search session by name to add to the project when created

    if st.button("create project"):
        with st.spinner():
            try:
                project_req = requests.post(
                    url=f"{API_URL}/session/project/create",
                    json={
                        "name": name,
                        "goal": goal,
                    },
                )

                match project_req.status_code:
                    case 201:
                        st.toast("project created successfully")
                        st.session_state.project_id = project_req.json()["id"]
                        st.session_state.update_project_view = True
                        st.rerun()
                    case _:
                        resp = project_req.json()
                        st.toast(
                            (resp["msg"] if "msg" in resp else resp["detail"]),
                            duration=6,
                        )

            except Exception as e:
                logging.error(f"Failed to complete request to the server -> {e}")
                st.error(
                    "Failed to create new project \n couldn't communicate with the server."
                )


@st.dialog("Add Session")
def add_session_to_project():
    # TODO: Add the sessions ? how when element ?
    ids = []
    if st.button("add sessions"):
        with st.spinner():
            try:
                project_req = requests.put(
                    url=f"{API_URL}/session/project/add/{st.session_state.project_id}",
                    json={"ids": ids},
                )

                match project_req.status_code:
                    case 202:
                        st.toast("sessions added successfully")
                    case _:
                        resp = project_req.json()
                        st.toast(
                            (resp["msg"] if "msg" in resp else resp["detail"]),
                            duration=6,
                        )

            except Exception as e:
                logging.error(f"Failed to complete request to the server -> {e}")
                st.error(
                    "Failed to add sessions to project \n couldn't communicate with the server."
                )


@st.dialog("Remove Session")
def remove_session_from_project():
    # TODO: Fetch sessions currently in project
    ids = []
    if st.button("remove sessions"):
        with st.spinner():
            try:
                project_req = requests.delete(
                    url=f"{API_URL}/session/project/remove/{st.session_state.project_id}",
                    json={"ids": ids},
                )

                match project_req.status_code:
                    case 202:
                        st.toast("sessions removed successfully")
                    case _:
                        resp = project_req.json()
                        st.toast(
                            (resp["msg"] if "msg" in resp else resp["detail"]),
                            duration=6,
                        )

            except Exception as e:
                logging.error(f"Failed to complete request to the server -> {e}")
                st.error(
                    "Failed to remove sessions from project \n couldn't communicate with the server."
                )


@st.dialog("Delete Project")
def delete_project():
    st.popover("Deleting this will remove all the sessions from this project!")
    project_name = st.text_input("Enter the project name.")
    if st.button("delete project") and project_name == st.session_state.project_name:
        with st.spinner():
            try:
                project_req = requests.delete(
                    url=f"{API_URL}/session/project/delete/{st.session_state.project_id}",
                )

                match project_req.status_code:
                    case 204:
                        st.toast("project deleted successfully")
                    case _:
                        resp = project_req.json()
                        st.toast(
                            (resp["msg"] if "msg" in resp else resp["detail"]),
                            duration=6,
                        )

            except Exception as e:
                logging.error(f"Failed to complete request to the server -> {e}")
                st.error(
                    "Failed to remove delete project \n couldn't communicate with the server."
                )
