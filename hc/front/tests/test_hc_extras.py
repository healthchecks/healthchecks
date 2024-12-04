from __future__ import annotations

from datetime import timedelta as td
from unittest import TestCase
from urllib.parse import urlparse

from django.test.utils import override_settings

from hc.front.templatetags.hc_extras import (absolute_site_logo_url,
                                             hc_duration, site_hostname)


class HcExtrasTestCase(TestCase):
    def test_hc_duration_works(self) -> None:
        samples = [
            (60, "1 minute"),
            (120, "2 minutes"),
            (3600, "1 hour"),
            (3660, "1 hour 1 minute"),
            (86400, "1 day"),
            (604800, "1 week"),
            (2419200, "4 weeks"),
            (2592000, "30 days"),
            (3801600, "44 days"),
        ]

        for seconds, expected_result in samples:
            result = hc_duration(td(seconds=seconds))
            self.assertEqual(result, expected_result)


class AbsoluteSiteLogoUrlTestCase(TestCase):
    def _test(
        self, site_root: str, site_logo_url: str | None, expected_result: str
    ) -> None:
        subpath = urlparse(site_root).path
        with override_settings(
            SITE_ROOT=site_root,
            SITE_LOGO_URL=site_logo_url,
            STATIC_URL=f"{subpath}/static/",
        ):
            self.assertEqual(absolute_site_logo_url(), expected_result)

    def test_it_handles_default(self) -> None:
        self._test(
            site_root="http://example.org",
            site_logo_url=None,
            expected_result="http://example.org/static/img/logo.png",
        )

    def test_it_handles_default_with_subpath(self) -> None:
        self._test(
            site_root="http://example.org/subpath",
            site_logo_url=None,
            expected_result="http://example.org/subpath/static/img/logo.png",
        )

    def test_it_handles_external_url(self) -> None:
        self._test(
            site_root="http://example.org",
            site_logo_url="http://example.com/foo.png",
            expected_result="http://example.com/foo.png",
        )

    def test_it_handles_leading_slash(self) -> None:
        self._test(
            site_root="http://example.org",
            site_logo_url="/foo/bar.png",
            expected_result="http://example.org/foo/bar.png",
        )

    def test_it_handles_leading_slash_with_subpath(self) -> None:
        self._test(
            site_root="http://example.org/subpath",
            site_logo_url="/foo/bar.png",
            expected_result="http://example.org/foo/bar.png",
        )


class SiteHostnameTestCase(TestCase):
    @override_settings(SITE_ROOT="http://example.org")
    def test_it_works(self) -> None:
        self.assertEqual(site_hostname(), "example.org")

    @override_settings(SITE_ROOT="http://example.org/foo")
    def test_it_handles_subpath(self) -> None:
        self.assertEqual(site_hostname(), "example.org")
