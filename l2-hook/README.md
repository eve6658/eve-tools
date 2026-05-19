# 通达信 L2 数据捕获

通过 Frida hook AX.exe 的 recv/WSARecv，捕获通达信客户端的网络数据流。

## 协议格式

```
TCP 明文 → FD FD FD FD + 8字节ASCII hex长度 + payload → zlib → JSON(GBK)
```

### 帧结构
| 偏移 | 长度 | 说明 |
|------|------|------|
| 0 | 4 | Magic: `FD FD FD FD` |
| 4 | 8 | ASCII 十六进制 payload 长度 |
| 12 | N | payload 数据 |

### 消息类型
| Route | 内容 |
|-------|------|
| `push_notify_msg` | 推送通知 |
| `S200004` | 选股结果/订阅推送 |

## 使用

### 捕获数据
```bash
# 自动捕获（9:15-15:05）
python tdx_capture.py

# 指定时长
python tdx_capture.py --hours 4
python tdx_capture.py --until 11:30
```

### 解码数据
```bash
python decode_v2.py <packets_file.bin>
```

## AX.exe 连接

| 远端 | 端口 | 用途 |
|------|------|------|
| 59.36.5.11 | 9902 | 行情主站 |
| 101.230.126.11 | 8205 | 登录/认证 |
| 123.125.108.247-249 | 6928 | L2 数据通道 |

## 文件说明

| 文件 | 说明 |
|------|------|
| `tdx_capture.py` | 自动捕获（推荐） |
| `hook_recv.py` | 基础版 Frida hook |
| `simple_capture.py` | 简单 raw 捕获 |
| `decode_v2.py` | 离线解码 |
| `test_*.py` | 各种测试脚本 |
