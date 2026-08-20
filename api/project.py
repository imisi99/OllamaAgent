import logging
import datetime
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from starlette import status

from core.mongo import Database
from db.mongo import get_mongo_database
from schemas.mongo import Project
from schemas.project import (
    CreateProject,
    UpdateProjectSession,
)

project = APIRouter()


@project.post("/project/create")
def create_project(payload: CreateProject, db: Database = Depends(get_mongo_database)):
    try:
        project: Project = {
            "_id": "",
            "name": payload.name,
            "goal": payload.goal,
            "created_at": datetime.datetime.now(),
        }

        err, id = db.create_project(project)
        if err:
            return JSONResponse(content={"msg": err.message}, status_code=err.code)

        return JSONResponse(status_code=status.HTTP_201_CREATED, content={"id": id})

    except Exception as e:
        logging.error(f"Failed to create project, An error occured -> {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"msg": f"Failed to create the project -> {e}."},
        )


@project.put("/project/edit/{project_id}")
def edit_project(
    project_id: str, payload: CreateProject, db: Database = Depends(get_mongo_database)
):
    try:
        err = db.edit_project_details(payload.name, payload.goal, project_id)
        if err:
            return JSONResponse(content={"msg": err.message}, status_code=err.code)
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={"msg": "Project updated successfully."},
        )
    except Exception as e:
        logging.error(f"Failed to edit project, An error occured -> {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"msg": f"Failed to edit the project -> {e}."},
        )


@project.get("/project/all")
def get_projects(db: Database = Depends(get_mongo_database)):
    try:
        projects = db.fetch_projects()

        if len(projects) == 0:
            return JSONResponse(
                content={"msg": "No project found."},
                status_code=status.HTTP_404_NOT_FOUND,
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK, content={"projects": projects}
        )

    except Exception as e:
        logging.error(f"Failed to retrieve projects, An error occured -> {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"msg": f"Failed to retrieve projects -> {e}."},
        )


@project.get("/project/{project_id}")
def get_project(project_id: str, db: Database = Depends(get_mongo_database)):
    try:
        err, project, sessions = db.fetch_project(project_id)

        if err:
            return JSONResponse(content={"msg": err.message}, status_code=err.code)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"project": project, "sessions": sessions},
        )

    except Exception as e:
        logging.error(f"Failed to retrieve project, An error occured -> {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"msg": f"Failed to retrieve project -> {e}."},
        )


@project.get("/project/all/exclude/{project_id}")
def get_projects_exclude(project_id: str, db: Database = Depends(get_mongo_database)):
    try:
        projects = db.fetch_all_project_exclude_one(project_id)

        if len(projects) == 0:
            return JSONResponse(
                content={"msg": "No project found."},
                status_code=status.HTTP_404_NOT_FOUND,
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK, content={"projects": projects}
        )

    except Exception as e:
        logging.error(f"Failed to retrieve projects, An error occured -> {e}")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"msg": f"Failed to retrieve projects -> {e}."},
        )


@project.put("/project/add/{project_id}")
def add_to_project(
    session: UpdateProjectSession,
    project_id: str,
    db: Database = Depends(get_mongo_database),
):
    try:
        err = db.add_session_to_project(session.ids, project_id)

        if err:
            return JSONResponse(content={"msg": err.message}, status_code=err.code)

        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={"msg": "Session added to project."},
        )

    except Exception as e:
        logging.error(f"Failed to update project to add session -> {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"msg": f"Failed to add session to project -> {e}."},
        )


@project.delete("/project/remove/{project_id}")
def remove_from_project(
    session: UpdateProjectSession,
    project_id: str,
    db: Database = Depends(get_mongo_database),
):
    try:
        err = db.remove_session_from_project(session.ids, project_id)

        if err:
            return JSONResponse(content={"msg": err.message}, status_code=err.code)

        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={"msg": "Session removed from project."},
        )

    except Exception as e:
        logging.error(f"Failed to update project to remove session -> {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"msg": f"Failed to remove session from project -> {e}."},
        )


@project.delete("/project/delete/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, db: Database = Depends(get_mongo_database)):
    try:
        err = db.delete_project(project_id)

        if err:
            return JSONResponse(content={"msg": err.message}, status_code=err.code)

        return None

    except Exception as e:
        logging.error(f"Failed to delete proejct -> {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"msg": f"Failed to delete project -> {e}."},
        )
