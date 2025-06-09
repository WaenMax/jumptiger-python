#!/usr/bin/env python3

import os
import sys
import json
import time
import socket
import threading
import logging
import argparse
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ConnectionStats:
    """连接统计类"""
    def __init__(self):
        self.lock = threading.Lock()
        self.reset()

    def reset(self):
        """重置统计数据"""
        with self.lock:
            self.start_time = time.time()
            self.connections = {}
            self.stats = {
                'total_connections': 0,
                'active_connections': 0,
                'total_bytes_in': 0,
                'total_bytes_out': 0,
                'uptime': 0
            }

    def add_connection(self, client_id, host, port):
        """添加新连接"""
        with self.lock:
            self.stats['total_connections'] += 1
            self.stats['active_connections'] += 1
            self.connections[client_id] = {
                'id': client_id,
                'host': host,
                'port': port,
                'start_time': time.time(),
                'bytes_in': 0,
                'bytes_out': 0,
                'status': 'active'
            }

    def close_connection(self, client_id):
        """关闭连接"""
        with self.lock:
            if client_id in self.connections:
                self.connections[client_id]['status'] = 'closed'
                self.connections[client_id]['end_time'] = time.time()
                self.stats['active_connections'] -= 1

    def update_traffic(self, client_id, bytes_in=0, bytes_out=0):
        """更新流量统计"""
        with self.lock:
            if client_id in self.connections:
                self.connections[client_id]['bytes_in'] += bytes_in
                self.connections[client_id]['bytes_out'] += bytes_out
                self.stats['total_bytes_in'] += bytes_in
                self.stats['total_bytes_out'] += bytes_out

    def get_stats(self):
        """获取统计数据"""
        with self.lock:
            # 更新运行时间
            self.stats['uptime'] = time.time() - self.start_time
            return {
                'stats': dict(self.stats),
                'connections': list(self.connections.values())
            }

# 全局统计对象
connection_stats = ConnectionStats()

class MonitorRequestHandler(BaseHTTPRequestHandler):
    """监控HTTP请求处理器"""

    def do_GET(self):
        """处理GET请求"""
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(self.get_html_content().encode('utf-8'))
        elif self.path == '/api/stats':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(connection_stats.get_stats()).encode('utf-8'))
        elif self.path == '/api/reset':
            connection_stats.reset()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok'}).encode('utf-8'))
        else:
            self.send_error(404)

    def log_message(self, format, *args):
        """覆盖日志方法，减少控制台输出"""
        return

    def get_html_content(self):
        """获取HTML内容"""
        return '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JumpTiger 监控面板</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        .card {
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            padding: 20px;
            margin-bottom: 20px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 20px;
        }
        .stat-card {
            background-color: #f9f9f9;
            border-radius: 8px;
            padding: 15px;
            text-align: center;
        }
        .stat-value {
            font-size: 24px;
            font-weight: bold;
            margin: 10px 0;
        }
        .stat-label {
            color: #666;
            font-size: 14px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #f2f2f2;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .status-active {
            color: green;
            font-weight: bold;
        }
        .status-closed {
            color: #999;
        }
        .btn {
            background-color: #4CAF50;
            border: none;
            color: white;
            padding: 10px 15px;
            text-align: center;
            text-decoration: none;
            display: inline-block;
            font-size: 14px;
            margin: 4px 2px;
            cursor: pointer;
            border-radius: 4px;
        }
        .btn-danger {
            background-color: #f44336;
        }
        .chart-container {
            height: 300px;
            margin-bottom: 20px;
        }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>JumpTiger 监控面板</h1>
            <button class="btn btn-danger" onclick="resetStats()">重置统计</button>
        </div>
        
        <div class="card">
            <h2>系统概览</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-label">总连接数</div>
                    <div class="stat-value" id="total-connections">0</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">活跃连接数</div>
                    <div class="stat-value" id="active-connections">0</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">总入站流量</div>
                    <div class="stat-value" id="total-bytes-in">0 KB</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">总出站流量</div>
                    <div class="stat-value" id="total-bytes-out">0 KB</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">运行时间</div>
                    <div class="stat-value" id="uptime">0:00:00</div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>流量监控</h2>
            <div class="chart-container">
                <canvas id="trafficChart"></canvas>
            </div>
        </div>
        
        <div class="card">
            <h2>连接列表</h2>
            <table id="connections-table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>目标主机</th>
                        <th>端口</th>
                        <th>开始时间</th>
                        <th>入站流量</th>
                        <th>出站流量</th>
                        <th>状态</th>
                    </tr>
                </thead>
                <tbody id="connections-body">
                    <!-- 连接数据将在这里动态填充 -->
                </tbody>
            </table>
        </div>
    </div>

    <script>
        // 格式化字节数
        function formatBytes(bytes, decimals = 2) {
            if (bytes === 0) return '0 Bytes';
            
            const k = 1024;
            const dm = decimals < 0 ? 0 : decimals;
            const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
            
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            
            return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
        }
        
        // 格式化时间
        function formatTime(seconds) {
            const hrs = Math.floor(seconds / 3600);
            const mins = Math.floor((seconds % 3600) / 60);
            const secs = Math.floor(seconds % 60);
            
            return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        }
        
        // 格式化日期时间
        function formatDateTime(timestamp) {
            const date = new Date(timestamp * 1000);
            return date.toLocaleString();
        }
        
        // 流量图表
        let trafficChart;
        const trafficData = {
            labels: [],
            inData: [],
            outData: []
        };
        
        function initChart() {
            const ctx = document.getElementById('trafficChart').getContext('2d');
            trafficChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: trafficData.labels,
                    datasets: [
                        {
                            label: '入站流量',
                            data: trafficData.inData,
                            borderColor: 'rgba(75, 192, 192, 1)',
                            backgroundColor: 'rgba(75, 192, 192, 0.2)',
                            tension: 0.4
                        },
                        {
                            label: '出站流量',
                            data: trafficData.outData,
                            borderColor: 'rgba(255, 99, 132, 1)',
                            backgroundColor: 'rgba(255, 99, 132, 0.2)',
                            tension: 0.4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: '流量 (KB)'
                            }
                        },
                        x: {
                            title: {
                                display: true,
                                text: '时间'
                            }
                        }
                    }
                }
            });
        }
        
        // 更新图表数据
        function updateChart(bytesIn, bytesOut) {
            const now = new Date();
            const timeStr = now.getHours() + ':' + now.getMinutes() + ':' + now.getSeconds();
            
            trafficData.labels.push(timeStr);
            trafficData.inData.push(bytesIn / 1024);
            trafficData.outData.push(bytesOut / 1024);
            
            // 保持最近30个数据点
            if (trafficData.labels.length > 30) {
                trafficData.labels.shift();
                trafficData.inData.shift();
                trafficData.outData.shift();
            }
            
            trafficChart.update();
        }
        
        // 更新统计信息
        let lastBytesIn = 0;
        let lastBytesOut = 0;
        
        function updateStats() {
            fetch('/api/stats')
                .then(response => response.json())
                .then(data => {
                    // 更新概览统计
                    document.getElementById('total-connections').textContent = data.stats.total_connections;
                    document.getElementById('active-connections').textContent = data.stats.active_connections;
                    document.getElementById('total-bytes-in').textContent = formatBytes(data.stats.total_bytes_in);
                    document.getElementById('total-bytes-out').textContent = formatBytes(data.stats.total_bytes_out);
                    document.getElementById('uptime').textContent = formatTime(data.stats.uptime);
                    
                    // 更新图表
                    const currentBytesIn = data.stats.total_bytes_in;
                    const currentBytesOut = data.stats.total_bytes_out;
                    
                    // 计算增量
                    const deltaBytesIn = currentBytesIn - lastBytesIn;
                    const deltaBytesOut = currentBytesOut - lastBytesOut;
                    
                    updateChart(deltaBytesIn, deltaBytesOut);
                    
                    lastBytesIn = currentBytesIn;
                    lastBytesOut = currentBytesOut;
                    
                    // 更新连接表格
                    const tableBody = document.getElementById('connections-body');
                    tableBody.innerHTML = '';
                    
                    data.connections.forEach(conn => {
                        const row = document.createElement('tr');
                        
                        row.innerHTML = `
                            <td>${conn.id}</td>
                            <td>${conn.host}</td>
                            <td>${conn.port}</td>
                            <td>${formatDateTime(conn.start_time)}</td>
                            <td>${formatBytes(conn.bytes_in)}</td>
                            <td>${formatBytes(conn.bytes_out)}</td>
                            <td class="status-${conn.status}">${conn.status}</td>
                        `;
                        
                        tableBody.appendChild(row);
                    });
                })
                .catch(error => console.error('Error fetching stats:', error));
        }
        
        // 重置统计
        function resetStats() {
            if (confirm('确定要重置所有统计数据吗？')) {
                fetch('/api/reset')
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'ok') {
                            lastBytesIn = 0;
                            lastBytesOut = 0;
                            trafficData.labels = [];
                            trafficData.inData = [];
                            trafficData.outData = [];
                            trafficChart.update();
                            updateStats();
                        }
                    })
                    .catch(error => console.error('Error resetting stats:', error));
            }
        }
        
        // 初始化
        document.addEventListener('DOMContentLoaded', () => {
            initChart();
            updateStats();
            // 每2秒更新一次统计
            setInterval(updateStats, 2000);
        });
    </script>
</body>
</html>
        '''

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """多线程HTTP服务器"""
    daemon_threads = True

class JumpTigerMonitor:
    """JumpTiger监控类"""

    def __init__(self, config_path='config.json', http_port=8088):
        self.config_path = config_path
        self.http_port = http_port
        self.load_config()

    def load_config(self):
        """加载配置文件"""
        try:
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
            logger.info(f"配置已加载: {self.config_path}")
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            self.config = {
                "server": "127.0.0.1",
                "server_port": 8388,
                "local_port": 1080
            }

    def start_http_server(self):
        """启动HTTP监控服务器"""
        server = ThreadingHTTPServer(('0.0.0.0', self.http_port), MonitorRequestHandler)
        logger.info(f"监控服务器已启动: http://127.0.0.1:{self.http_port}")

        # 自动打开浏览器
        webbrowser.open(f"http://127.0.0.1:{self.http_port}")

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            logger.info("监控服务器已停止")

    def start(self):
        """启动监控"""
        logger.info("启动JumpTiger监控...")
        self.start_http_server()

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='JumpTiger监控工具')
    parser.add_argument('-c', '--config', default='config.json', help='配置文件路径')
    parser.add_argument('-p', '--port', type=int, default=8088, help='监控HTTP服务器端口')
    args = parser.parse_args()

    monitor = JumpTigerMonitor(args.config, args.port)
    monitor.start()

if __name__ == '__main__':
    main()
