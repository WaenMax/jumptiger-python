#!/usr/bin/env python3

import socket
import select
import threading
import logging
import ssl
import time
from urllib.parse import urlparse
import re

class HttpProxy:
    """HTTP/HTTPS代理服务器实现"""
    
    def __init__(self, host='127.0.0.1', port=8087):
        self.host = host
        self.port = port
        self.timeout = 60
        # 设置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def handle_client(self, client_socket, client_address):
        """处理客户端连接"""
        try:
            # 接收HTTP请求
            request = client_socket.recv(8192)
            if not request:
                return

            # 解析HTTP请求
            first_line = request.split(b'\n')[0]
            method, url, version = first_line.split(b' ')
            method = method.decode('utf-8')
            url = url.decode('utf-8')
            
            # 解析目标地址
            if method == 'CONNECT':  # HTTPS请求
                host_port = url.split(':')
                host = host_port[0]
                port = int(host_port[1]) if len(host_port) > 1 else 443
                self._handle_https(client_socket, host, port)
            else:  # HTTP请求
                parsed = urlparse(url)
                host = parsed.hostname
                port = parsed.port or 80
                self._handle_http(client_socket, host, port, request)

        except Exception as e:
            self.logger.error(f"Error handling client {client_address}: {e}")
        finally:
            client_socket.close()

    def _handle_http(self, client_socket, host, port, request):
        """处理HTTP请求"""
        try:
            # 连接目标服务器
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.settimeout(self.timeout)
            server_socket.connect((host, port))

            # 转发请求
            server_socket.send(request)

            # 转发响应
            while True:
                # 使用select来处理多个socket
                readable, _, _ = select.select([server_socket, client_socket], [], [], self.timeout)
                
                if not readable:
                    break

                for sock in readable:
                    try:
                        data = sock.recv(8192)
                        if not data:
                            return
                        if sock is server_socket:
                            client_socket.send(data)
                        else:
                            server_socket.send(data)
                    except:
                        return

        except Exception as e:
            self.logger.error(f"HTTP Error: {e}")
        finally:
            server_socket.close()

    def _handle_https(self, client_socket, host, port):
        """处理HTTPS请求"""
        try:
            # 连接目标服务器
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.settimeout(self.timeout)
            server_socket.connect((host, port))

            # 发送连接成功响应
            client_socket.send(b'HTTP/1.1 200 Connection established\r\n\r\n')

            # 双向转发数据
            while True:
                readable, _, _ = select.select([server_socket, client_socket], [], [], self.timeout)
                
                if not readable:
                    break

                for sock in readable:
                    try:
                        data = sock.recv(8192)
                        if not data:
                            return
                        if sock is server_socket:
                            client_socket.send(data)
                        else:
                            server_socket.send(data)
                    except:
                        return

        except Exception as e:
            self.logger.error(f"HTTPS Error: {e}")
        finally:
            server_socket.close()

    def start(self):
        """启动代理服务器"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen(100)
        
        self.logger.info(f"HTTP/HTTPS Proxy Server running on {self.host}:{self.port}")

        while True:
            try:
                client_socket, client_address = server_socket.accept()
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, client_address)
                )
                client_thread.daemon = True
                client_thread.start()
            except Exception as e:
                self.logger.error(f"Error accepting connection: {e}")

class MonitoringProxy(HttpProxy):
    """带监控功能的HTTP/HTTPS代理服务器"""
    
    def __init__(self, host='127.0.0.1', port=8087):
        super().__init__(host, port)
        self.connections = {}
        self.connection_lock = threading.Lock()
        self.stats = {
            'total_connections': 0,
            'active_connections': 0,
            'total_bytes_in': 0,
            'total_bytes_out': 0
        }

    def _update_stats(self, bytes_in=0, bytes_out=0):
        """更新统计信息"""
        with self.connection_lock:
            self.stats['total_bytes_in'] += bytes_in
            self.stats['total_bytes_out'] += bytes_out

    def handle_client(self, client_socket, client_address):
        """处理客户端连接并记录统计信息"""
        client_id = f"{client_address[0]}:{client_address[1]}"
        
        with self.connection_lock:
            self.stats['total_connections'] += 1
            self.stats['active_connections'] += 1
            self.connections[client_id] = {
                'start_time': time.time(),
                'bytes_in': 0,
                'bytes_out': 0,
                'status': 'active'
            }

        try:
            super().handle_client(client_socket, client_address)
        finally:
            with self.connection_lock:
                self.stats['active_connections'] -= 1
                if client_id in self.connections:
                    self.connections[client_id]['status'] = 'closed'
                    self.connections[client_id]['end_time'] = time.time()

    def get_stats(self):
        """获取代理服务器统计信息"""
        with self.connection_lock:
            return {
                'stats': dict(self.stats),
                'connections': dict(self.connections)
            }

def main():
    """主函数"""
    import argparse
    parser = argparse.ArgumentParser(description='HTTP/HTTPS Proxy Server with Monitoring')
    parser.add_argument('--host', default='127.0.0.1', help='Proxy server host')
    parser.add_argument('--port', type=int, default=8087, help='Proxy server port')
    parser.add_argument('--monitor', action='store_true', help='Enable monitoring')
    args = parser.parse_args()

    if args.monitor:
        proxy = MonitoringProxy(args.host, args.port)
    else:
        proxy = HttpProxy(args.host, args.port)
    
    try:
        proxy.start()
    except KeyboardInterrupt:
        print("\nShutting down proxy server...")

if __name__ == '__main__':
    main()
