from __future__ import annotations

from datetime import datetime, timezone
from datetime import timedelta as td
from unittest.mock import MagicMock, Mock, patch

import time_machine

from hc.api.management.commands.sendreports import Command
from hc.test import BaseTestCase

CURRENT_TIME = datetime(2020, 1, 13, 2, tzinfo=timezone.utc)
MOCK_SLEEP = Mock()


def _make_mock_conn(vendor: str, lock_acquired: bool) -> Mock:
    """Build a mock DB connection that returns lock_acquired for lock queries."""
    cursor_mock = MagicMock()
    cursor_mock.__enter__ = Mock(return_value=cursor_mock)
    cursor_mock.__exit__ = Mock(return_value=False)
    cursor_mock.fetchone.return_value = (lock_acquired,)

    conn_mock = Mock()
    conn_mock.vendor = vendor
    conn_mock.in_atomic_block = False
    conn_mock.cursor.return_value = cursor_mock
    return conn_mock


@time_machine.travel(CURRENT_TIME)
@patch("hc.api.management.commands.sendreports.time.sleep", MOCK_SLEEP)
class SendReportsHATestCase(BaseTestCase):
    """Tests for the distributed-lock HA code paths in sendreports.

    Both PostgreSQL (advisory lock) and MySQL (GET_LOCK) backends are covered.
    """

    def setUp(self) -> None:
        super().setUp()

        # Make alice eligible for a monthly report:
        self.profile.next_report_date = CURRENT_TIME - td(hours=1)
        self.profile.nag_period = td(hours=1)
        self.profile.next_nag_date = CURRENT_TIME - td(seconds=10)
        self.profile.save()

        # Disable other profiles so they don't interfere
        self.bobs_profile.reports = "off"
        self.bobs_profile.save()
        self.charlies_profile.reports = "off"
        self.charlies_profile.save()

    # -----------------------------------------------------------------------
    # Helpers shared across PostgreSQL and MySQL parameterised tests
    # -----------------------------------------------------------------------

    def _assert_lock_acquired(self, vendor: str, lock_sql: str) -> None:
        mock_conn = _make_mock_conn(vendor, lock_acquired=True)
        with patch("hc.api.management.commands.sendreports.connection", mock_conn):
            Command(stdout=Mock()).handle(loop=False)
        calls = [str(c) for c in mock_conn.cursor.return_value.execute.call_args_list]
        self.assertTrue(
            any(lock_sql in c for c in calls),
            f"{lock_sql!r} not called; calls: {calls}",
        )

    def _assert_exits_when_lock_not_acquired(self, vendor: str) -> None:
        mock_conn = _make_mock_conn(vendor, lock_acquired=False)
        with patch("hc.api.management.commands.sendreports.connection", mock_conn):
            cmd = Command(stdout=Mock())
            with patch.object(cmd, "handle_one_report") as mock_report:
                with patch.object(cmd, "handle_one_nag") as mock_nag:
                    result = cmd.handle(loop=False)
        mock_report.assert_not_called()
        mock_nag.assert_not_called()
        self.assertEqual(result, "Done.")

    def _assert_lock_released(self, vendor: str, release_sql: str) -> None:
        mock_conn = _make_mock_conn(vendor, lock_acquired=True)
        with patch("hc.api.management.commands.sendreports.connection", mock_conn):
            Command(stdout=Mock()).handle(loop=False)
        calls = [str(c) for c in mock_conn.cursor.return_value.execute.call_args_list]
        self.assertTrue(
            any(release_sql in c for c in calls),
            f"{release_sql!r} not called; calls: {calls}",
        )

    def _assert_lock_released_on_exception(self, vendor: str, release_sql: str) -> None:
        mock_conn = _make_mock_conn(vendor, lock_acquired=True)
        with patch("hc.api.management.commands.sendreports.connection", mock_conn):
            cmd = Command(stdout=Mock())
            with patch.object(cmd, "handle_one_report", side_effect=RuntimeError("boom")):
                with self.assertRaises(RuntimeError):
                    cmd.handle(loop=False)
        calls = [str(c) for c in mock_conn.cursor.return_value.execute.call_args_list]
        self.assertTrue(
            any(release_sql in c for c in calls),
            f"{release_sql!r} not released after exception; calls: {calls}",
        )

    # -----------------------------------------------------------------------
    # PostgreSQL – advisory lock
    # -----------------------------------------------------------------------

    def test_pg_acquires_advisory_lock_on_start(self) -> None:
        self._assert_lock_acquired("postgresql", "pg_try_advisory_lock")

    def test_pg_exits_when_lock_not_acquired(self) -> None:
        self._assert_exits_when_lock_not_acquired("postgresql")

    def test_pg_releases_lock_on_clean_exit(self) -> None:
        self._assert_lock_released("postgresql", "pg_advisory_unlock")

    def test_pg_releases_lock_on_exception(self) -> None:
        self._assert_lock_released_on_exception("postgresql", "pg_advisory_unlock")

    # -----------------------------------------------------------------------
    # MySQL – GET_LOCK / RELEASE_LOCK
    # -----------------------------------------------------------------------

    def test_mysql_acquires_get_lock_on_start(self) -> None:
        self._assert_lock_acquired("mysql", "GET_LOCK")

    def test_mysql_exits_when_lock_not_acquired(self) -> None:
        self._assert_exits_when_lock_not_acquired("mysql")

    def test_mysql_releases_lock_on_clean_exit(self) -> None:
        self._assert_lock_released("mysql", "RELEASE_LOCK")

    def test_mysql_releases_lock_on_exception(self) -> None:
        self._assert_lock_released_on_exception("mysql", "RELEASE_LOCK")

    # -----------------------------------------------------------------------
    # SQLite fallback – distributed lock is skipped entirely
    # -----------------------------------------------------------------------

    def test_sqlite_skips_distributed_lock(self) -> None:
        """On SQLite, no distributed lock is attempted."""
        # connection.vendor is "sqlite" in the default test suite.
        cmd = Command(stdout=Mock())
        with patch.object(cmd, "_try_acquire_lock") as mock_lock:
            cmd.handle(loop=False)
            mock_lock.assert_not_called()
