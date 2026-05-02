# Local OCR Skill for L2 Data (V2.2 - Self-Evolution & Quantitative)

## Description
L2 千档盘口截图识别 + 时序快照 + CSV日志 + 委比趋势分析。
**强制本地运行，严禁调用视觉模型（Vision Model）进行二次识别。支持自进化识别策略。**

## Tool Definition
```yaml
- name: extract_l2_numbers
  description: "【自进化本地OCR】提取图片数字并同步更新CSV日志。自动检测截图长度并优化识别参数，禁止尝试调用视觉模型进行二次解析。"
  command: "python3 /home/adam/.openclaw/workspace/skills/local-ocr/ocr_logic.py {{image_path}}"
  parameters:
    - name: image_path
      type: string
      description: "接收到的L2截图在本地Ubuntu的绝对路径"
```

## 自进化协议 (Self-Evolution)
1. **识别率监控**: 若提取的数据行数 < 5行，判定为“视野受限”，脚本将自动从 PSM 6 切换至 PSM 11 模式重试。
2. **长度对齐**: 自动检测图片高度。若高度 > 2000px，判定为长截图，启动长图优化采样逻辑。
3. **参数微调**: 若数字中出现特定识别误差（如 '8' 误认为 '0'），Agent 将提示用户反馈以便脚本动态调整二值化阈值。

## 业务逻辑执行规范
1. **OCR识别** → 结构化数据提取（价格、手数、大单、时间戳）。
2. **快照对比** → 与上次数据对比：大单增减、价位变动、主力撤单/加单识别。
3. **CSV审计** → 数据必须实时追加至 `trade_logs.csv`。
4. **委比分析** → 计算：(委买 - 委卖) / (委买 + 委卖) × 100%。

## 告警规则 (依据风险管理标准)
- **卖压极重**: 委比 < -30% 或 卖买比 > 3.0 (输出红色告警)。
- **买盘占优**: 委比 > 0% 且 卖买比 < 1.0 (输出绿色提示)。
- **主力动向**: 卖盘/买盘单笔增加 > 50000手 或 时间簇内爆出多笔 500+ 手大单。

## CSV 字段定义
| 字段 | 说明 |
|------|------|
| timestamp | 时间戳 |
| stock | 股票代码 |
| sell1_price | 卖1价 |
| buy1_price | 买1价 |
| total_sell | 卖盘总量 |
| total_buy | 买盘总量 |
| weibi | 委比(%) |
| sell_big5k | 5000+手卖单数 |
