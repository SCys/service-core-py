import io
import os
import socket
import struct
import sys
from typing import Optional
from dataclasses import dataclass, field
from typing import Dict

from .log import logger_debug as logger
from .utils import download

URLS_DB = [
    "https://github.com/lionsoul2014/ip2region/raw/master/data/ip2region.xdb",
    "https://cdn.jsdelivr.net/gh/lionsoul2014/ip2region@master/data/ip2region.xdb",
]

PATH_DB = "data/ipgeo/ip2region.db"

__all__ = ["load", "find"]

db: Optional["XdbSearcher"] = None


@dataclass
class IPLocationInfo:
    """
    ```python
    # 国家|区域|省份|城市|ISP，缺省的地域信息默认是0
    {
        "ip": ip,
        "country": params[1],  # 国家
        "area": params[2],  # 区域
        "province": params[3],  # 省份
        "city": params[4],  # 城市
        "isp": params[5],  # ISP
        "info": {},
    }
    ```
    """

    ip: str
    country: str
    area: str
    province: str
    city: str
    isp: str
    info: Dict = field(default_factory=dict)

    def __str__(self):
        return f"ip:{self.ip},country:{self.country},area:{self.area},province:{self.province},city:{self.city},isp:{self.isp},info:{self.info}"

    def __repr__(self):
        return self.__str__()


async def load():
    """load database from PATH_DB"""
    global db

    if not os.path.isdir("data/ipgeo"):
        os.makedirs("data/ipgeo")

    # use utils.download try to download content from URLS_DB
    if not os.path.isfile(PATH_DB):
        for url in URLS_DB:
            try:
                content = await download(url, timeout=30)
                with open(PATH_DB, "wb+") as f:
                    f.write(content)
                break
            except Exception as e:
                logger.warning(f"download {url} failed:{e}")

    if not os.path.isfile(PATH_DB):
        logger.warning(f"{PATH_DB} not exist!")
        return

    cb = XdbSearcher.loadContentFromFile(dbfile=PATH_DB)
    db = XdbSearcher(contentBuff=cb)

    logger.info(f"load ip location database from {PATH_DB}")


def find(ip) -> IPLocationInfo:
    global db

    if db is None:
        return IPLocationInfo(
            ip=ip,
            country="",
            area="",
            province="",
            city="",
            isp="",
            info={},
        )

    params = ["", "", "", "", "", ""]
    try:
        info = db.search(ip)
    except:
        pass
    else:
        if not info:
            params = ["", "", "", "", "", ""]
        else:
            params = info.split("|")
            # convert 0 to "0"
            params = [i if i != "0" else "" for i in params]

    # 国家|区域|省份|城市|ISP，缺省的地域信息默认是0
    return IPLocationInfo(
        ip=ip,
        country=params[0],
        area=params[1],
        province=params[2],
        city=params[3],
        isp=params[4],
        info={},
    )


# {{{ COPY FROM https://github.com/lionsoul2014/ip2region/raw/master/binding/python/xdbSearcher.py

# Copyright 2022 The Ip2Region Authors. All rights reserved.
# Use of this source code is governed by a Apache2.0-style
# license that can be found in the LICENSE file.
#
#  Created by luckydog on 2022/6/29.
#  Copyright © 2022年 luckydog. All rights reserved.
#

import socket
import struct
import io
import sys


# xdb默认参数
HeaderInfoLength = 256
VectorIndexRows = 256
VectorIndexCols = 256
VectorIndexSize = 8
SegmentIndexSize = 14


class XdbSearcher(object):
    __f = None

    # the minimal memory allocation.
    vectorIndex = None
    # 整个读取xdb，保存在内存中
    contentBuff = None

    @staticmethod
    def loadVectorIndexFromFile(dbfile):
        try:
            f = io.open(dbfile, "rb")
            f.seek(HeaderInfoLength)
            vi_len = VectorIndexRows * VectorIndexCols * SegmentIndexSize
            vector_data = f.read(vi_len)
            f.close()
            return vector_data
        except IOError as e:
            print("[Error]: %s" % e)

    @staticmethod
    def loadContentFromFile(dbfile):
        try:
            f = io.open(dbfile, "rb")
            all_data = f.read()
            f.close()
            return all_data
        except IOError as e:
            print("[Error]: %s" % e)

    def __init__(self, dbfile=None, vectorIndex=None, contentBuff=None):
        self.initDatabase(dbfile, vectorIndex, contentBuff)

    def search(self, ip):
        if isinstance(ip, str):
            if not ip.isdigit():
                ip = self.ip2long(ip)
            return self.searchByIPLong(ip)
        else:
            return self.searchByIPLong(ip)

    def searchByIPStr(self, ip):
        if not ip.isdigit():
            ip = self.ip2long(ip)
        return self.searchByIPLong(ip)

    def searchByIPLong(self, ip):
        # locate the segment index block based on the vector index
        sPtr = ePtr = 0
        il0 = (int)((ip >> 24) & 0xFF)
        il1 = (int)((ip >> 16) & 0xFF)
        idx = il0 * VectorIndexCols * VectorIndexSize + il1 * VectorIndexSize

        if self.vectorIndex is not None:
            sPtr = self.getLong(self.vectorIndex, idx)
            ePtr = self.getLong(self.vectorIndex, idx + 4)
        elif self.contentBuff is not None:
            sPtr = self.getLong(self.contentBuff, HeaderInfoLength + idx)
            ePtr = self.getLong(self.contentBuff, HeaderInfoLength + idx + 4)
        else:
            self.__f.seek(HeaderInfoLength + idx)
            buffer_ptr = self.__f.read(8)
            sPtr = self.getLong(buffer_ptr, 0)
            ePtr = self.getLong(buffer_ptr, 4)

        # binary search the segment index block to get the region info
        dataLen = dataPtr = int(-1)
        l = int(0)
        h = int((ePtr - sPtr) / SegmentIndexSize)
        while l <= h:
            m = int((l + h) >> 1)
            p = int(sPtr + m * SegmentIndexSize)
            # read the segment index
            buffer_sip = self.readBuffer(p, SegmentIndexSize)
            sip = self.getLong(buffer_sip, 0)
            if ip < sip:
                h = m - 1
            else:
                eip = self.getLong(buffer_sip, 4)
                if ip > eip:
                    l = m + 1
                else:
                    dataLen = self.getInt2(buffer_sip, 8)
                    dataPtr = self.getLong(buffer_sip, 10)
                    break

        # empty match interception
        if dataPtr < 0:
            return ""

        buffer_string = self.readBuffer(dataPtr, dataLen)
        return_string = buffer_string.decode("utf-8")
        return return_string

    def readBuffer(self, offset, length):
        buffer = None
        # check the in-memory buffer first
        if self.contentBuff is not None:
            buffer = self.contentBuff[offset : offset + length]
            return buffer

        # read from the file handle
        if self.__f is not None:
            self.__f.seek(offset)
            buffer = self.__f.read(length)
        return buffer

    def initDatabase(self, dbfile, vi, cb):
        """
        " initialize the database for search
        " param: dbFile, vectorIndex, contentBuff
        """
        try:
            if cb is not None:
                self.__f = None
                self.vectorIndex = None
                self.contentBuff = cb
            else:
                self.__f = io.open(dbfile, "rb")
                self.vectorIndex = vi
        except IOError as e:
            print("[Error]: %s" % e)
            sys.exit()

    def ip2long(self, ip):
        _ip = socket.inet_aton(ip)
        return struct.unpack("!L", _ip)[0]

    def isip(self, ip):
        p = ip.split(".")

        if len(p) != 4:
            return False
        for pp in p:
            if not pp.isdigit():
                return False
            if len(pp) > 3:
                return False
            if int(pp) > 255:
                return False
        return True

    def getLong(self, b, offset):
        if len(b[offset : offset + 4]) == 4:
            return struct.unpack("I", b[offset : offset + 4])[0]
        return 0

    def getInt2(self, b, offset):
        return (b[offset] & 0x000000FF) | (b[offset + 1] & 0x0000FF00)

    def close(self):
        if self.__f is not None:
            self.__f.close()
        self.vectorIndex = None
        self.contentBuff = None


# }}} COPY FROM https://github.com/lionsoul2014/ip2region/raw/master/binding/python/xdbSearcher.py
