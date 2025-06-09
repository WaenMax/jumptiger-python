# 安装指南

本文档提供了JumpTiger Python增强版的详细安装和配置说明。

## 系统要求

- Python 3.6或更高版本
- pip (Python包管理器)
- 支持的操作系统: Windows, macOS, Linux

## 安装步骤

### 1. 安装Python 3

如果您的系统尚未安装Python 3，请从[Python官网](https://www.python.org/downloads/)下载并安装。

确认Python安装成功：

```bash
python --version
# 或
python3 --version
```

### 2. 下载项目

克隆或下载项目到本地：

```bash
git clone https://github.com/yourusername/jumptiger-python-enhanced.git
cd jumptiger-python-enhanced
```

或者直接下载ZIP压缩包并解压。

### 3. 安装依赖

安装所需的Python库：

```bash
pip install pycryptodome
# 可选: 安装gevent以提高性能
pip install gevent
```

### 4. 配置

创建或编辑`config.json`文件：

```json
{
    "server": "your_server_ip",
    "server_port": 8086,
    "local_port": 1030,
    "password": "your_password",
    "timeout": 600,
    "method": "aes-256-cfb"
}
```

参数说明：
- `server`: 服务器IP地址
- `server_port`: 服务器端口
- `local_port`: 本地SOCKS5代理端口
- `password`: 加密密码
- `timeout`: 连接超时时间(秒)
- `method`: 加密方法，推荐使用"aes-256-cfb"

### 5. 运行

#### 使用管理界面

启动管理界面：

```bash
python start.py
```

然后按照菜单提示操作。

#### 使用命令行参数

```bash
# 启动所有服务
python start.py --start-all

# 只启动客户端
python start.py --start-local

# 只启动服务器
python start.py --start-server

# 启动HTTP代理
python start.py --start-http

# 启动监控面板
python start.py --start-monitor
```

### 6. 验证安装

1. 启动本地客户端后，配置浏览器使用SOCKS5代理：
   - 地址: 127.0.0.1
   - 端口: 1030 (或您在配置中指定的端口)

2. 或者配置HTTP代理：
   - 地址: 127.0.0.1
   - 端口: 8087

3. 访问[ip.gs](http://ip.gs)或[ipinfo.io](https://ipinfo.io)检查您的IP地址是否已更改。

4. 访问监控面板查看连接状态：
   - 打开浏览器访问: http://127.0.0.1:8088

## 常见问题

### 1. 无法连接到服务器

- 检查服务器IP地址和端口是否正确
- 确认服务器防火墙已开放相应端口
- 检查服务器是否正常运行

### 2. 安装依赖失败

如果安装pycryptodome失败，可以尝试：

```bash
# Windows可能需要安装Visual C++ Build Tools
pip install --upgrade pip
pip install pycryptodome
```

### 3. 权限问题

在Linux/macOS系统上，可能需要使用sudo运行：

```bash
sudo python start.py
```

或者给脚本添加执行权限：

```bash
chmod +x start.py
./start.py
```

### 4. 端口冲突

如果出现端口已被占用的错误，请修改配置文件中的端口设置。

## 更多信息

- 详细文档请参阅[DOCUMENTATION.md](DOCUMENTATION.md)
- 常见问题解答请参阅[FAQ.md](FAQ.md)（如果有）
- 贡献指南请参阅[CONTRIBUTING.md](CONTRIBUTING.md)
