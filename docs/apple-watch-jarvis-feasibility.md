# Apple Watch + AirPods 贾维斯终端 — 可行性调研

> 作者：Eve | 日期：2026-05-03
> 状态：技术预研（非最终方案）

---

## 一、目标定义

**核心愿景**：Apple Watch + AirPods = 随身 AI 终端，语音是唯一交互方式。

**用户场景**：
- 戴着 AirPods 走在路上，对 Watch 说一句话 → AI Agent 处理 → 语音回复
- 不需要掏手机、不需要打字、不需要看屏幕
- 预设快捷指令（"启动 L2 监控"、"查一下邮件"）一键触发

**判定标准**：端到端延迟 < 2 秒（说话 → 听到回复），可用率 > 95%。

---

## 二、watchOS 技术约束

### 2.1 能做什么 ✅

| 能力 | 说明 |
|------|------|
| 麦克风录音 | `AVAudioEngine` 在 watchOS 上可用，支持后台音频 session |
| 网络请求 | `URLSession` 支持 HTTP/HTTPS，可调后端 API |
| 后台刷新 | `WKApplicationRefreshBackgroundTask` 每小时可被唤醒一次 |
| 长时间后台任务 | 音频 app 可以持续运行（类似播客/录音 app） |
| WatchConnectivity | Watch ↔ iPhone 实时通信，延迟低 |
| SwiftUI | 自定义 UI 完全可行 |
| 蓝牙 | AirPods 自动连接，系统级管理 |

### 2.2 不能做什么 / 严重限制 ❌

| 限制 | 影响 | 解法 |
|------|------|------|
| **watchOS 没有 WebSocket** | 无法维持长连接 | 用 HTTP 轮询或 WatchConnectivity 中转 |
| **后台 CPU 时间极短** | 非音频 task 只有几秒 | 音频 session 可延长，但需持续播放/录音 |
| **无自定义推送** | 不能在 watch 上运行自定义通知处理 | 用 Apple Push + complication 显示 |
| **内存限制** | 约 50MB 可用 | ASR 模型不可能在 watch 上跑，必须推到服务器 |
| **无原生 MQTT 库** | watchOS 没有官方 MQTT SDK | 用 URLSession 做 HTTP 长轮询，或第三方轻量 MQTT 客户端 |
| **Watch App 不能独立安装** | 必须配合 iPhone App | 需要一个配套的 iOS App |

### 2.3 关键发现：watchOS 的后台音频

这是**唯一**能让 Watch App 持续运行的方式：

```swift
// 配置音频 session
let session = AVAudioSession.sharedInstance()
try session.setCategory(.record, mode:.default, options: [.defaultToSpeaker])
try session.setActive(true)

// 开始录音 → App 进入后台但仍运行
let engine = AVAudioEngine()
// ... 配置 input node
engine.inputNode.installTap(onBus: 0, bufferSize: 1024, format: nil) { buffer, time in
    // 音频数据实时到达
    // 在这里发送到服务器
}
try engine.start()
```

**⚠️ 但是**：watchOS 对后台音频有严格审核。Apple 可能拒绝"假音频 app"——你必须真的在录音，而不是用它来保持 App 存活。

---

## 三、通信方案对比

### 方案 A：HTTP 直连（最简单）

```
Watch ──HTTP POST──▶ Air7 服务器 ──HTTP Response──▶ Watch
```

- **延迟**：网络 RTT + ASR 处理时间，预计 1-3 秒
- **优点**：零依赖，`URLSession` 直接搞定
- **缺点**：不是流式，每次等完整结果；服务器不能主动推
- **适合**：快捷指令场景（"查天气"、"启动监控"）

### 方案 B：WatchConnectivity（Apple 原生）

```
Watch ──WatchSession──▶ iPhone ──HTTP/WebSocket──▶ Air7 服务器
```

- **延迟**：Watch→iPhone 近乎即时 + iPhone→服务器 RTT
- **优点**：Apple 官方支持，无需额外协议
- **缺点**：依赖 iPhone 在附近且 App 在后台；iPhone 挂了就断
- **适合**：家里/办公室场景

### 方案 C：MQTT over HTTP（推荐）

```
Watch ──HTTP long-poll──▶ MQTT Broker (Mosquitto) ──▶ OpenClaw
```

- **延迟**：长轮询 ~200ms + ASR 处理
- **优点**：真正的发布/订阅，双向通信，服务器可主动推
- **缺点**：需要部署 Mosquitto；watchOS 没有原生 MQTT，需自己封装
- **实现**：用 `URLSession` 的 `dataTask` 做 HTTP 长轮询模拟 MQTT subscribe

### 方案 D：SSE / Server-Sent Events

```
Watch ──POST──▶ Server ──SSE stream──▶ Watch
```

- **延迟**：接近实时
- **优点**：单向流（服务器→Watch），比 WebSocket 轻
- **缺点**：只有服务器能推，Watch→服务器还是要 POST
- **适合**：AI 回复的流式输出（打字机效果）

### 推荐组合

**快捷指令用 HTTP（方案 A）+ 实时交互用 SSE（方案 D）**

理由：
- 快捷指令是单次请求/响应，HTTP 最简单
- AI 语音回复需要流式输出（不然用户等太久），SSE 够用
- 不需要引入 MQTT 的复杂度，除非以后要做多设备协调

---

## 四、端到端延迟分析

### 语音链路分解

```
用户说话 → Watch 录音 → 上传音频 → ASR 转文字 → Agent 处理 → TTS 合成 → 下载音频 → AirPods 播放
  ①         ②          ③           ④            ⑤           ⑥          ⑦          ⑧
```

| 环节 | 耗时 | 优化空间 |
|------|------|----------|
| ① 用户说话 | 1-3 秒 | 用户控制 |
| ② Watch 本地录音 | ~0ms | 实时流出 |
| ③ 上传音频 | 200-500ms | 内网优先，压缩音频 |
| ④ ASR（WhisperX） | 300-800ms | large-v2 + GPU 加速 |
| ⑤ Agent 处理 | 500-2000ms | 模型选择 + prompt 优化 |
| ⑥ TTS 合成 | 300-600ms | MiMo-TTS |
| ⑦ 下载音频 | 100-300ms | 内网 |
| ⑧ AirPods 播放 | ~0ms | 蓝牙延迟可忽略 |

**总计：1.4 - 4.2 秒**

**目标 < 2 秒** → 需要：
- 内网部署（③⑦ < 200ms）
- ASR 用 large-v2 + INT8（④ < 500ms）
- Agent 用快速模型或缓存（⑤ < 800ms）
- **最关键：VAD 精准切句**，避免等用户说完才开始处理

---

## 五、VAD（语音端点检测）方案

这是**最容易被忽视但最影响体验的环节**。

### 5.1 Silero VAD（推荐）

- 模型极小（~2MB），CPU 即可运行
- 识别静音/语音切换，精度高
- 可以在 Watch 端运行（如果内存允许）或服务器端

### 5.2 双缓冲策略

```
Watch 持续录音 → 环形缓冲区
    │
    ├─ 检测到语音开始 → 开始向服务器推流
    ├─ 检测到语音结束 → 停止推送，标记 EOT
    └─ 服务器收到完整语音片段 → ASR 处理
```

### 5.3 Watch 端实现

```swift
// 简单的静音检测（不用 VAD 模型）
let threshold: Float = 0.01  // 音量阈值
var isRecording = false
var silenceCount = 0

engine.inputNode.installTap(onBus: 0, bufferSize: 1024, format: nil) { buffer, time in
    let level = buffer.averagePowerLevel  // 或计算 RMS
    if level > threshold {
        isRecording = true
        silenceCount = 0
        // 推送音频数据到服务器
    } else if isRecording {
        silenceCount += 1
        if silenceCount > 30 {  // 30 帧静音 ≈ 0.75 秒
            // 语音结束，发送 EOT 标记
            isRecording = false
        }
    }
}
```

---

## 六、安全架构

### 6.1 认证层

```
Watch App → POST /transcribe
Header: Authorization: Bearer <JWT>
Body: { "audio": "<base64>", "device_id": "adam-watch" }
```

- JWT 由 iPhone App 签发（登录 OpenClaw 后获取）
- Token 有效期 24 小时，过期自动刷新
- 每个设备独立 device_id

### 6.2 网络安全

| 层 | 方案 |
|----|------|
| 传输 | HTTPS（内网可用自签证书） |
| 认证 | JWT Bearer Token |
| 限流 | 每设备 10 次/分钟 |
| 内网穿透 | Tailscale（推荐）或 frp |

### 6.3 敏感操作确认

```
Agent 收到指令："删除所有邮件"
    │
    ├─ 检测到敏感操作
    ├─ 返回确认提示："确定要删除所有邮件吗？回复确认"
    └─ Watch 播放确认提示，用户语音确认后执行
```

---

## 七、开发计划

### Phase 0：验证核心假设（1-2 天）

**目标**：确认 Watch → 服务器 → 语音回复 这条链路能跑通

- [ ] Air7 部署 WhisperX + FastAPI 服务端
- [ ] Watch 用 Siri Shortcut 录音 → HTTP POST → 获取文字
- [ ] 测量端到端延迟

**交付物**：一个 Siri Shortcut + 一个 FastAPI 端点

### Phase 1：基础语音交互（1-2 周）

**目标**：完整的语音 → 文字 → AI 回复 → 语音播报闭环

- [ ] 服务端：WhisperX + Agent + TTS 的完整 pipeline
- [ ] Watch 端：SwiftUI App，录音 + 上传 + 播放回复
- [ ] VAD：简单静音检测
- [ ] 认证：JWT Token

**交付物**：可日常使用的 Watch App（基础版）

### Phase 2：实时交互（2-4 周）

**目标**：流式输出，延迟 < 2 秒

- [ ] SSE 流式输出（Agent 回复边生成边播报）
- [ ] WhisperX 流式识别
- [ ] 预设快捷指令系统
- [ ] 通知推送（Bark/Pushover）

**交付物**：接近「贾维斯」体验的 Watch App

### Phase 3：多设备 + 高级功能（可选）

- [ ] iPhone App 中继（Watch 在外时通过 iPhone 转发）
- [ ] 多设备协调（Watch + 手机 + 桌面）
- [ ] 本地 VAD 模型（Silero）部署到 Watch
- [ ] 声纹识别（区分家庭成员）

---

## 八、风险评估

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| Apple 审核拒绝（后台音频） | 中 | 高 | 提交真实的录音/语音助手类 App 描述 |
| ASR 中文延迟过高 | 低 | 中 | WhisperX 已验证 70x 实时速度 |
| 网络不稳定（外网） | 中 | 高 | Tailscale + 离线缓存预设指令 |
| AirPods 蓝牙断连 | 低 | 中 | 系统级管理，自动重连 |
| 内存不足（Watch 端） | 低 | 中 | 不在 Watch 上跑模型 |
| 隐私问题（录音上传） | 中 | 高 | 端到端加密 + 本地 VAD 只传语音段 |

---

## 九、结论

### 可行性判定：✅ 可行，但有约束

**能做的**：
- Watch 录音 → 服务器 ASR → Agent → TTS → AirPods 播报 ✅
- 快捷指令一键触发 ✅
- 内网环境下延迟 < 2 秒 ✅
- SwiftUI 自定义 UI ✅

**做不到的**：
- Watch 上跑 ASR 模型 ❌（必须推服务器）
- 真正的流式语音对话（像 GPT-4o 那样） ❌（有 1-2 秒延迟）
- 完全脱离 iPhone 独立运行 ❌（watchOS 限制）

### 推荐路径

1. **今晚**：用 Siri Shortcut 验证链路（零开发量）
2. **本周**：写 FastAPI 服务端 + 简单 Watch App
3. **本月**：打磨成可用的日常工具

### 投入预估

| 项目 | 工时 |
|------|------|
| FastAPI ASR 服务端 | 2-4 小时 |
| Watch SwiftUI App（基础版） | 1-2 周 |
| VAD + 流式优化 | 1 周 |
| 安全 + 认证 | 2-3 天 |
| **总计** | **约 3-4 周（兼职）** |

---

*This is a living document. Update as implementation progresses.*
