"""认证接口测试。"""

from __future__ import annotations


class TestAuthLogin:
    def test_login_success(self, client, test_user) -> None:
        response = client.post(
            "/api/auth/login",
            json={"username": "tester", "password": "test1234"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["code"] == 200
        assert body["data"]["access_token"]
        assert body["data"]["user"]["username"] == "tester"

    def test_login_wrong_password(self, client, test_user) -> None:
        response = client.post(
            "/api/auth/login",
            json={"username": "tester", "password": "wrong"},
        )
        assert response.status_code == 401

    def test_forgot_password_resets(self, client, test_user) -> None:
        response = client.post(
            "/api/auth/forgot-password",
            json={
                "username_or_email": "tester",
                "new_password": "newpass1234",
            },
        )
        assert response.status_code == 200
        login = client.post(
            "/api/auth/login",
            json={"username": "tester", "password": "newpass1234"},
        )
        assert login.status_code == 200
