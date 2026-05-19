# L2 Hook 项目

## 目标
通过 Frida hook AX.exe 的 recv/WSARecv 函数，截获 Level-2 行情原始网络数据。

## 背景
- 内存扫描方案（l2_main_v2.py）存在性能和稳定性问题
- AX.exe 32-bit，Level-2 数据单独注册登录
- 内存中数据为明文（20字节/条：price float32 + vol + cnt + status + seq）
- 网络数据大概率也是明文

## 工具栈
- Python 3.13 + Frida 17.9.10
- Wireshark/tshark 4.6.4（抓包验证）
- x64dbg（调试）

## 执行路线图
参照《证券客户端网络层数据采集执行路线图》

### Step 1-2: ✅ 工具安装 + 进程确认
### Step 3: hook_recv.py — Hook recv/WSARecv
### Step 4: 验证数据流
### Step 5: 关键实验（不切股票是否有数据）
### Step 6: 保存原始数据包
### Step 7: 观察协议结构

## 文件
- `hook_recv.py` — 主 hook 脚本
- `raw_packets/` — 原始数据包存储
- `work_log.md` — 工作日志

## 当前状态
- [x] Frida 已安装 (17.9.10)
- [x] Wireshark 已安装 (4.6.4)
- [x] hook_recv.py 已编写
- [ ] Hook 测试运行
- [ ] 数据流验证
- [ ] 协议分析
