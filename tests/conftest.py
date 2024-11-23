from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import Connection
from sqlalchemy.engine.base import Transaction
from sqlalchemy.orm import Session, clear_mappers, scoped_session, sessionmaker

from app.api import api
from app.database import get_session
from app.models import User, table_registry
from app.security import get_password_hash


@pytest.fixture(scope='session')
def engine() -> Generator[Engine, None, None]:
    """
    Creates a SQLAlchemy engine instance connected to an in-memory SQLite
    database.
    """
    engine = create_engine(
        'sqlite:///:memory:', connect_args={'check_same_thread': False}
    )
    table_registry.metadata.create_all(engine)  # Create all tables
    yield engine
    table_registry.metadata.drop_all(engine)  # Cleanup after tests


@pytest.fixture
def session(engine: Engine) -> Generator[Session, None, None]:
    """
    Provides a scoped session for database interactions during tests.
    Rolls back changes after each test to keep the database clean.
    """
    connection: Connection = engine.connect()
    transaction: Transaction = connection.begin()
    session_factory = sessionmaker(bind=connection)
    Session = scoped_session(session_factory)
    session = Session()

    yield session  # This is the session your tests will use

    session.close()
    transaction.rollback()
    connection.close()
    Session.remove()


@pytest.fixture
def setup_database(engine: Engine) -> Generator[None, None, None]:
    """
    Optional fixture to prepare the database with test data before each test.
    """
    clear_mappers()
    table_registry.metadata.create_all(engine)
    yield
    table_registry.metadata.drop_all(engine)


@pytest.fixture
def client(session: Session) -> Generator[TestClient, None, None]:
    def get_session_override():
        return session

    with TestClient(api) as client:
        api.dependency_overrides[get_session] = get_session_override
        yield client

    api.dependency_overrides.clear()


@pytest.fixture
def user(session: Session) -> User:
    user = User(  # type: ignore
        email='test@example.com',
        password=get_password_hash('securepassword'),
    )

    session.add(user)
    session.commit()
    session.refresh(user)

    user.clean_password = 'securepassword'  # type: ignore

    return user


@pytest.fixture
def token(client: TestClient, user: User) -> str:
    response = client.post(
        '/auth/token',
        data={
            'username': user.email,
            'password': user.clean_password,  # type: ignore
        },
    )
    return response.json()['access_token']
