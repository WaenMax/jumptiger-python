#!/usr/bin/env python3

import os
import sys
import json
import time
import argparse
import subprocess
import webbrowser
import logging
import signal
import platform

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class JumpTigerManager:
    """JumpTiger管理器"""

    def __init__(self):
        self.config_path = 'config.json'
        self.processes = {}
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
                "local_port": 1080,
                "password": "password",
                "timeout": 600,
                "method": "aes-256-cfb"
            }

    def save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            logger.info(f"配置已保存: {self.config_path}")
        except Exception as e:
            logger.error(f"保存配置失败: {e}")

    def start_local(self):
        """启动本地客户端"""
        if 'local' in self.processes and self.processes['local'].poll() is None:
            logger.warning("本地客户端已在运行")
            return

        cmd = [sys.executable, 'local3.py']
        logger.info(f"启动本地客户端: {' '.join(cmd)}")

        try:
            self.processes['local'] = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            logger.info(f"本地客户端已启动，PID: {self.processes['local'].pid}")
        except Exception as e:
            logger.error(f"启动本地客户端失败: {e}")

    def start_server(self):
        """启动服务器"""
        if 'server' in self.processes and self.processes['server'].poll() is None:
            logger.warning("服务器已在运行")
            return

        cmd = [sys.executable, 'server3.py']
        logger.info(f"启动服务器: {' '.join(cmd)}")

        try:
            self.processes['server'] = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            logger.info(f"服务器已启动，PID: {self.processes['server'].pid}")
        except Exception as e:
            logger.error(f"启动服务器失败: {e}")

    def start_http_proxy(self):
        """启动HTTP代理"""
        if 'http_proxy' in self.processes and self.processes['http_proxy'].poll() is None:
            logger.warning("HTTP代理已在运行")
            return

        http_port = self.config.get('http_port', 8087)
        cmd = [sys.executable, 'http_proxy.py', '--host', '127.0.0.1', '--port', str(http_port)]
        logger.info(f"启动HTTP代理: {' '.join(cmd)}")

        try:
            self.processes['http_proxy'] = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            logger.info(f"HTTP代理已启动，PID: {self.processes['http_proxy'].pid}")
        except Exception as e:
            logger.error(f"启动HTTP代理失败: {e}")

    def start_monitor(self):
        """启动监控面板"""
        if 'monitor' in self.processes and self.processes['monitor'].poll() is None:
            logger.warning("监控面板已在运行")
            # 打开浏览器
            monitor_port = self.config.get('monitor_port', 8088)
            webbrowser.open(f"http://127.0.0.1:{monitor_port}")
            return

        monitor_port = self.config.get('monitor_port', 8088)
        cmd = [sys.executable, 'monitor.py', '--port', str(monitor_port)]
        logger.info(f"启动监控面板: {' '.join(cmd)}")

        try:
            self.processes['monitor'] = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            logger.info(f"监控面板已启动，PID: {self.processes['monitor'].pid}")
        except Exception as e:
            logger.error(f"启动监控面板失败: {e}")

    def stop_process(self, name):
        """停止指定进程"""
        if name not in self.processes or self.processes[name].poll() is not None:
            logger.warning(f"{name}未在运行")
            return

        logger.info(f"停止{name}...")

        # 根据操作系统选择终止进程的方式
        if platform.system() == 'Windows':
            subprocess.call(['taskkill', '/F', '/T', '/PID', str(self.processes[name].pid)])
        else:
            os.kill(self.processes[name].pid, signal.SIGTERM)
            self.processes[name].wait()

        logger.info(f"{name}已停止")

    def stop_all(self):
        """停止所有进程"""
        for name in list(self.processes.keys()):
            self.stop_process(name)

    def show_status(self):
        """显示各组件状态"""
        status = {
            'local': '运行中' if 'local' in self.processes and self.processes['local'].poll() is None else '已停止',
            'server': '运行中' if 'server' in self.processes and self.processes['server'].poll() is None else '已停止',
            'http_proxy': '运行中' if 'http_proxy' in self.processes and self.processes['http_proxy'].poll() is None else '已停止',
            'monitor': '运行中' if 'monitor' in self.processes and self.processes['monitor'].poll() is None else '已停止'
        }

        print("\n=== JumpTiger 状态 ===")
        print(f"本地客户端: {status['local']}")
        print(f"服务器: {status['server']}")
        print(f"HTTP代理: {status['http_proxy']}")
        print(f"监控面板: {status['monitor']}")
        print("========================\n")

    def edit_config(self):
        """编辑配置"""
        print("\n=== 当前配置 ===")
        for key, value in self.config.items():
            print(f"{key}: {value}")
        print("=================\n")

        print("输入新的配置值（直接回车保持不变）:")

        server = input(f"服务器地址 [{self.config.get('server', '127.0.0.1')}]: ")
        if server:
            self.config['server'] = server

        server_port = input(f"服务器端口 [{self.config.get('server_port', 8388)}]: ")
        if server_port:
            self.config['server_port'] = int(server_port)

        local_port = input(f"本地端口 [{self.config.get('local_port', 1080)}]: ")
        if local_port:
            self.config['local_port'] = int(local_port)

        password = input(f"密码 [{self.config.get('password', '******')}]: ")
        if password:
            self.config['password'] = password

        method = input(f"加密方法 [{self.config.get('method', 'aes-256-cfb')}]: ")
        if method:
            self.config['method'] = method

        timeout = input(f"超时时间 [{self.config.get('timeout', 600)}]: ")
        if timeout:
            self.config['timeout'] = int(timeout)

        http_port = input(f"HTTP代理端口 [{self.config.get('http_port', 8087)}]: ")
        if http_port:
            self.config['http_port'] = int(http_port)

        monitor_port = input(f"监控面板端口 [{self.config.get('monitor_port', 8088)}]: ")
        if monitor_port:
            self.config['monitor_port'] = int(monitor_port)

        self.save_config()
        print("\n配置已保存。重启服务以应用新配置。\n")

def show_menu():
    """显示菜单"""
    print("\n=== JumpTiger 管理菜单 ===")
    print("1. 启动本地客户端")
    print("2. 启动服务器")
    print("3. 启动HTTP代理")
    print("4. 启动监控面板")
    print("5. 停止本地客户端")
    print("6. 停止服务器")
    print("7. 停止HTTP代理")
    print("8. 停止监控面板")
    print("9. 停止所有服务")
    print("10. 显示状态")
    print("11. 编辑配置")
    print("0. 退出")
    print("============================\n")
    return input("请选择操作: ")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='JumpTiger管理工具')
    parser.add_argument('--start-all', action='store_true', help='启动所有服务')
    parser.add_argument('--stop-all', action='store_true', help='停止所有服务')
    parser.add_argument('--start-local', action='store_true', help='启动本地客户端')
    parser.add_argument('--start-server', action='store_true', help='启动服务器')
    parser.add_argument('--start-http', action='store_true', help='启动HTTP代理')
    parser.add_argument('--start-monitor', action='store_true', help='启动监控面板')
    args = parser.parse_args()

    manager = JumpTigerManager()

    # 处理命令行参数
    if args.start_all:
        manager.start_local()
        manager.start_server()
        manager.start_http_proxy()
        manager.start_monitor()
        return
    elif args.stop_all:
        manager.stop_all()
        return
    elif args.start_local:
        manager.start_local()
        return
    elif args.start_server:
        manager.start_server()
        return
    elif args.start_http:
        manager.start_http_proxy()
        return
    elif args.start_monitor:
        manager.start_monitor()
        return

    # 交互式菜单
    try:
        while True:
            choice = show_menu()

            if choice == '1':
                manager.start_local()
            elif choice == '2':
                manager.start_server()
            elif choice == '3':
                manager.start_http_proxy()
            elif choice == '4':
                manager.start_monitor()
            elif choice == '5':
                manager.stop_process('local')
            elif choice == '6':
                manager.stop_process('server')
            elif choice == '7':
                manager.stop_process('http_proxy')
            elif choice == '8':
                manager.stop_process('monitor')
            elif choice == '9':
                manager.stop_all()
            elif choice == '10':
                manager.show_status()
            elif choice == '11':
                manager.edit_config()
            elif choice == '0':
                manager.stop_all()
                print("感谢使用，再见！")
                break
            else:
                print("无效选择，请重试")

            # 暂停一下，让用户看到输出
            if choice not in ['0', '10', '11']:
                time.sleep(1)
    except KeyboardInterrupt:
        print("\n程序被中断")
        manager.stop_all()

if __name__ == '__main__':
    main()
