from http import HTTPStatus

from fastapi.testclient import TestClient


def test_list_organizations(client: TestClient, token: str):
    response = client.get(
        '/organizations/',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == HTTPStatus.OK
    assert 'organizations' in response.json()


# def test_create_organization(client: TestClient, token: str):
#     response = client.post(
#         '/organizations/',
#         headers={'Authorization': f'Bearer {token}'},
#         json={'name': 'Test Organization'},
#     )
#     assert response.status_code == HTTPStatus.CREATED

#     data = response.json()
#     assert data['name'] == 'Test Organization'
