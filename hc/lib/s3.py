from io import BytesIO
from threading import Thread

from django.conf import settings
from minio import Minio
from minio.deleteobjects import DeleteObject


def client():
    return Minio(
        settings.S3_ENDPOINT,
        settings.S3_ACCESS_KEY,
        settings.S3_SECRET_KEY,
        region=settings.S3_REGION,
    )


ASCII_J = ord("j")
ASCII_Z = ord("z")


def enc(n):
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
    Thread(target=_remove_objects, args=(check_code, upto_n)).start()
