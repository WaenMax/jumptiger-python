#!/usr/bin/env python3

import sys
import socket
import select
import struct
import threading
import logging
import getopt
import os
import json
import hashlib
import time
import socketserver
from monitor import connection_stats
from typing import List, Tuple, Union
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import base64

try:
    import gevent
    import gevent.monkey
    gevent.monkey.patch_all(dns=gevent.version_info[0]>=1)
except ImportError:
    gevent = None
    print('warning: gevent not found, using threading instead', file=sys.stderr)

class Encryptor:
    """支持多种加密方法的加密器"""
    def __init__(self, key: str, method: str = 'aes-256-cfb'):
        self.key = key.encode('utf-8')
        self.method = method
        self.iv = None
        self.iv_sent = False
        self.cipher_iv = None
        self.decipher = None

        if method == 'aes-256-cfb':
            # 使用密码生成256位密钥
            self.key = hashlib.sha256(self.key).digest()
            self.iv = get_random_bytes(16)  # AES块大小为16字节
            self.cipher_iv = AES.new(self.key, AES.MODE_CFB, self.iv)
        else:
            # 保留原有的table方法作为备选
            self.encrypt_table = self._get_table(key)
            self.decrypt_table = bytes.maketrans(self.encrypt_table, bytes(range(256)))

    def _get_table(self, key: str) -> bytes:
        """生成加密表"""
        m = hashlib.md5()
        m.update(key.encode('utf-8'))
        s = m.digest()
        (a, b) = struct.unpack('<QQ', s)
        table = list(range(256))
        for i in range(1, 1024):
            table.sort(key=lambda x: int(a % (x + i) - a % (i)))
        return bytes(table)

    def encrypt(self, data: bytes) -> bytes:
        """加密数据"""
        if self.method == 'aes-256-cfb':
            if not self.iv_sent:
                self.iv_sent = True
                return self.iv + self.cipher_iv.encrypt(data)
            return self.cipher_iv.encrypt(data)
        else:
            return data.translate(self.encrypt_table)

    def decrypt(self, data: bytes) -> bytes:
        """解密数据"""
        if self.method == 'aes-256-cfb':
            if self.decipher is None:
                self.iv = data[:16]
                self.decipher = AES.new(self.key, AES.MODE_CFB, self.iv)
                return self.decipher.decrypt(data[16:])
            return self.decipher.decrypt(data)
        else:
            return data.translate(self.decrypt_table)

def send_all(sock: socket.socket, data: bytes) -> int:
    """确保所有数据都被发送"""
    bytes_sent = 0
    while True:
        r = sock.send(data[bytes_sent:])
        if r < 0:
            return r
        bytes_sent += r
        if bytes_sent == len(data):
            return bytes_sent

class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True

class SocksProxy:
    """SOCKS5代理实现"""

    def __init__(self, server_addr, server_port, local_port, password, method='aes-256-cfb', timeout=60):
        self.server_addr = server_addr
        self.server_port = server_port
        self.local_port = local_port
        self.password = password
        self.method = method
        self.timeout = timeout
        self.encryptor = None

        # 配置日志
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s %(levelname)-8s %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    def handle_connection(self, sock, addr):
        """处理客户端连接"""
        try:
            # 初始化加密器
            self.encryptor = Encryptor(self.password, self.method)

            # 接收SOCKS5握手请求
            sock.recv(262)  # 跳过SOCKS5握手
            sock.send(b"\x05\x00")  # 发送无需认证的响应

            # 接收连接请求
            data = sock.recv(4)
            mode = data[1]

            if mode != 1:  # 仅支持CONNECT模式
                logging.warning('仅支持CONNECT模式')
                return

            # 解析地址类型
            addrtype = data[3]

            if addrtype == 1:  # IPv4
                addr_ip = sock.recv(4)
                addr = socket.inet_ntoa(addr_ip)
            elif addrtype == 3:  # 域名
                addr_len = sock.recv(1)[0]
                addr = sock.recv(addr_len)
                addr = addr.decode('utf-8')
            else:
                logging.warning('不支持的地址类型')
                return

            # 解析端口
            addr_port = sock.recv(2)
            port = struct.unpack('>H', addr_port)[0]

            # 回复客户端连接成功
            reply = b"\x05\x00\x00\x01"
            reply += socket.inet_aton('0.0.0.0') + struct.pack(">H", 0)
            sock.send(reply)

            # 连接到远程服务器
            try:
                remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                remote.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                remote.connect((self.server_addr, self.server_port))

                # 发送目标地址到服务器
                if addrtype == 1:  # IPv4
                    data_to_send = b'\x01' + addr_ip
                elif addrtype == 3:  # 域名
                    data_to_send = b'\x03' + bytes([addr_len]) + addr.encode('utf-8')

                data_to_send += addr_port
                remote.send(self.encryptor.encrypt(data_to_send))

                # 处理数据转发
                self.handle_tcp(sock, remote)
            except socket.error as e:
                logging.error(f'连接服务器失败: {e}')
                return
        except socket.error as e:
            logging.error(f'处理连接错误: {e}')
        finally:
            sock.close()

    def handle_tcp(self, sock, remote):
        """处理TCP连接的数据转发"""
        try:
            # 生成唯一连接ID
            client_id = f"{id(self)}_{time.time()}"
            host, port = sock.getpeername()
            connection_stats.add_connection(client_id, host, port)
            
            fdset = [sock, remote]
            while True:
                r, w, e = select.select(fdset, [], [])
                if sock in r:
                    data = sock.recv(4096)
                    if len(data) <= 0:
                        break
                    encrypted = self.encryptor.encrypt(data)
                    result = send_all(remote, encrypted)
                    if result < len(data):
                        raise Exception('发送数据失败')
                    # 记录出站流量(加密后的数据大小)
                    connection_stats.update_traffic(client_id, bytes_out=len(encrypted))
                if remote in r:
                    data = remote.recv(4096)
                    if len(data) <= 0:
                        break
                    decrypted = self.encryptor.decrypt(data)
                    result = send_all(sock, decrypted)
                    if result < len(data):
                        raise Exception('发送数据失败')
                    # 记录入站流量(解密后的数据大小)
                    connection_stats.update_traffic(client_id, bytes_in=len(decrypted))
        finally:
            sock.close()
            remote.close()

    def start(self):
        """启动SOCKS5代理服务器"""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', self.local_port))
        server.listen(1024)

        logging.info(f'启动SOCKS5代理服务器在 127.0.0.1:{self.local_port}')

        try:
            while True:
                sock, addr = server.accept()
                thread = threading.Thread(target=self.handle_connection, args=(sock, addr))
                thread.daemon = True
                thread.start()
        except KeyboardInterrupt:
            logging.info('服务器已停止')
        finally:
            server.close()

def main():
    """主函数"""
    os.chdir(os.path.dirname(__file__) or '.')
    print('JumpTiger v1.0 (Python 3)')

    # 默认配置
    config = {
        'server': '127.0.0.1',
        'server_port': 8388,
        'local_port': 1080,
        'password': 'default_password',
        'timeout': 600,
        'method': 'aes-256-cfb'
    }

    # 读取配置文件
    try:
        with open('config.json', 'r') as f:
            config.update(json.load(f))
    except Exception as e:
        logging.error(f'读取配置文件失败: {e}')

    # 解析命令行参数
    try:
        optlist, args = getopt.getopt(sys.argv[1:], 's:p:l:k:m:t:')
        for key, value in optlist:
            if key == '-s':
                config['server'] = value
            elif key == '-p':
                config['server_port'] = int(value)
            elif key == '-l':
                config['local_port'] = int(value)
            elif key == '-k':
                config['password'] = value
            elif key == '-m':
                config['method'] = value
            elif key == '-t':
                config['timeout'] = int(value)
    except getopt.GetoptError as e:
        logging.error(f'命令行参数错误: {e}')

    # 启动代理服务器
    proxy = SocksProxy(
        config['server'],
        config['server_port'],
        config['local_port'],
        config['password'],
        config['method'],
        config['timeout']
    )
    proxy.start()

if __name__ == '__main__':
    import socketserver
    main()
