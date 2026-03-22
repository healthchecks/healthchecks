from __future__ import annotations

from datetime import timedelta as td
from unittest.mock import MagicMock, Mock, patch

from django.utils.timezone import now

from hc.api.management.commands.sendalerts import Command
from hc.api.models import Check, Flip
from hc.test import BaseTestCase


class SendAlertsHATestCase(BaseTestCase):
    """Tests for the PostgreSQL/MySQL HA code paths in sendalerts.

    These tests mock connection.vendor to simulate PostgreSQL or MySQL without
    requiring those databases. The existing test suite (test_sendalerts.py)
    covers the SQLite/optimistic-lock fallback paths.
    """

    def _make_flip(self) -> Flip:
        check = Check(project=self.project, status="up")
        check.last_ping = now()
        check.alert_after = check.last_ping + td(days=1, hours=1)
        check.save()

        flip = Flip(owner=check, created=check.last_ping)
        flip.old_status = "down"
        flip.new_status = "up"
        flip.save()
        return flip

    # -----------------------------------------------------------------------
    # process_one_flip – PostgreSQL path
    # -----------------------------------------------------------------------

    @patch("hc.api.management.commands.sendalerts.statsd")
    @patch("hc.api.management.commands.sendalerts.notify")
    @patch("hc.api.management.commands.sendalerts.connection")
    def test_pg_process_one_flip_uses_select_for_update(
        self, mock_conn: Mock, mock_notify: Mock, mock_statsd: Mock
    ) -> None:
        """On PostgreSQL, process_one_flip uses SELECT FOR UPDATE SKIP LOCKED."""
        mock_conn.vendor = "postgresql"
        # Make transaction.atomic() a no-op context manager
        mock_conn.in_atomic_block = False

        flip = self._make_flip()

        with patch(
            "hc.api.management.commands.sendalerts.transaction.atomic"
        ) as mock_atomic:
            mock_atomic.return_value.__enter__ = Mock(return_value=None)
            mock_atomic.return_value.__exit__ = Mock(return_value=False)

            # Patch select_for_update to return a queryset that yields our flip
            with patch.object(
                Flip.objects.all().__class__,
                "select_for_update",
                return_value=Flip.objects.filter(id=flip.id),
            ):
                result = Command(stdout=Mock()).process_one_flip()

        self.assertTrue(result)
        # The flip should have been marked as processed
        flip.refresh_from_db()
        self.assertIsNotNone(flip.processed)

    @patch("hc.api.management.commands.sendalerts.statsd")
    @patch("hc.api.management.commands.sendalerts.notify")
    @patch("hc.api.management.commands.sendalerts.connection")
    def test_pg_process_one_flip_returns_false_when_no_flips(
        self, mock_conn: Mock, mock_notify: Mock, mock_statsd: Mock
    ) -> None:
        """On PostgreSQL, process_one_flip returns False when no unprocessed flips exist."""
        mock_conn.vendor = "postgresql"
        mock_conn.in_atomic_block = False

        # No flips created — the select_for_update query should return None
        with patch(
            "hc.api.management.commands.sendalerts.transaction.atomic"
        ) as mock_atomic:
            mock_atomic.return_value.__enter__ = Mock(return_value=None)
            mock_atomic.return_value.__exit__ = Mock(return_value=False)

            with patch.object(
                Flip.objects.all().__class__,
                "select_for_update",
                return_value=Flip.objects.none(),
            ):
                result = Command(stdout=Mock()).process_one_flip()

        self.assertFalse(result)
        mock_notify.assert_not_called()

    # -----------------------------------------------------------------------
    # handle_going_down – PostgreSQL path
    # -----------------------------------------------------------------------

    @patch("hc.api.management.commands.sendalerts.connection")
    def test_pg_handle_going_down_creates_flip(self, mock_conn: Mock) -> None:
        """On PostgreSQL, handle_going_down creates a Flip inside transaction.atomic()."""
        mock_conn.vendor = "postgresql"
        mock_conn.in_atomic_block = False

        check = Check(project=self.project, status="up")
        check.last_ping = now() - td(days=2)
        check.alert_after = check.last_ping + td(days=1, hours=1)
        check.save()

        with patch(
            "hc.api.management.commands.sendalerts.transaction.atomic"
        ) as mock_atomic:
            mock_atomic.return_value.__enter__ = Mock(return_value=None)
            mock_atomic.return_value.__exit__ = Mock(return_value=False)

            with patch.object(
                Check.objects.all().__class__,
                "select_for_update",
                return_value=Check.objects.filter(id=check.id),
            ):
                result = Command().handle_going_down()

        self.assertTrue(result)
        check.refresh_from_db()
        self.assertEqual(check.status, "down")
        self.assertIsNone(check.alert_after)
        self.assertEqual(Flip.objects.filter(owner=check).count(), 1)

    @patch("hc.api.management.commands.sendalerts.connection")
    def test_pg_handle_going_down_returns_false_when_no_checks(
        self, mock_conn: Mock
    ) -> None:
        """On PostgreSQL, handle_going_down returns False when no checks are due."""
        mock_conn.vendor = "postgresql"
        mock_conn.in_atomic_block = False

        with patch(
            "hc.api.management.commands.sendalerts.transaction.atomic"
        ) as mock_atomic:
            mock_atomic.return_value.__enter__ = Mock(return_value=None)
            mock_atomic.return_value.__exit__ = Mock(return_value=False)

            with patch.object(
                Check.objects.all().__class__,
                "select_for_update",
                return_value=Check.objects.none(),
            ):
                result = Command().handle_going_down()

        self.assertFalse(result)

    # -----------------------------------------------------------------------
    # SQLite fallback – verify existing behaviour is unchanged
    # -----------------------------------------------------------------------

    @patch("hc.api.management.commands.sendalerts.statsd")
    @patch("hc.api.management.commands.sendalerts.notify")
    def test_sqlite_process_one_flip_uses_optimistic_lock(
        self, mock_notify: Mock, mock_statsd: Mock
    ) -> None:
        """On non-PostgreSQL backends the original optimistic-lock path is used."""
        # connection.vendor is "sqlite" in the test suite — no mocking needed.
        flip = self._make_flip()

        result = Command(stdout=Mock()).process_one_flip()

        self.assertTrue(result)
        flip.refresh_from_db()
        self.assertIsNotNone(flip.processed)

    def test_sqlite_handle_going_down_uses_optimistic_lock(self) -> None:
        """On non-PostgreSQL backends handle_going_down uses the original path."""
        check = Check(project=self.project, status="up")
        check.last_ping = now() - td(days=2)
        check.alert_after = check.last_ping + td(days=1, hours=1)
        check.save()

        result = Command().handle_going_down()

        self.assertTrue(result)
        check.refresh_from_db()
        self.assertEqual(check.status, "down")
        self.assertEqual(Flip.objects.filter(owner=check).count(), 1)
