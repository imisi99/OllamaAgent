import requests
import time
import streamlit as st
import logging

API_URL = "http://server:8000"

logging.basicConfig(level=logging.INFO)


@st.dialog("Projects", width="medium")
def view_projects():
    st.session_state.active_dialog = ""

    if "projects" not in st.session_state:
        st.session_state.projects = []
        st.session_state.update_project_view = True

    if st.button("New Project", icon=":material/add:", type="tertiary"):
        st.session_state.active_dialog = "create_project"
        st.rerun()

    if st.session_state.get("update_project_view"):
        st.session_state.projects = []
        with st.spinner():
            try:
                projects_req = requests.get(url=f"{API_URL}/project/all")

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
                        st.stop()

            except Exception as e:
                logging.error(f"Failed to complete request to the server -> {e}")
                st.error("Failed to view projects... server error.")

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
                st.session_state.project_name = project["name"]
                st.session_state.project_goal = project["goal"]
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


@st.dialog("Project", width="large")
def view_project():
    st.session_state.active_dialog = ""

    if "project_session" not in st.session_state:
        st.session_state.project_session = []

    back, edit, delete = st.columns([7, 1, 1], vertical_alignment="top")
    if back.button("Go to Projects", type="tertiary"):
        st.session_state.active_dialog = "view_projects"
        st.rerun()

    if edit.button("Edit Project"):
        st.session_state.active_dialog = "edit_project"
        st.rerun()

    if delete.button("Delete Project", type="primary"):
        st.session_state.active_dialog = "delete_project"
        st.rerun()

    st.header(st.session_state.project_name)
    st.subheader(st.session_state.project_goal)

    add, rem, _ = st.columns([1, 1, 7], vertical_alignment="top")
    if add.button("Add Session", icon=":material/add:", type="tertiary"):
        st.session_state.active_dialog = "add_sessions"
        st.rerun()

    if rem.button("Remove Session", icon=":material/remove:", type="tertiary"):
        st.session_state.active_dialog = "remove_sessions"
        st.rerun()

    with st.spinner():
        st.session_state.project_session = []
        try:
            project_req = requests.get(
                url=f"{API_URL}/project/{st.session_state.project_id}"
            )

            match project_req.status_code:
                case 404:
                    st.info("This project doesn't exist")
                case 200:
                    st.session_state.project_session = project_req.json()["sessions"]
                case _:
                    resp = project_req.json()
                    st.toast(
                        (resp["msg"] if "msg" in resp else resp["detail"]),
                        duration=6,
                    )
                    st.stop()
        except Exception as e:
            logging.error(f"Failed to complete request to the server -> {e}")
            st.error("Failed to view project... server error.")

    for session in st.session_state.project_session:
        if st.button(session["name"]):
            try:
                message_req = requests.get(f"{API_URL}/session/" + session["_id"])

                match message_req.status_code:
                    case 200:
                        st.session_state.session_name = session["name"]
                        st.session_state.session_id = session["_id"]
                        st.session_state.session_uid = session["uuid"]
                        st.session_state.ghost_session = False
                        st.session_state.show_header = False
                        st.session_state.messages = message_req.json()["messages"]
                        st.rerun()
                    case 404:
                        st.toast("Session not found.")
                    case _:
                        resp = message_req.json()
                        st.toast(
                            resp["msg"] if "msg" in resp else resp["detail"],
                            duration=7,
                        )

            except Exception as e:
                logging.error(f"Failed to complete request to the server -> {e}")
                st.error("Failed to fetch session... server error.")


@st.dialog("Create Project", width="medium")
def create_project():
    st.session_state.active_dialog = ""

    if st.button("Go to Projects", type="tertiary"):
        st.session_state.active_dialog = "view_projects"
        st.rerun()

    name = st.text_input("Project name")
    goal = st.text_input("Project goal")

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
                            st.session_state.project_name = name
                            st.session_state.project_goal = goal
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
                    st.error("Failed to create new project... server error.")


@st.dialog("Edit Project", width="medium")
def edit_project():
    st.session_state.active_dialog = ""

    if st.button("Go to Project", type="tertiary"):
        st.session_state.active_dialog = "view_project"
        st.rerun()

    name = st.text_input("Project name", value=st.session_state.project_name)
    goal = st.text_input("Project goal", value=st.session_state.project_goal)

    with st.container(horizontal=True, horizontal_alignment="right"):
        if st.button("edit", type="primary"):
            with st.spinner("editing"):
                try:
                    project_req = requests.put(
                        url=f"{API_URL}/project/edit/{st.session_state.project_id}",
                        json={
                            "name": name,
                            "goal": goal,
                        },
                    )

                    match project_req.status_code:
                        case 202:
                            st.toast("Project edit successfully")
                            st.session_state.update_project_view = True
                            st.session_state.project_goal = goal
                            st.session_state.project_name = name
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
                    st.error("Failed to edit project... server error.")


@st.dialog("Add Session", width="medium")
def add_session_to_project():
    st.session_state.active_dialog = ""
    st.session_state.exclude_sessions = []

    try:
        get_req = requests.get(
            url=f"{API_URL}/session/preview/exclude/{st.session_state.project_id}"
        )

        match get_req.status_code:
            case 200:
                st.session_state.exclude_sessions = get_req.json()["sessions"]
            case _:
                resp = get_req.json()
                st.toast(resp["msg"] if "msg" in resp else resp["detail"], duration=6)

    except Exception as e:
        logging.error(f"Failed to complete request to the server -> {e}")
        st.error("Failed to fetch sessions... server error")

    if st.button("Go to Project", type="tertiary"):
        st.session_state.active_dialog = "view_project"
        st.rerun()

    if st.button("New Session", icon=":material/add:", type="tertiary"):
        st.session_state.session_id = ""
        st.session_state.session_uid = ""
        st.session_state.show_header = True
        st.session_state.messages = []
        st.rerun()

    ids = []
    if st.session_state.exclude_sessions:
        st.write("Select sessions to add")
        for session in st.session_state.exclude_sessions:
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
                                    resp["msg"] if "msg" in resp else resp["detail"],
                                    duration=6,
                                )

                    except Exception as e:
                        logging.error(
                            f"Failed to complete request to the server -> {e}"
                        )
                        st.error("Failed to add sessions to project... server error.")


@st.dialog("Remove Session", width="medium")
def remove_session_from_project():
    st.session_state.active_dialog = ""

    if st.button("Go to Project", type="tertiary"):
        st.session_state.active_dialog = "view_project"
        st.rerun()

    ids = []
    if st.session_state.project_session:
        st.write("Select sessions to remove")
        for session in st.session_state.project_session:
            if st.checkbox(session["name"]):
                ids.append(session["_id"])

    if ids:
        with st.container(horizontal=True, horizontal_alignment="right"):
            if st.button("remove", type="primary"):
                with st.spinner():
                    try:
                        project_req = requests.delete(
                            url=f"{API_URL}/project/remove/{st.session_state.project_id}",
                            json={"ids": ids},
                        )

                        match project_req.status_code:
                            case 202:
                                st.toast("sessions removed successfully")
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
                            "Failed to remove sessions from project... server error."
                        )


@st.dialog("Delete Project", width="medium")
def delete_project():
    st.session_state.active_dialog = ""

    if st.button("Go to Project", type="tertiary"):
        st.session_state.active_dialog = "view_project"
        st.rerun()

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
                        st.error("Failed to remove delete project... server error.")
    else:
        st.error("Invalid name")
