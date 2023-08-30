from __future__ import annotations

from hc.test import BaseTestCase


class SearchTestCase(BaseTestCase):
    def test_it_works(self) -> None:
        r = self.client.get("/docs/search/?q=failure")
        self.assertContains(
            r, "You can actively signal a <span>failure</span>", status_code=200
        )

    def test_it_handles_no_results(self) -> None:
        r = self.client.get("/docs/search/?q=asfghjkl")
        self.assertContains(r, "Your search query matched no results", status_code=200)

    def test_it_rejects_special_characters(self) -> None:
        r = self.client.get("/docs/search/?q=api/v1")
        self.assertContains(r, "Your search query matched no results", status_code=200)
