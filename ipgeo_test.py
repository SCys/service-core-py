from .ipgeo import load, find
import asyncio
import unittest

ADDRESS_LIST = {
    "8.8.8.8": {"country": "美国", "area": "", "province": "", "city": "", "isp": "Level3", "info": {}},
    "8.8.4.4": {"country": "美国", "area": "", "province": "新泽西", "city": "", "isp": "Level3", "info": {}},
    "114.114.114.114": {"country": "中国", "area": "", "province": "江苏省", "city": "南京市", "isp": "", "info": {}},
    "119.29.29.29": {"country": "中国", "area": "", "province": "北京", "city": "北京市", "isp": "腾讯", "info": {}},
    "223.5.5.5": {"country": "中国", "area": "", "province": "浙江省", "city": "杭州市", "isp": "阿里云", "info": {}},
}


class TestIpGeo(unittest.TestCase):
    def test_load(self):
        asyncio.run(load())

    def test_find(self):
        asyncio.run(load())

        for ip, ip_check_info in ADDRESS_LIST.items():
            info = find(ip)
            self.assertEqual(info.ip, ip)
            self.assertEqual(info.country, ip_check_info["country"])
            self.assertEqual(info.area, ip_check_info["area"])
            self.assertEqual(info.province, ip_check_info["province"])
            self.assertEqual(info.city, ip_check_info["city"])
            self.assertEqual(info.isp, ip_check_info["isp"])
            self.assertEqual(info.info, ip_check_info["info"])
