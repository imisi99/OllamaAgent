import requests
import time
import streamlit as st
import logging

from session import view_all_sessions_preview

API_URL = "http://localhost:8000"

logging.basicConfig(level=logging.INFO)


@st.dialog("Projects")
def view_projects():
    st.session_state.active_dialog = ""

    if st.button("New Project", icon=":material/add:", type="tertiary"):
        st.session_state.active_dialog = "create_project"
        st.rerun()

    if "projects" not in st.session_state or st.session_state.get(
        "update_project_view"
    ):
        with st.spinner():
            try:
                projects_req = requests.get(url=f"{API_URL}/project/all")

                match projects_req.status_code:
                    case 404:
                        st.info("You have no existing project create one.")
                        st.stop()
                    case 200:
                        st.session_state.projects = projects_req.json()["projects"]
                        st.session_state.update_project_view = False
                    case _:
                        resp = projects_req.json()
                        st.toast(
                            (resp["msg"] if "msg" in resp else resp["detail"]),
                            duration=6,
                        )
                        st.stop()

            except Exception as e:
                logging.error(f"Failed to complete request to the server -> {e}")
                st.error(
                    "Failed to view projects ... couldn't communicate with the server."
                )

    for project in st.session_state.projects:
        with st.expander(project["name"]):
            goal, open_proj, del_proj = st.columns(
                [4, 1, 1], vertical_alignment="center"
            )
            goal.write(project["goal"])
            if open_proj.button(
                "view",
                key=project["_id"],
                use_container_width=True,
            ):
                st.session_state.project_id = project["_id"]
                st.session_state.active_dialog = "view_project"
                st.rerun()
            if del_proj.button(
                "del",
                key="del" + project["_id"],
                type="primary",
                use_container_width=True,
            ):
                st.session_state.project_id = project["_id"]
                st.session_state.project_name = project["name"]
                st.session_state.active_dialog = "delete_project"
                st.rerun()


@st.dialog("Project")
def view_project():
    st.session_state.active_dialog = ""

    if st.button("Add Session", icon=":material/add:", type="tertiary"):
        st.session_state.active_dialog = "add_sessions"
        st.rerun()

    if st.session_state.get("loaded_project_id") != st.session_state.project_id:
        with st.spinner():
            try:
                project_req = requests.get(
                    url=f"{API_URL}/project/{st.session_state.project_id}"
                )

                match project_req.status_code:
                    case 404:
                        st.info("This project doesn't exist")
                        st.stop()
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
                        st.stop()
            except Exception as e:
                logging.error(f"Failed to complete request to the server -> {e}")
                st.error(
                    "Failed to view project... couldn't communicate with the server."
                )

    for session in st.session_state.project_session:
        if st.button(session["name"]):
            pass


@st.dialog("Create Project")
def create_project():
    st.session_state.active_dialog = ""
    name = st.text_input("Project name")
    goal = st.text_input("Project goal")

    # TODO: Maybe add a view sessions ? search session by name to add to the project when created

    with st.container(horizontal=True, horizontal_alignment="right"):
        if st.button("create", type="primary"):
            with st.spinner("creating"):
                try:
                    project_req = requests.post(
                        url=f"{API_URL}/project/create",
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
                            st.session_state.active_dialog = "view_project"
                            time.sleep(0.8)
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
                        "Failed to create new project... couldn't communicate with the server."
                    )


@st.dialog("Edit Project")
def edit_project():
    st.session_state.active_dialog = ""
    name = st.text_input("Project name", value=st.session_state.project_name)
    goal = st.text_input("Project goal", value=st.session_state.project_goal)

    with st.container(horizontal=True, horizontal_alignment="right"):
        if st.button("edit", type="primary"):
            with st.spinner("editing"):
                try:
                    project_req = requests.put(
                        url=f"{API_URL}/project/edit",
                        json={
                            "name": name,
                            "goal": goal,
                        },
                    )

                    match project_req.status_code:
                        case 202:
                            st.toast("Project edit successfully")
                            st.session_state.update_s_project_view = True
                            st.session_state.active_dialog = "view_project"
                            time.sleep(0.8)
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
                        "Failed to edit project... couldn't communicate with the server."
                    )


@st.dialog("Add Session")
def add_session_to_project():
    st.session_state.active_dialog = ""
    view_all_sessions_preview()

    if st.button("Create Session", icon=":material/add:", type="tertiary"):
        st.session_state.active_dialog = "create_session"
        st.rerun()

    ids = []
    if st.session_state.sessions:
        st.write("Select sessions to add")
        for session in st.session_state.sessions:
            if st.checkbox(session["name"]):
                ids.append(session["_id"])

    if ids:
        with st.container(horizontal=True, horizontal_alignment="right"):
            if st.button("add", type="primary"):
                with st.spinner():
                    try:
                        project_req = requests.put(
                            url=f"{API_URL}/project/add/{st.session_state.project_id}",
                            json={"ids": ids},
                        )

                        match project_req.status_code:
                            case 202:
                                st.toast("sessions added successfully")
                                st.session_state.active_dialog = "view_project"
                                time.sleep(0.8)
                                st.rerun()
                            case _:
                                resp = project_req.json()
                                st.toast(
                                    (resp["msg"] if "msg" in resp else resp["detail"]),
                                    duration=6,
                                )

                    except Exception as e:
                        logging.error(
                            f"Failed to complete request to the server -> {e}"
                        )
                        st.error(
                            "Failed to add sessions to project... couldn't communicate with the server."
                        )


@st.dialog("Remove Session")
def remove_session_from_project():
    for session in st.session_state.project_session:
        if st.button(session["name"]):
            pass
    ids = []
    if st.button("remove sessions"):
        with st.spinner():
            try:
                project_req = requests.delete(
                    url=f"{API_URL}/project/remove/{st.session_state.project_id}",
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
                    "Failed to remove sessions from project... couldn't communicate with the server."
                )


@st.dialog("Delete Project")
def delete_project():
    st.session_state.active_dialog = ""
    st.warning(
        "Deleting this will remove all the sessions from this project but not delete them!"
    )
    st.subheader(st.session_state.project_name)
    project_name = st.text_input("Enter the project name.")
    if project_name == st.session_state.project_name:
        with st.container(horizontal=True, horizontal_alignment="right"):
            if st.button("delete", type="primary"):
                with st.spinner("deleting"):
                    try:
                        project_req = requests.delete(
                            url=f"{API_URL}/project/delete/{st.session_state.project_id}",
                        )

                        match project_req.status_code:
                            case 204:
                                st.session_state.active_dialog = "view_projects"
                                st.session_state.update_project_view = True
                                st.toast("project deleted successfully")
                                time.sleep(0.8)
                                st.rerun()
                            case _:
                                resp = project_req.json()
                                st.toast(
                                    (resp["msg"] if "msg" in resp else resp["detail"]),
                                    duration=6,
                                )

                    except Exception as e:
                        logging.error(
                            f"Failed to complete request to the server -> {e}"
                        )
                        st.error(
                            "Failed to remove delete project... couldn't communicate with the server."
                        )
    else:
        st.error("Invalid name")
