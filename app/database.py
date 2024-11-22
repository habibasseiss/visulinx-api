from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.settings import Settings

engine = create_engine(Settings().get_database_url())


def get_session():
    with Session(engine) as session:
        yield session
