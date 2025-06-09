#!/usr/bin/env python3

import sys
import socket
import select
import socketserver
import struct
import os
import json
import logging
import getopt
import hashlib
import time
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

class Socks5Server(socketserver.StreamRequestHandler):
    def __init__(self, *args, **kwargs):
        self.encryptor = None
        super().__init__(*args, **kwargs)

    def handle_tcp(self, sock: socket.socket, remote: socket.socket):
        """处理TCP连接"""
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
                    decrypted = self.encryptor.decrypt(data)
                    result = send_all(remote, decrypted)
                    if result < len(data):
                        raise Exception('failed to send all data')
                    # 记录入站流量(解密后的数据大小)
                    connection_stats.update_traffic(client_id, bytes_out=len(decrypted))
                if remote in r:
                    data = remote.recv(4096)
                    if len(data) <= 0:
                        break
                    encrypted = self.encryptor.encrypt(data)
                    result = send_all(sock, encrypted)
                    if result < len(data):
                        raise Exception('failed to send all data')
                    # 记录出站流量(加密前的数据大小)
                    connection_stats.update_traffic(client_id, bytes_in=len(data))
        finally:
            sock.close()
            remote.close()

    def handle(self):
        """处理连接请求"""
        try:
            sock = self.connection
            # 初始化加密器
            self.encryptor = Encryptor(KEY, METHOD)

            # 解析地址类型
            data = sock.recv(1)
            addrtype = self.encryptor.decrypt(data)[0]

            if addrtype == 1:  # IPv4
                addr = socket.inet_ntoa(self.encryptor.decrypt(self.rfile.read(4)))
            elif addrtype == 3:  # Domain name
                length = self.encryptor.decrypt(sock.recv(1))[0]
                addr = self.encryptor.decrypt(self.rfile.read(length))
                addr = addr.decode('utf-8')
            else:
                logging.warning('address type not supported')
                return

            # 解析端口
            port_data = self.encryptor.decrypt(self.rfile.read(2))
            port = struct.unpack('>H', port_data)[0]

            try:
                logging.info(f'connecting {addr}:{port}')
                remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                remote.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                remote.connect((addr, port))
            except socket.error as e:
                logging.warning(f'connection error: {e}')
                return

            self.handle_tcp(sock, remote)
        except socket.error as e:
            logging.warning(f'socket error: {e}')

def main():
    try:
        os.chdir(os.path.dirname(__file__) or '.')
        print('JumpTiger v1.0 (Python 3)')

        global SERVER, PORT, KEY, METHOD
        args = []  # 初始化args变量

        # 读取配置文件
        config_file = 'config.json'
        for i, arg in enumerate(sys.argv[1:]):
            if arg == '-c' and i + 1 < len(sys.argv[1:]):
                config_file = sys.argv[i + 2]
                break
        
        print(f"Reading config from: {config_file}")
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
        except Exception as e:
            print(f"Error reading config file: {e}")
            sys.exit(1)

        SERVER = config.get('server', '0.0.0.0')
        PORT = config.get('server_port', 8388)
        KEY = config.get('password', 'default_password')
        METHOD = config.get('method', 'aes-256-cfb')

        print(f"Config loaded: SERVER={SERVER}, PORT={PORT}, METHOD={METHOD}")

        # 解析命令行参数
        try:
            optlist, args = getopt.getopt(sys.argv[1:], 'p:k:m:c:')
            for key, value in optlist:
                if key == '-p':
                    PORT = int(value)
                elif key == '-k':
                    KEY = value
                elif key == '-m':
                    METHOD = value
        except getopt.GetoptError as e:
            print(f"Command line argument error: {e}")
    except Exception as e:
        print(f"Error in initialization: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    # 配置日志
    try:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s %(levelname)-8s %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            filemode='a+'
        )
        print("Logging configured successfully")
    except Exception as e:
        print(f"Error configuring logging: {e}")

    # 设置IPv6支持
    if '-6' in args:
        ThreadingTCPServer.address_family = socket.AF_INET6
        print("IPv6 support enabled")

    # 启动服务器
    try:
        print(f"Attempting to start server on port {PORT}...")
        server = ThreadingTCPServer(('', PORT), Socks5Server)
        print(f"Server created successfully")
        logging.info(f"starting server at {SERVER}:{PORT}")
        logging.info(f"encryption method: {METHOD}")
        print(f"Server starting at {SERVER}:{PORT} with {METHOD} encryption")
        server.serve_forever()
    except socket.error as e:
        print(f"Socket error: {e}")
        logging.error(f"Socket error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        logging.error(f"Unexpected error: {e}")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"Fatal error in main: {e}")
        import traceback
        traceback.print_exc()
