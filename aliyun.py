import base64
import hmac
from hashlib import sha1
import time
import urllib.request as urllib
import aiohttp

from .web import RemoteServerError
from .logging import app_logger as logger
from rapidjson import DM_ISO8601, loads

chunk_size = 1024
region_host = "oss-cn-hangzhou-internal.aliyuncs.com"

# use signature in url
def _oss_file_url(method, app_id, app_secret, bucket, filename, content_type):
    now = int(time.time())
    expire = now - (now % 1800) + 3600  # expire will not different every second
    tosign = "%s\n\n\n%d\n/%s/%s" % (method, expire, bucket, filename)
    if method == "PUT" or method == "POST":
        tosign = "%s\n\n%s\n%d\n/%s/%s" % (method, content_type, expire, bucket, filename)
    h = hmac.new(app_secret.encode(), tosign.encode(), sha1)
    sign = urllib.quote(base64.encodestring(h.digest()).strip())
    return "http://%s.%s/%s?OSSAccessKeyId=%s&Expires=%d&Signature=%s" % (bucket, region_host, filename, app_id, expire, sign)


def get_object_url(app_id, app_secret, bucket, filename):
    return _oss_file_url("GET", app_id, app_secret, bucket, filename, None)

async def put_object(app_id, app_secret, bucket, filename, data, content_type):
    url = _oss_file_url("PUT", app_id, app_secret, bucket, filename, content_type)

    async with aiohttp.ClientSession(headers={"content-type": content_type}) as session:
        async with session.put(url, data=data) as resp:
            if resp.status != 200:
                logger.error("[aliyun.put_object]failed:%d %s", resp.status, resp.reason)
                raise RemoteServerError(resp.status, resp.reason)
