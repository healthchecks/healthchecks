from __future__ import annotations

import logging
import time
from io import BytesIO
from threading import Thread

from django.conf import settings
from statsd.defaults.env import statsd

try:
    from minio import Minio, S3Error
    from minio.deleteobjects import DeleteObject
    from urllib3 import PoolManager
    from urllib3.exceptions import HTTPError, ReadTimeoutError
except ImportError:
    # Enforce
    settings.S3_BUCKET = None

_client = None
logger = logging.getLogger(__name__)


def client():
    if not settings.S3_BUCKET:
        raise Exception("Object storage is not configured")

    global _client
    if _client is None:
        _client = Minio(
            settings.S3_ENDPOINT,
            settings.S3_ACCESS_KEY,
            settings.S3_SECRET_KEY,
            region=settings.S3_REGION,
            http_client=PoolManager(timeout=settings.S3_TIMEOUT),
        )

    return _client


ASCII_J = ord("j")
ASCII_Z = ord("z")


def enc(n):
    """Generate an object key in the "<sorting prefix>-<n>" form.

    >>> [enc(i) for i in range(0, 5)]
    ['zj-0', 'zi-1', 'zh-2', 'zg-3', 'zf-4']

    The purpose of the sorting prefix is to sort keys with smaller n values
    last:

    >>> sorted([enc(i) for i in range(0, 5)])
    ['zf-4', 'zg-3', 'zh-2', 'zi-1', 'zj-0']

    This allows efficient lookup of objects with n
    values below a specific threshold. For example, the following
    retrieves all keys at bucket's root directory with n < 123:

    >>> client.list_objects(bucket_name, start_after=enc(123))
    """
    s = str(n)
    len_inverted = chr(ASCII_Z - len(s) + 1)
    inverted = "".join(chr(ASCII_J - int(c)) for c in s)
    return len_inverted + inverted + "-" + s


@statsd.timer("hc.lib.s3.getObjectTime")
def get_object(code, n):
    if not settings.S3_BUCKET:
        return None

    key = "%s/%s" % (code, enc(n))
    response = None
    try:
        response = client().get_object(settings.S3_BUCKET, key)
        return response.read()
    except S3Error as e:
        if e.code == "NoSuchKey":
            # It's not an error condition if an object does not exist.
            # Return None, don't log exception, don't increase error counter.
            return None

        logger.exception("S3Error in hc.lib.s3.get_object")
        statsd.incr("hc.lib.s3.getObjectErrors")
        return None
    except HTTPError:
        logger.exception("HTTPError in hc.lib.s3.get_object")
        statsd.incr("hc.lib.s3.getObjectErrors")
        return None
    finally:
        if response:
            response.close()
            response.release_conn()


def put_object(code, n, data):
    key = "%s/%s" % (code, enc(n))
    retries = 10
    while True:
        try:
            client().put_object(settings.S3_BUCKET, key, BytesIO(data), len(data))
            break
        except S3Error as e:
            if e.code == "InternalError" and retries > 0:
                retries -= 1
                print("InternalError, retrying (retries=%d)..." % retries)
                continue

            raise e


def _remove_objects(code, upto_n):
    if upto_n <= 0:
        return

    prefix = "%s/" % code
    start_after = prefix + enc(upto_n + 1)
    q = client().list_objects(settings.S3_BUCKET, prefix, start_after=start_after)
    delete_objs = [DeleteObject(obj.object_name) for obj in q]
    if delete_objs:
        num_objs = len(delete_objs)
        try:
            with statsd.timer("hc.lib.s3.removeObjectsTime"):
                errors = client().remove_objects(settings.S3_BUCKET, delete_objs)
                for e in errors:
                    statsd.incr("hc.lib.s3.removeObjectsErrors")
                    logger.error(f"remove_objects error: {e}")
        except ReadTimeoutError:
            logger.exception(f"ReadTimeoutError while removing {num_objs} objects")
            statsd.incr("hc.lib.s3.removeObjectsErrors")


def remove_objects(check_code, upto_n):
    """Remove keys with n values below or equal to `upto_n`.

    The S3 API calls can take seconds to complete,
    therefore run the removal code on thread.
    """
    Thread(target=_remove_objects, args=(check_code, upto_n)).start()
