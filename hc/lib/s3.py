from io import BytesIO
from threading import Thread

from django.conf import settings

try:
    from minio import Minio
    from minio.deleteobjects import DeleteObject
except ImportError:
    # Enforce
    settings.S3_BUCKET = None


def client():
    if not settings.S3_BUCKET:
        raise Exception("Object storage is not configured")

    return Minio(
        settings.S3_ENDPOINT,
        settings.S3_ACCESS_KEY,
        settings.S3_SECRET_KEY,
        region=settings.S3_REGION,
    )


ASCII_J = ord("j")
ASCII_Z = ord("z")


def enc(n):
    """Generates an object key in the "<sorting prefix>-<n>" form.

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


def get_object(code, n):
    key = "%s/%s" % (code, enc(n))

    try:
        response = client().get_object(settings.S3_BUCKET, key)
        data = response.read()
    finally:
        response.close()
        response.release_conn()

    return data


def put_object(code, n, data):
    key = "%s/%s" % (code, enc(n))
    client().put_object(settings.S3_BUCKET, key, BytesIO(data), len(data))


def _remove_objects(code, upto_n):
    c = client()
    prefix = "%s/" % code
    start_after = prefix + enc(upto_n + 1)
    q = c.list_objects(settings.S3_BUCKET, prefix, start_after=start_after)
    delete_objs = [DeleteObject(obj.object_name) for obj in q]
    if delete_objs:
        errors = c.remove_objects(settings.S3_BUCKET, delete_objs)
        for e in errors:
            print("remove_objects error: ", e)


def remove_objects(check_code, upto_n):
    """Removes keys with n values below or equal to `upto_n`.

    The S3 API calls can take seconds to complete,
    therefore run the removal code on thread.

    """

    Thread(target=_remove_objects, args=(check_code, upto_n)).start()
