# Local OCR Skill for L2 Data (V4 - Auto-Detect + Orderbook + Tick)

## Description
L2 截图自动识别：千档盘口 + 逐笔成交。自动检测截图类型，自动分段处理超长截图。
**强制本地运行，严禁调用视觉模型（Vision Model）进行二次识别。**

## 支持的截图类型
| 类型 | 特征 | 输出 |
|------|------|------|
| **千档盘口** | 左右分栏（卖盘/买盘），如"卖1 6.26 34" | `{asks, bids, total_ask, total_bid, ratio}` |
| **逐笔成交** | 时间戳行，如"10:29:27 122.05 2 买单" | `[{t, p, v, a}, ...]` |

## Tool Definition
```yaml
- name: extract_l2_data
  description: "L2截图OCR：自动检测类型（千档盘口/逐笔成交），超长截图自动分段，双引擎（Tesseract/EasyOCR）"
  command: "/home/adam/open_claw_env/bin/python3 /home/adam/.openclaw/workspace/skills/local-ocr/ocr_logic.py {{image_path}}"
  parameters:
    - name: image_path
      type: string
      description: "L2截图的本地绝对路径"
```

## 使用方式
```bash
# 自动检测类型（推荐）
python3 ocr_logic.py <截图路径>

# 强制按千档盘口解析
python3 ocr_logic.py <截图路径> --orderbook

# 高精度模式（EasyOCR，逐笔成交专用）
python3 ocr_logic.py <截图路径> --accuracy
```

## 技术细节
- 超长截图自动分段（每段3000px，200px重叠防边界丢失）
- 千档盘口：左右分栏独立OCR，卖盘/买盘分开提取
- 逐笔成交：按时间戳行解析，(时间,价格,手数)去重
- 类型检测：取数据区300-800px OCR，优先匹配"卖N+价格+手数"（盘口），其次"委托价+方向"（逐笔）
