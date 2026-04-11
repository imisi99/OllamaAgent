import logging
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from starlette import status

from core.mongo import Database
from db.mongo import get_mongo_database
from schemas.user import UpdateMemory

user = APIRouter()


@user.get("/user")
def get_user_id(db: Database = Depends(get_mongo_database)):
    try:
        id = db.fetch_user_id()
        if id is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"msg": "User not found."},
            )

        return JSONResponse(status_code=status.HTTP_200_OK, content={"id": id})

    except Exception as e:
        logging.error(f"An error occured while trying to get user id -> {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"msg": "Failed to retrieve user id."},
        )


@user.post("/user/create/{username}")
def create_user(username: str, db: Database = Depends(get_mongo_database)):
    try:
        id, created = db.create_user(username)
        if not created:
            raise Exception("MongoDB operation to create user not acknowledged")

        return JSONResponse(status_code=status.HTTP_201_CREATED, content={"id": id})

    except Exception as e:
        logging.error(f"An error occured while trying to create new user -> {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"msg": "Failed to create new user."},
        )


@user.get("/user/me/{id}")
def get_user(id: str, db: Database = Depends(get_mongo_database)):
    try:
        user = db.fetch_user(id)
        if user is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"msg": "User not found."},
            )

        return JSONResponse(status_code=status.HTTP_200_OK, content={"user": user})

    except Exception as e:
        logging.error(f"An error occured while trying to retrieve user -> {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"msg": "Failed to retrieve user."},
        )


@user.put("/user/{id}/update/memory")
def update_memory(
    id: str, memory: UpdateMemory, db: Database = Depends(get_mongo_database)
):
    try:
        updated = db.update_user_memory(id, memory.key, memory.value)
        if not updated:
            raise Exception("MongoDB operation to update memory not acknowledged")

        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED, content={"msg": "memory updated."}
        )

    except Exception as e:
        logging.error(f"An error occured while trying to update memory -> {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"msg": "Failed to update memory."},
        )


@user.put("/user/{id}/update/{name}")
def update_username(id: str, name: str, db: Database = Depends(get_mongo_database)):
    try:
        updated = db.update_user_name(id, name)
        if not updated:
            raise Exception("MongoDB operation to update username not acknowledged")

        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED, content={"msg": "username updated."}
        )

    except Exception as e:
        logging.error(f"An error occured while trying to update username -> {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"msg": "Failed to update username."},
        )


@user.delete("/user/{id}/delete/memory/{key}")
def delete_memory(id: str, key: str, db: Database = Depends(get_mongo_database)):
    try:
        deleted = db.remove_user_memory(id, key)
        if not deleted:
            raise Exception(
                "MongoDB operation to remove a key from memory not acknowledged"
            )

        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED, content={"msg": "memory updated."}
        )

    except Exception as e:
        logging.error(f"An error occured while trying to update memory -> {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"msg": "Failed to update memory."},
        )
