from __future__ import annotations

from unittest import skipIf
from unittest.mock import Mock, patch

from django.test import TestCase

from hc.lib.s3 import get_object

try:
    from minio import S3Error
    from urllib3.exceptions import ProtocolError

    have_minio = True
except ImportError:
    have_minio = False


@skipIf(not have_minio, "minio not installed")
class S3TestCase(TestCase):
    @patch("hc.lib.s3._client")
    def test_get_object_handles_s3error(self, mock_client):
        e = S3Error("a", "b", "c", "d", "e", "f")
        mock_client.get_object.return_value.read = Mock(side_effect=e)
        self.assertIsNone(get_object("dummy-code", 1))

    @patch("hc.lib.s3._client")
    def test_get_object_handles_protocolerror(self, mock_client):
        mock_client.get_object.return_value.read = Mock(side_effect=ProtocolError)
        self.assertIsNone(get_object("dummy-code", 1))
