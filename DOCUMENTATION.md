# JumpTiger Python 增强版 - 技术文档

## 架构概述

JumpTiger增强版由以下几个主要组件组成：

1. **服务器端 (server3.py)**
   - 接收来自客户端的加密连接
   - 解密请求并转发到目标服务器
   - 加密目标服务器的响应并发送回客户端

2. **客户端 (local3.py)**
   - 提供SOCKS5代理接口
   - 加密本地应用程序的请求并发送到服务器
   - 解密服务器的响应并返回给本地应用程序

3. **HTTP代理 (http_proxy.py)**
   - 提供HTTP/HTTPS代理接口
   - 支持标准HTTP代理协议
   - 处理CONNECT方法用于HTTPS连接

4. **监控系统 (monitor.py)**
   - 提供Web界面展示系统状态
   - 收集和展示流量统计数据
   - 显示连接历史和实时图表

5. **管理界面 (start.py)**
   - 统一管理所有组件
   - 提供命令行和交互式界面
   - 简化配置和操作流程

## 技术细节

### 加密实现

#### AES-256-CFB加密

```python
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
```

加密过程：
1. 使用SHA-256哈希函数从密码生成256位密钥
2. 生成16字节的随机初始化向量(IV)
3. 使用密钥和IV创建AES-CFB模式的加密器
4. 第一个数据包包含IV和加密数据
5. 后续数据包只包含加密数据

### SOCKS5协议实现

客户端实现了标准的SOCKS5协议，处理流程如下：

1. **握手阶段**
   ```python
   # 接收SOCKS5握手请求
   sock.recv(262)  # 跳过SOCKS5握手
   sock.send(b"\x05\x00")  # 发送无需认证的响应
   ```

2. **请求阶段**
   ```python
   # 接收连接请求
   data = sock.recv(4)
   mode = data[1]
   
   # 解析地址类型
   addrtype = data[3]
   
   if addrtype == 1:  # IPv4
       addr_ip = sock.recv(4)
       addr = socket.inet_ntoa(addr_ip)
   elif addrtype == 3:  # 域名
       addr_len = sock.recv(1)[0]
       addr = sock.recv(addr_len)
       addr = addr.decode('utf-8')
   ```

3. **响应阶段**
   ```python
   # 回复客户端连接成功
   reply = b"\x05\x00\x00\x01"
   reply += socket.inet_aton('0.0.0.0') + struct.pack(">H", 0)
   sock.send(reply)
   ```

### HTTP/HTTPS代理实现

HTTP代理支持标准的HTTP代理协议，包括CONNECT方法：

```python
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
```

### 监控系统

监控系统使用简单的HTTP服务器提供Web界面，并使用Chart.js绘制流量图表：

```python
def get_stats(self):
    """获取统计数据"""
    with self.lock:
        # 更新运行时间
        self.stats['uptime'] = time.time() - self.start_time
        return {
            'stats': dict(self.stats),
            'connections': list(self.connections.values())
        }
```

前端使用JavaScript定期获取统计数据并更新界面：

```javascript
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
        })
}
```

## 配置详解

### 基本配置 (config.json)

```json
{
    "server": "127.0.0.1",      // 服务器地址
    "server_port": 8086,        // 服务器端口
    "local_port": 1030,         // 本地SOCKS5代理端口
    "password": "pwd",          // 加密密码
    "timeout": 600,             // 连接超时时间(秒)
    "method": "aes-256-cfb"     // 加密方法
}
```

### 扩展配置选项

可以在start.py中通过交互式界面添加以下配置：

- `http_port`: HTTP代理端口 (默认8087)
- `monitor_port`: 监控界面端口 (默认8088)

## 使用示例

### 1. 基本使用

启动所有服务：

```bash
python start.py --start-all
```

然后在浏览器中配置SOCKS5代理为 127.0.0.1:1030 或HTTP代理为 127.0.0.1:8087。

### 2. 仅作为客户端使用

如果服务器已经部署在远程主机上：

```bash
# 编辑配置文件，设置远程服务器地址
# 然后启动本地客户端
python start.py --start-local
```

### 3. 仅作为服务器使用

在服务器上部署：

```bash
python start.py --start-server
```

### 4. 使用监控功能

启动监控界面：

```bash
python start.py --start-monitor
```

然后在浏览器中访问 http://127.0.0.1:8088

## 性能优化

1. **使用gevent**

   如果安装了gevent库，系统会自动使用它来提高性能：

   ```python
   try:
       import gevent
       import gevent.monkey
       gevent.monkey.patch_all(dns=gevent.version_info[0]>=1)
   except ImportError:
       gevent = None
       print('warning: gevent not found, using threading instead', file=sys.stderr)
   ```

2. **TCP_NODELAY选项**

   禁用Nagle算法以减少延迟：

   ```python
   remote.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
   ```

3. **select多路复用**

   使用select进行I/O多路复用，提高并发性能：

   ```python
   def handle_tcp(self, sock, remote):
       try:
           fdset = [sock, remote]
           while True:
               r, w, e = select.select(fdset, [], [])
               if sock in r:
                   # 处理本地到远程的数据
               if remote in r:
                   # 处理远程到本地的数据
       finally:
           sock.close()
           remote.close()
   ```

## 故障排除

### 常见问题

1. **连接超时**
   - 检查服务器地址和端口是否正确
   - 确认防火墙未阻止连接
   - 增加timeout值

2. **加密错误**
   - 确保客户端和服务器使用相同的密码和加密方法
   - 检查是否正确安装了pycryptodome库

3. **端口冲突**
   - 如果端口已被占用，修改配置文件中的端口设置

### 日志分析

所有组件都使用Python的logging模块记录日志：

```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
```

增加日志级别可以获取更详细的信息：

```python
logging.basicConfig(level=logging.DEBUG, ...)
```

## 安全考虑

1. **加密强度**
   - AES-256-CFB提供强大的加密保护
   - 每个连接使用随机IV，防止重放攻击

2. **密码安全**
   - 使用SHA-256哈希函数处理密码
   - 避免在代码中硬编码密码

3. **网络安全**
   - 监控界面仅绑定到本地地址
   - 服务器默认只监听本地连接

## 扩展开发

### 添加新的加密方法

在Encryptor类中添加新的加密方法：

```python
def __init__(self, key: str, method: str = 'aes-256-cfb'):
    # 现有代码...
    
    if method == 'aes-256-cfb':
        # 现有AES实现...
    elif method == 'chacha20':
        # 添加ChaCha20实现
        from Crypto.Cipher import ChaCha20
        self.key = hashlib.sha256(self.key).digest()
        self.nonce = get_random_bytes(12)
        self.cipher = ChaCha20.new(key=self.key, nonce=self.nonce)
    else:
        # 保留原有的table方法...
```

然后更新encrypt和decrypt方法以支持新的加密方法。

### 添加新功能

项目的模块化设计使添加新功能变得简单。例如，添加PAC代理自动配置：

1. 创建新文件 `pac_server.py`
2. 实现PAC文件生成和HTTP服务
3. 在start.py中添加对新组件的支持

## 参考资料

- [SOCKS5协议规范 (RFC 1928)](https://tools.ietf.org/html/rfc1928)
- [HTTP代理规范](https://tools.ietf.org/html/rfc7230)
- [AES加密标准](https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.197.pdf)
- [Python Socket编程](https://docs.python.org/3/library/socket.html)
- [PyCryptodome文档](https://pycryptodome.readthedocs.io/)
