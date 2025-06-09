import os
import sys
import time
import subprocess
import unittest
import requests
import json

class TestShadowsocksProxy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 创建测试配置文件
        cls.server_config = {
            "server": "127.0.0.1",
            "server_port": 8388,
            "password": "test_password",
            "method": "aes-256-cfb",
            "timeout": 300
        }

        cls.client_config = {
            "server": "127.0.0.1",
            "server_port": 8388,
            "local_port": 1080,
            "password": "test_password",
            "method": "aes-256-cfb",
            "timeout": 300
        }

        with open("test_server_config.json", "w") as f:
            json.dump(cls.server_config, f)

        with open("test_client_config.json", "w") as f:
            json.dump(cls.client_config, f)

        # 启动服务器
        print("启动服务器...")
        cls.server_process = subprocess.Popen(
            [sys.executable, "server3.py", "-c", "test_server_config.json"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # 启动客户端
        print("启动客户端...")
        cls.client_process = subprocess.Popen(
            [sys.executable, "local3.py", "-c", "test_client_config.json"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # 等待服务启动
        time.sleep(3)

    @classmethod
    def tearDownClass(cls):
        # 停止服务
        cls.server_process.terminate()
        cls.client_process.terminate()
        cls.server_process.wait()
        cls.client_process.wait()

        # 删除测试配置文件
        os.remove("test_server_config.json")
        os.remove("test_client_config.json")

    def test_proxy_connection(self):
        """测试代理连接是否成功"""
        proxies = {
            'http': 'socks5://127.0.0.1:1080',
            'https': 'socks5://127.0.0.1:1080'
        }

        try:
            response = requests.get("http://httpbin.org/get", proxies=proxies, timeout=10)
            self.assertEqual(response.status_code, 200)
            print("代理连接测试成功")
        except Exception as e:
            self.fail(f"代理连接失败: {str(e)}")

if __name__ == "__main__":
    unittest.main()
