# 加密代理项目

这是一个基于Python实现的加密代理系统，包含服务器端和客户端组件，支持SOCKS5协议和AES加密。

## 功能特性

- 支持AES-256-CFB加密
- 支持SOCKS5协议
- 服务器端监控和Web界面
- 客户端GUI和命令行界面
- 自动重连和故障恢复
- 流量统计和连接监控

## 安装依赖

在运行项目前，请确保安装以下依赖：

```bash
pip install pycryptodome PyQt5
```

## 快速开始

### 1. 配置服务器

1. 复制`config_template.json`为`server_config.json`
2. 修改`server_config.json`中的服务器配置
3. 启动服务器：

```bash
python proxy_project/server/main.py -c server_config.json
```

### 2. 配置客户端

1. 复制`config_template.json`为`client_config.json`
2. 修改`client_config.json`中的客户端配置（确保与服务器配置匹配）
3. 启动客户端：

图形界面：
```bash
python proxy_project/client/main.py -c client_config.json
```

命令行界面：
```bash
python proxy_project/client/main.py -c client_config.json --cli
```

## 文件结构

```
proxy_project/
├── client/                  # 客户端代码
│   ├── encryption/          # 加密模块
│   ├── gui/                 # 图形界面
│   ├── utils/               # 工具类
│   ├── local.py             # 本地代理实现
│   └── main.py              # 客户端入口
├── server/                  # 服务器端代码
│   ├── encryption/          # 加密模块
│   ├── monitor/             # 监控模块
│   ├── utils/               # 工具类
│   ├── encrypted_server.py  # 加密服务器实现
│   └── main.py              # 服务器入口
├── config_template.json     # 配置文件模板
└── README.md                # 项目文档
```

## 配置选项

| 配置项 | 描述 | 默认值 |
|--------|------|--------|
| server | 服务器地址 | 127.0.0.1 |
| server_port | 服务器端口 | 8388 |
| local_address | 本地监听地址 | 127.0.0.1 |
| local_port | 本地监听端口 | 1080 |
| password | 加密密码 | default_password |
| timeout | 超时时间(秒) | 300 |
| method | 加密方法 | aes-256-cfb |
| fast_open | TCP Fast Open | false |
| verbose | 详细日志 | false |
| connect_timeout | 连接超时(秒) | 5 |
| retry_times | 重试次数 | 3 |
| retry_interval | 重试间隔(秒) | 2 |
| auto_reconnect | 自动重连 | true |
| max_connections | 最大连接数 | 100 |

## 许可证

本项目采用MIT许可证。
