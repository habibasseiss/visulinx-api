from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.settings import Settings

settings = Settings.model_validate({})
engine = create_engine(settings.get_database_url())


def get_session():
    with Session(engine) as session:
        yield session
