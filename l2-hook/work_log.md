# L2 Hook 工作日志

## 2026-05-19

### 16:00 - 16:25 系统排查 + 方案讨论

**L2 采集系统问题排查：**
- 发现 4 个 P0/P1 问题：内存读取崩溃、无成交断流、switching_lock 死锁、scheduler 未初始化
- 修改 l2_main_v2.py：重定位失败快速重试 + 连续 3 次失败退出
- 修改 scheduler_fixed.py：崩溃自动重启 + lock 超时释放
- 已通过 SSH 同步到 Windows (192.168.1.32)

**Hook 方案讨论：**
- 确认 AX.exe 是 32-bit
- 确认 Level-2 数据在内存中为明文（20字节/条）
- 读取了 MiMo 开发纪要：内存扫描 600 档方案因性能问题失败（50分钟未完成）
- 确定方向：hook recv/WSARecv 是更优路线

**工具安装（Windows 192.168.1.32）：**
- ✅ Python 3.13 (已有)
- ✅ Frida 17.9.10 (新装)
- ✅ Wireshark 4.6.4 + tshark (已有)
- ✅ x64dbg (已有)
- ❌ HxD (未装，不急)
- ✅ Windows 防火墙已关闭
- ✅ Windows 休眠已禁用

**hook_recv.py 编写：**
- Hook recv + WSARecv（含 overlapped 版本）
- 打印数据长度 + 前 32 字节 hex
- 支持保存原始数据包到文件
- 支持统计速率（pkt/s, KB/s）
- 已同步到 Windows `C:\l2-hook\`

### 关键发现
- Adam 指出"三思而后行" — 不要蛮干，先讨论方案可行性再动手
- 核心问题不是 GUI 自动化，而是数据获取方式本身
- 内存扫描路线太脆弱，hook recv 是更根本的解决方案

### 16:28 Frida Hook 调试
- Frida 17.x API 变化：`Module.findExportByName` 不存在，改用 `Process.enumerateModules` + `enumerateExports`
- 修正 JS 脚本后 hook 成功
- **测试结果**：10 秒内收到 3 个 recv 包，每个 43 字节，首字节 0xFD
- 43 字节包可能是心跳/控制包，非 L2 行情数据
- hook_recv.py 已更新为 Frida 17.x 兼容版本并同步到 Windows

### 关键发现
- Frida 17.x 中 `Module` 是 function 不是 object，只有 `getGlobalExportByName` 方法
- 正确做法：`Process.enumerateModules()` → 找 ws2_32.dll → `enumerateExports()` → 找 recv
- recv hook 地址: 0x762323a0

### 下一步
- [ ] 运行 hook_recv.py 长时间测试，观察数据流模式
- [ ] 验证数据流是否持续（Step 5 关键实验）
- [ ] 区分心跳包（43字节）和行情数据包
- [ ] 观察前 32 字节是否有可识别的协议结构
