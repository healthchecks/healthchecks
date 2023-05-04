from __future__ import annotations

import logging
from functools import wraps
from unittest import skipIf
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from django.test.utils import override_settings

from hc.lib.s3 import get_object

try:
    from minio import S3Error
    from urllib3.exceptions import InvalidHeader, ProtocolError

    have_minio = True
except ImportError:
    have_minio = False


def nolog(func):
    @wraps(func)
    def wrapper_func(*args, **kwargs):
        logging.disable(logging.CRITICAL)
        result = func(*args, **kwargs)
        logging.disable(logging.NOTSET)
        return result

    return wrapper_func


@skipIf(not have_minio, "minio not installed")
@override_settings(S3_BUCKET="dummy-bucket")
class S3TestCase(SimpleTestCase):
    @patch("hc.lib.s3.statsd")
    @patch("hc.lib.s3._client")
    def test_get_object_handles_nosuchkey(self, mock_client, mock_statsd):
        e = S3Error("NoSuchKey", "b", "c", "d", "e", "f")
        mock_client.get_object.return_value.read = Mock(side_effect=e)
        self.assertIsNone(get_object("dummy-code", 1))
        mock_client.get_object.assert_called_once()
        # Should not increase the error counter for NoSuchKey responses
        mock_statsd.incr.assert_not_called()

    @nolog
    @patch("hc.lib.s3.statsd")
    @patch("hc.lib.s3._client")
    def test_get_object_handles_s3error(self, mock_client, mock_statsd):
        e = S3Error("DummyError", "b", "c", "d", "e", "f")
        mock_client.get_object.return_value.read = Mock(side_effect=e)
        self.assertIsNone(get_object("dummy-code", 1))
        mock_client.get_object.assert_called_once()
        mock_statsd.incr.assert_called_once()

    @nolog
    @patch("hc.lib.s3._client")
    def test_get_object_handles_urllib_exceptions(self, mock_client):
        for e in [ProtocolError, InvalidHeader]:
            mock_client.get_object.reset_mock()
            mock_client.get_object.return_value.read = Mock(side_effect=e)
            self.assertIsNone(get_object("dummy-code", 1))
            mock_client.get_object.assert_called_once()

    @override_settings(S3_BUCKET=None)
    @patch("hc.lib.s3._client")
    def test_get_object_handles_no_s3_configuration(self, mock_client):
        self.assertIsNone(get_object("dummy-code", 1))
        mock_client.get_object.assert_not_called()
