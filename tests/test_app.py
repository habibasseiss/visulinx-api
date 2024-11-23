from http import HTTPStatus

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def test_app_root(client: TestClient, session: Session):
    response = client.get('/')

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'message': 'hello'}
