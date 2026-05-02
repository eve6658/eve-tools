#!/usr/bin/env python3
"""
L2 OCR v4 — 自适应宽度 + 智能双引擎 + 自动分段裁切
- 自动检测图片宽度，按比例缩放跑道
- 超长截图自动分段处理，避免OOM
- 默认Tesseract（快），--accuracy模式用EasyOCR（准）
- 方向字段后处理修正
"""

import os, sys, re, json, subprocess
from PIL import Image, ImageOps, ImageEnhance

# ========== 分段裁切配置 ==========
MAX_HEIGHT = 3000        # 单段最大高度（px），超过则分段
HEADER_SKIP = 400        # 跳过标题区域（px）
OVERLAP = 200            # 分段重叠区（px），避免边界数据丢失

# ========== 跑道定义（基于575px基准宽度） ==========
BASE_WIDTH = 575
LANES_BASE = {
    "time": (10, 160),
    "price": (165, 285),
    "vol": (290, 425),
    "side": (430, 565)
}

def scale_lanes(img_width):
    """根据实际图片宽度等比缩放跑道"""
    scale = img_width / BASE_WIDTH
    lanes = {}
    for label, (x1, x2) in LANES_BASE.items():
        lanes[label] = (int(x1 * scale), int(x2 * scale))
    return lanes

# ========== 截图类型检测 ==========
def detect_type(img_path):
    """
    检测截图类型："tick"（逐笔成交）或 "orderbook"（千档盘口）
    方法：取数据区域一段OCR，看特征关键词
    """
    img = Image.open(img_path).convert('L')
    w, h = img.size
    region = img.crop((0, 300, w, 800))
    region = ImageEnhance.Contrast(region).enhance(2.0)
    region = region.point(lambda x: 255 if x > 140 else 0, '1')
    tmp = "/tmp/type_detect.jpg"
    region.save(tmp)
    
    result = subprocess.run(
        ['tesseract', tmp, '-', '-l', 'chi_sim+eng', '--psm', '6'],
        capture_output=True, text=True
    )
    if os.path.exists(tmp):
        os.remove(tmp)
    
    text = result.stdout
    # 千档盘口特征优先：卖N+价格+手数（如"卖1 6.26 34"）
    if re.search(r'(卖|买)\d+\s+[\d.]+\s+\d+', text):
        return "orderbook"
    # 逐笔成交特征词（委托价+手数+方向 列标题）
    if '委托价' in text and '方向' in text:
        return "tick"
    if '播放' in text:
        return "tick"
    # 兜底
    return "orderbook" if w >= 900 else "tick"

# ========== 千档盘口解析 ==========
def parse_orderbook(img_path):
    """
    千档盘口截图解析：左右分栏（卖盘/买盘）
    输出: {"asks": [...], "bids": [...], "total_ask": N, "total_bid": N, "ratio": N}
    """
    img = Image.open(img_path).convert('L')
    w, h = img.size
    mid = w // 2
    segments = split_image(img)
    all_asks = []
    all_bids = []
    seen = set()
    
    for crop, y_offset, seg_id in segments:
        enhancer = ImageEnhance.Contrast(crop)
        processed = enhancer.enhance(2.5)
        bw = processed.point(lambda x: 255 if x > 140 else 0, '1')
        
        # 左半：卖盘 / 右半：买盘
        for tmp_path, target_list, x1, x2 in [
            (f"/tmp/ob_ask_{seg_id}.jpg", all_asks, 0, mid),
            (f"/tmp/ob_bid_{seg_id}.jpg", all_bids, mid, w)
        ]:
            region = bw.crop((x1, 0, x2, bw.size[1]))
            region.save(tmp_path)
            result = subprocess.run(
                ['tesseract', tmp_path, '-', '-l', 'chi_sim+eng', '--psm', '6'],
                capture_output=True, text=True
            )
            for line in result.stdout.strip().split('\n'):
                matches = re.findall(r'(卖|买)(\d+)\s+([\d.]+)\s+(\d+(?:\.\d+)?万?)', line)
                for side, idx, price, vol in matches:
                    v = float(vol.replace('万', '')) * 10000 if '万' in vol else float(vol)
                    key = (side, int(idx))
                    if key not in seen:
                        seen.add(key)
                        target_list.append({'side': 'Ask' if side == '卖' else 'Bid', 'idx': int(idx), 'price': float(price), 'vol': int(v)})
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    
    asks = sorted(all_asks, key=lambda x: x['idx'])
    bids = sorted(all_bids, key=lambda x: x['idx'])
    total_ask = sum(a['vol'] for a in asks)
    total_bid = sum(b['vol'] for b in bids)
    ratio = round((total_bid - total_ask) / (total_bid + total_ask) * 100, 2) if (total_bid + total_ask) > 0 else 0
    
    return {'type': 'orderbook', 'asks': asks, 'bids': bids, 'total_ask': total_ask, 'total_bid': total_bid, 'ratio': ratio}

# ========== 图片分段裁切 ==========
def split_image(img):
    """
    超长图片自动分段，返回 [(crop_obj, y_offset), ...]
    非长图返回单段
    """
    w, h = img.size
    data_h = h - HEADER_SKIP
    
    if data_h <= MAX_HEIGHT:
        # 不需要分段
        crop = img.crop((0, HEADER_SKIP, w, h))
        return [(crop, 0, 0)]
    
    # 需要分段
    segments = []
    y = HEADER_SKIP
    seg_id = 0
    while y < h:
        y_end = min(y + MAX_HEIGHT, h)
        crop = img.crop((0, y, w, y_end))
        segments.append((crop, y, seg_id))
        seg_id += 1
        # 下一段从当前结束位置减去重叠区开始
        y = y_end - OVERLAP
        if y_end >= h:
            break
    
    return segments

# ========== Tesseract 引擎 ==========
def run_tesseract(img_path):
    """用Tesseract识别，速度快（3-5秒/段）"""
    img = Image.open(img_path).convert('L')
    w, h = img.size
    
    # 自动分段
    segments = split_image(img)
    all_trades = []
    seen_keys = set()  # 去重用
    
    for crop, y_offset, seg_id in segments:
        # 增强对比度 + 二值化
        enhancer = ImageEnhance.Contrast(crop)
        crop = enhancer.enhance(2.0)
        bw = crop.point(lambda x: 255 if x > 128 else 0, '1')
        
        tmp = f"/tmp/l2_tess_seg{seg_id}.jpg"
        bw.save(tmp)
        
        result = subprocess.run(
            ['tesseract', tmp, '-', '-l', 'chi_sim+eng', '--psm', '6'],
            capture_output=True, text=True
        )
        
        # 清理临时文件
        if os.path.exists(tmp):
            os.remove(tmp)
        
        lines = result.stdout.strip().split('\n')
        
        for line in lines:
            time_match = re.search(r'(\d{2})[:.](\d{2})[:.](\d{2})', line)
            if not time_match:
                continue
            
            t = f"{time_match.group(1)}:{time_match.group(2)}:{time_match.group(3)}"
            
            # 方向判断
            if '买' in line or 'Su' in line or 'B' in line.split()[1:2]:
                direction = 'Buy'
            elif '卖' in line or 'Ss' in line or 'S' in line.split()[1:2]:
                direction = 'Sell'
            else:
                direction = '?'
            
            line_no_time = line[time_match.end():]
            
            # 提取价格
            prices2 = re.findall(r'\d{1,3}\.\d{2}', line_no_time)
            price = None
            for p in prices2:
                try:
                    val = float(p)
                    if 0.01 < val < 10000:
                        price = val
                        break
                except:
                    pass
            
            # 提取手数
            vol = None
            if price:
                price_pos = line_no_time.find(str(price))
                if price_pos >= 0:
                    after_price = line_no_time[price_pos + len(str(price)):]
                    nums_in_after = re.findall(r'\d+', after_price)
                    for n in nums_in_after:
                        val = int(n)
                        if 1 <= val < 1000000:
                            vol = val
                            break
            
            if vol is None:
                all_nums = re.findall(r'\d+\.?\d*', line_no_time)
                for n in all_nums:
                    try:
                        val = float(n)
                        if val == price:
                            continue
                        if 1 <= val < 1000000:
                            vol = int(val)
                            break
                    except:
                        pass
            
            if price and vol:
                # 去重：用(时间,价格,手数)做key
                key = (t, price, vol)
                if key not in seen_keys:
                    seen_keys.add(key)
                    all_trades.append({"t": t, "p": price, "v": vol, "a": direction})
    
    return all_trades

# ========== EasyOCR 引擎 ==========
def run_easyocr(img_path):
    """用EasyOCR识别，精度高（60-120秒）"""
    import easyocr
    
    reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)
    img = Image.open(img_path).convert('L')
    w, h = img.size
    lanes = scale_lanes(w)
    
    # 自动分段：先裁切再处理
    segments = split_image(img)
    all_raw = []
    
    for crop, y_offset, seg_id in segments:
        seg_h = crop.size[1]
        slice_h = 1000
        
        for y in range(0, seg_h, slice_h):
            h_limit = min(y + slice_h, seg_h)
            for label, (x_start, x_end) in lanes.items():
                chunk = ImageOps.autocontrast(crop.crop((x_start, y, x_end, h_limit)), cutoff=1)
                tmp = f"/tmp/lane_{label}_{seg_id}_{y}.jpg"
                chunk.save(tmp)
                res = reader.readtext(tmp)
                for r in res:
                    all_raw.append({
                        'y': (r[0][0][1] + r[0][2][1]) / 2 + y + y_offset,
                        'text': r[1],
                        'type': label
                    })
                if os.path.exists(tmp):
                    os.remove(tmp)
    
    # 按Y坐标归行
    rows = {}
    for p in all_raw:
        line_id = round(p['y'] / 18.2)
        if line_id not in rows:
            rows[line_id] = {}
        rows[line_id][p['type']] = p['text']
    
    trades = []
    for l_id in sorted(rows.keys()):
        row = rows[l_id]
        time_raw = row.get("time", "")
        price_raw = row.get("price", "")
        vol_raw = row.get("vol", "0")
        side_raw = row.get("side", "")
        
        # 时间清洗
        t = "".join(re.findall(r'\d', time_raw.replace('O', '0')))
        if len(t) < 4:
            continue
        t_fmt = f"{t[:2]}:{t[2:4]}:{t[4:6] if len(t) >= 6 else '00'}"
        
        # 价格清洗
        p_str = "".join(re.findall(r'[\d\.]', price_raw.replace(',', '.')))
        if not p_str:
            continue
        price = float(p_str)
        
        # 手数清洗
        v = int("".join(re.findall(r'\d', vol_raw.replace('O', '0'))) or 0)
        if v == 0:
            continue
        
        # 方向映射
        direction = "Buy" if any(x in side_raw for x in ["买", "B"]) else "Sell"
        
        trades.append({"t": t_fmt, "p": price, "v": v, "a": direction})
    
    return trades

# ========== 方向修正（后处理） ==========
def fix_direction(trades):
    """根据价格关系修正方向：如果价格明显低于均价，可能是卖单砸盘"""
    # 简单规则：保留原始方向，不做猜测
    # EasyOCR/Tesseract已经能识别买/卖字段
    for t in trades:
        if t["a"] == "?":
            t["a"] = "-"  # 未知方向
    return trades

# ========== 主函数 ==========
def main():
    if len(sys.argv) < 2:
        print("用法: python3 ocr_logic.py <图片路径> [--accuracy|--orderbook]")
        print("  默认: 自动检测类型（逐笔成交/千档盘口）")
        print("  --accuracy: EasyOCR高精度模式（逐笔成交）")
        print("  --orderbook: 强制按千档盘口解析")
        print(f"  超长截图自动分段（每段{MAX_HEIGHT}px）", file=sys.stderr)
        sys.exit(1)
    
    img_path = sys.argv[1]
    use_easyocr = "--accuracy" in sys.argv
    force_orderbook = "--orderbook" in sys.argv
    
    if not os.path.exists(img_path):
        print(f"❌ 文件不存在: {img_path}")
        sys.exit(1)
    
    img = Image.open(img_path)
    w, h = img.size
    
    # 自动检测类型
    img_type = "orderbook" if force_orderbook else detect_type(img_path)
    
    if img_type == "orderbook":
        print(f"📊 图片: {w}x{h} → 千档盘口模式", file=sys.stderr)
        result = parse_orderbook(img_path)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        # 统计
        print(f"\n📊 千档盘口识别完成:", file=sys.stderr)
        print(f"   卖盘: {len(result['asks'])}档, 总量: {result['total_ask']:,}手", file=sys.stderr)
        print(f"   买盘: {len(result['bids'])}档, 总量: {result['total_bid']:,}手", file=sys.stderr)
        print(f"   委比: {result['ratio']}%", file=sys.stderr)
        if result['asks']:
            print(f"   卖1: {result['asks'][0]['price']:.2f} ({result['asks'][0]['vol']}手)", file=sys.stderr)
        if result['bids']:
            print(f"   买1: {result['bids'][0]['price']:.2f} ({result['bids'][0]['vol']}手)", file=sys.stderr)
    else:
        # 逐笔成交模式
        data_h = h - HEADER_SKIP
        if data_h > MAX_HEIGHT:
            seg_count = (data_h + MAX_HEIGHT - OVERLAP) // MAX_HEIGHT
            print(f"📷 图片: {w}x{h} → 逐笔成交（超长，自动分{seg_count}段）", file=sys.stderr)
        else:
            print(f"📷 图片: {w}x{h} → 逐笔成交模式", file=sys.stderr)
        
        if use_easyocr:
            print("🔬 引擎: EasyOCR（高精度模式）", file=sys.stderr)
            try:
                trades = run_easyocr(img_path)
            except Exception as e:
                print(f"⚠️ EasyOCR失败，切换Tesseract: {e}", file=sys.stderr)
                trades = run_tesseract(img_path)
        else:
            print("⚡ 引擎: Tesseract（快速模式）", file=sys.stderr)
            trades = run_tesseract(img_path)
        
        trades = fix_direction(trades)
        print(json.dumps(trades, indent=2, ensure_ascii=False))
        
        print(f"\n📊 识别结果: {len(trades)}笔", file=sys.stderr)
        if trades:
            buys = [t for t in trades if t["a"] == "Buy"]
            sells = [t for t in trades if t["a"] == "Sell"]
            print(f"   买单: {len(buys)}笔, 卖单: {len(sells)}笔", file=sys.stderr)
            print(f"   价格区间: {min(t['p'] for t in trades):.2f} - {max(t['p'] for t in trades):.2f}", file=sys.stderr)
            print(f"   时间范围: {trades[-1]['t']} - {trades[0]['t']}", file=sys.stderr)

if __name__ == "__main__":
    main()
