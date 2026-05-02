# 语音实时转文字：随身边缘AI输入通道研究

> 作者：Adam & Eve | 日期：2026-05-03
> 
> 核心命题：**Apple Watch + AirPods = 贾维斯终端**，摆脱键盘与屏幕的束缚，语音是唯一的输入输出。

---

## 一、Whisper 生态调研

GitHub 上跟 Whisper 相关的开源项目，光星星过千的就有十几个，每个都说自己更快、更强，但全跑了一遍，真正能打的没几个。

### 选型前提

选 Whisper 的核心原因只有一个：**多语言支持**——中文、英文、日文、韩文都得能识别。如果只做中文，根本不会选 Whisper，FunASR 更好。但多语言这个需求，目前只有 Whisper 能扛。

### ❌ 不适合的项目

| 项目 | 问题 |
|------|------|
| whisper-finetune | LoRA 微调，工程完整度高，但离线识别，先录完再转，流式用不了 |
| whisper-jax | 速度快 70 倍，但峰值性能依赖 TPU，普通 GPU 优势不大 |
| buzz | 桌面 APP，不适合后端部署 |
| whisper-timestamped | 只做时间戳，没有加速和部署 |
| whisper-mic | 场景最贴合（麦克风输入实时转录），但只支持英文 |
| whisper_real_time / whisper_live | 边录边识别，但没加速优化，中文延迟偏高 |
| whisper-diarization | 能识别"谁在什么时候说了什么"，但串了 4-5 个模型，太重 |

### 功能聚焦但场景窄的

| 项目 | 特点 |
|------|------|
| faster-whisper | Ctranslate2 加速，速度 4 倍，内存更低，支持 INT8 量化，行业广泛使用。但只是推理引擎，不提供流式输出，需自己组合 |
| yt-whisper | 只做 YouTube 字幕，场景太窄 |

### ✅ 两个重量级选手

#### WhisperX — 短期最优解

- 综合评价最高
- large-v2 做 70 倍实时速度
- 不到 8GB 显存就能跑
- **关键能力：单词级时间戳**——每个字精确对应到音频时间位置
- 做流式展示和字幕对齐，这个能力太重要了
- **短期方案，它最稳**

#### Distil-Whisper — 长期最优解

- 把 large-v2 蒸馏成小模型
- 速度快 6 倍，体积小一半
- 错误率只涨不到 1%，性价比炸裂
- **致命问题：只发布了英文模型**，其他语言得自己蒸馏
- 门槛有，但走通了长期收益最大

### 结论

> 多语言需求选 Whisper 没毛病，但具体用哪个得看场景。
> - **短期：WhisperX 最稳**
> - **长期：自蒸馏 Distil-Whisper 收益最大**
> - 选项目不是选最好的，是选最合适的。

---

## 二、从调研到产品：贾维斯架构

### 核心愿景

Apple Watch + AirPods = 随身 AI 终端。不需要掏手机、不需要打字、不需要看屏幕。说话就是输入，听就是输出。

### 系统架构

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  AirPods 🎤 │────▶│  Apple Watch │────▶│  Edge ASR   │
│  (输入+输出) │◀────│  (中继/控制)  │◀────│  WhisperX   │
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                 │
                                          ┌──────▼──────┐
                                          │  AI Agent   │
                                          │ (OpenClaw)  │
                                          └──────┬──────┘
                                                 │
                                          ┌──────▼──────┐
                                          │  TTS 合成   │
                                          │ (MiMo-TTS)  │
                                          └─────────────┘
```

### 关键问题：Watch 上怎么拿到音频流

watchOS 的限制很死，三条路：

#### 方案一：Watch 原生 App（最靠谱）

- 用 `AVAudioEngine` 录音，后台运行
- Watch 本身算力有限，录音+编码后推到本地服务器
- 本地服务器跑 WhisperX，延迟可控在 500ms 内

#### 方案二：Siri Shortcut 中转（最快落地）

- 创建 Shortcut：录音 → 发 HTTP 请求 → 播放返回音频
- 缺点：不是真正的流式，每次要等 ASR 完整出结果
- **胜在零开发量，当天就能跑通**

#### 方案三：OpenClaw 手机 App 中继

- Phone 做计算中枢，Watch 做遥控器
- Watch 上按一下触发手机端录音

### 落地建议

**先走 Shortcut 路线验证价值**，别一上来就写原生 App：

```
Watch Siri Shortcut:
  1. 录音 N 秒
  2. POST 到 http://<server>:8000/transcribe
  3. 拿到文字 → 发给 AI Agent
  4. 拿到回复 → 用"朗读文本"播报
```

跑通了再优化——流式识别、后台常驻、原生 App。

Agent 层不需要动——已经在用 OpenClaw，把消息通道从 QQ Bot 换成语音管道就行。

---

## 三、补充视角

### 流式延迟的真正瓶颈

不在 ASR 本身，而在 **VAD（语音端点检测）+ chunk 策略**。WhisperX 再快，如果 VAD 切句不准或者 chunk 太大，用户体验还是卡。Realtime Whisper 那几个项目虽然没加速，但 VAD 做得比 WhisperX 好。

### 端侧部署的现实

- large-v2 要 8GB 显存，手机/树莓派跑不动
- 如果目标是手机端：faster-whisper + INT8 量化
- 或者 **sherpa-onnx**（纯 C++，ARM 优化，有 Android/iOS binding）

### 蒸馏之外的路

- **whisper.cpp**：纯 C 推理，CPU 上能到实时的 3-5 倍，不需要 GPU
- 对边缘设备来说，这可能比 Distil-Whisper 更实际

---

## 四、自建极简 Watch App（SwiftUI + MQTT）

如果追求极低延迟和自定义 UI，可以编写一个轻量级 Watch 独立应用。

### 通信协议

建议使用 **MQTT 协议**。OpenClaw 端运行一个 MQTT 客户端监听 Topic，Watch 端作为 Publisher。MQTT 比 HTTP 轮询延迟低一个数量级，适合实时交互。

### 开发重点

- 用 **SwiftUI** 构建「一键触发」按钮或 Slider
- 利用 **WatchConnectivity** 框架确保数据传输
- 场景模拟：Watch 上设置几个预设指令（如：「启动 L2 监控」「停止所有 Agent」），点一下即可远程控制

### 核心技术建议

| 模块 | 方案 |
|------|------|
| 内网穿透 | Tailscale 或 frp（Ubuntu 在家、Watch 在外时） |
| 安全验证 | API 加 Auth Token，防止接口被扫后恶意调用 |
| 反馈闭环 | OpenClaw 任务完成后，通过 Bark/Pushover 推送通知到 iPhone/Watch |

## 五、当前 OpenClaw 插件配置

| 通道 | 状态 | 说明 |
|------|------|------|
| QQ Bot | ✅ 在用 | 当前主要通信通道 |
| 企业微信 (WeCom) | ✅ 已加载 | wecom-openclaw-plugin |
| 微信 (WeChat) | ✅ 已加载 | openclaw-weixin |
| **MQTT** | ❌ 未接入 | Watch App 集成目标 |

### MQTT 集成路径

要让 Watch App 接入 OpenClaw，需要：

1. **服务端**：在 Air7 服务器部署 MQTT Broker（Mosquitto），OpenClaw 注册一个 MQTT 插件监听指定 Topic
2. **Watch 端**：SwiftUI App 连接 Broker，发布语音转文字结果到 `eve/input` Topic
3. **响应**：OpenClaw 处理后发布到 `eve/output/{device_id}`，Watch 订阅并播报

```
Watch App                    MQTT Broker                 OpenClaw
   │                             │                          │
   │── publish(eve/input) ──────▶│── on_message ──────────▶│
   │                             │                          │ (处理请求)
   │◀── subscribe(eve/output) ◀─│◀── publish ─────────────│
   │                             │                          │
```

---

## 六、项目状态

| 组件 | 状态 |
|------|------|
| WhisperX 服务端 | 待部署（FastAPI + WhisperX，跑在 Air7 服务器） |
| MQTT Broker | 待部署（Mosquitto，Air7 本地） |
| Apple Watch SwiftUI App | 待开发（一键触发 + MQTT Publisher） |
| OpenClaw MQTT 插件 | 待开发（监听 eve/input Topic） |
| OpenClaw Agent | ✅ 已有（当前通过 QQ Bot 通信） |
| TTS 输出 | ✅ MiMo-TTS 已配置 |
| 语音输入通道 | 🔄 等 ASR 服务端 + MQTT 就绪 |

---

*This document is a living spec. Updates will be pushed as the project progresses.*
