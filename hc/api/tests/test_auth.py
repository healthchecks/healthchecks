from __future__ import annotations


from unittest.mock import Mock, patch
from hc.test import BaseTestCase, TestHttpResponse


class AuthTestCase(BaseTestCase):
    def get(self, key: str) -> TestHttpResponse:
        return self.client.get("/api/v1/checks/", HTTP_X_API_KEY=key)

    def post(self, key: str) -> TestHttpResponse:
        return self.client.post(
            "/api/v1/checks/",
            {"name": "Foo"},
            content_type="application/json",
            HTTP_X_API_KEY=key,
        )

    def test_plain_text_api_key_works(self) -> None:
        r = self.get(key="X" * 32)
        self.assertEqual(r.status_code, 200)

    def test_plain_text_readonly_key_works(self) -> None:
        self.project.api_key_readonly = "R" * 32
        self.project.save()

        r = self.get(key="R" * 32)
        self.assertEqual(r.status_code, 200)

    def test_it_rejects_wrong_key(self) -> None:
        r = self.get(key="W" * 32)
        self.assertEqual(r.status_code, 401)

    def test_ro_endpoint_accepts_hashed_api_key(self) -> None:
        key = self.project.set_api_key()
        self.project.save()
        r = self.get(key=key)
        self.assertEqual(r.status_code, 200)

    def test_ro_endpoint_accepts_hashed_readonly_key(self) -> None:
        key = self.project.set_api_key_readonly()
        self.project.save()

        r = self.get(key=key)
        self.assertEqual(r.status_code, 200)

    def test_rw_endpoint_accepts_hashed_api_key(self) -> None:
        key = self.project.set_api_key()
        self.project.save()

        r = self.post(key=key)
        self.assertEqual(r.status_code, 201)

    def test_rw_endpoint_rejects_hashed_readonly_key(self) -> None:
        key = self.project.set_api_key_readonly()
        self.project.save()

        r = self.post(key=key)
        self.assertEqual(r.status_code, 401)

    @patch("hc.accounts.models.hmac.compare_digest")
    def test_it_does_not_compare_digest_to_plaintext_key(
        self, mock_compare: Mock
    ) -> None:
        # Database has a plain text API key "X" * 32
        # We pass "hcw_" + "X" * 28.
        # We should recognize that the DB has a plain text key not a hashed key,
        # and we *should not* call hmac.compare_digest()
        self.post(key="hcw_" + "X" * 28)
        self.assertFalse(mock_compare.called)
