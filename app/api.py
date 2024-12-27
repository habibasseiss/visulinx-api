from http import HTTPStatus

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, organizations, preferences, projects, users
from app.schemas import Message
from app.settings import Settings

settings = Settings.model_validate({})
api = FastAPI()


# Configure CORS
api.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_origins(),
    allow_credentials=True,
    allow_methods=['*'],  # Allows all methods
    allow_headers=['*'],  # Allows all headers
)

api.include_router(users.router)
api.include_router(auth.router)
api.include_router(organizations.router)
api.include_router(projects.router)
api.include_router(preferences.router)


@api.get('/', status_code=HTTPStatus.OK, response_model=Message)
def read_root():
    return {'message': 'hello'}
