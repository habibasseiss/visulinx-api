from http import HTTPStatus

from fastapi import FastAPI

from app.routers import auth, todos, users
from app.schemas import Message

api = FastAPI()

api.include_router(users.router)
api.include_router(auth.router)
api.include_router(todos.router)


@api.get('/', status_code=HTTPStatus.OK, response_model=Message)
def read_root():
    return {'message': 'hello'}
