import gzip
import io
import logging

from utils.ip2region import Ip2Region

ip2region = None

logger = logging.getLogger(__name__)


async def ip2region_update():
    import aiohttp

    global ip2region

    # download remote source
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
        async with session.get("https://iscys.com/f/ipgeo/ip2region.db.latest.gz") as response:
            content = await response.read()
            fobj = io.BytesIO(gzip.decompress(content))
            logger.info("ip2region is loaded")
            ip2region = Ip2Region(fobj)


def ip2region_update_sync():
    import requests

    global ip2region

    # download remote source
    response = requests.get("https://iscys.com/f/ipgeo/ip2region.db.latest.gz")
    content = response.body
    fobj = io.BytesIO(gzip.decompress(content))
    logger.info("ip2region is loaded")
    ip2region = Ip2Region(fobj)


def find(ip):
    global ip2region

    info = ip2region.memorySearch(ip)
    params = info.split("|")

    return {
        "ip": ip,
        "country": params[1],
        "area": params[2],
        "province": params[3],
        "city": params[4],
        "isp": params[5],
        "info": {},
    }
