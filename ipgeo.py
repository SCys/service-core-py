# copy from https://github.com/lionsoul2014/ip2region/blob/master/binding/python/ip2Region.py
from utils.ip2region import Ip2Region

from .logging import logger_app as logger

ip2region = None

url_db = "https://cdn.jsdelivr.net/gh/lionsoul2014/ip2region@v2.2.0-release/data/ip2region.db"


async def ip2region_update():
    import aiohttp

    global ip2region

    # download remote source
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
        async with session.get(url_db) as response:
            content = await response.read()
            ip2region = Ip2Region(content)

    logger.info("ip2region is loaded")


def find(ip):
    global ip2region

    params = ["" for i in range(0, 6)]
    try:
        info = ip2region.memorySearch(ip)
    except:
        pass
    else:
        if not info:
            params = ["" for i in range(0, 6)]
        else:
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
