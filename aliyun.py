import base64
import hmac
import time
import urllib.request as urllib
from hashlib import sha1

from aiohttp import ClientSession

from .log import app_logger as logger
from .web import RemoteServerError

chunk_size = 1024
region_host = "oss-cn-hangzhou-internal.aliyuncs.com"


def sign(method: str, app_id: str, app_secret: str, bucket: str, filename: str, content_type: str, expire: int = 3600) -> str:
    """sign a oss object url

    params:

    - app_id: application id
    - app_secret: secret
    - bucket: bucket name
    - filename: full file path
    - content_type: file mimetype
    - expire: expire after current timestamp(uint: second)
    """
    now = int(time.time())
    expire = now - (now % 1800) + expire  # expire will not different every second
    tosign = "%s\n\n\n%d\n/%s/%s" % (method, expire, bucket, filename)
    if method == "PUT" or method == "POST":
        tosign = "%s\n\n%s\n%d\n/%s/%s" % (method, content_type, expire, bucket, filename)
    h = hmac.new(app_secret.encode(), tosign.encode(), sha1)
    sign = urllib.quote(base64.encodestring(h.digest()).strip())

    return "http://%s.%s/%s?OSSAccessKeyId=%s&Expires=%d&Signature=%s" % (bucket, region_host, filename, app_id, expire, sign)


def url(app_id: str, app_secret: str, bucket: str, filename: str, expire=600):
    """get oss object url(support download)

    params:

    - app_id: application id
    - app_secret: secret
    - bucket: bucket name
    - filename: full file path
    - expire: expire after current timestamp(uint: second)
    """
    return sign("GET", app_id, app_secret, bucket, filename, expire=expire)


async def put(app_id: str, app_secret: str, bucket: str, filename: str, data: bytes, content_type: str):
    """put file content to oss by bucket & filename

    params:

    - app_id: application id
    - app_secret: secret
    - bucket: bucket name
    - filename: full file path
    - data: file content bytes
    - content_type: file mimetype
    """
    url = sign("PUT", app_id, app_secret, bucket, filename, content_type)

    async with ClientSession(headers={"content-type": content_type}) as session:
        async with session.put(url, data=data) as resp:
            if resp.status != 200:
                logger.error("[aliyun.put_object]failed:%d %s", resp.status, resp.reason)
                raise RemoteServerError(resp.status, resp.reason)
