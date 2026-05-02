#!/usr/bin/env python3
"""
委托挂单表格 OCR v3 — 自适应价格范围
6列×19行网格，上下各6列
第1列第1行 = 实时成交价

用法: python3 ocr_table.py <图片路径> [--debug]
"""

import os, sys, re, json, subprocess
from PIL import Image, ImageEnhance, ImageFilter

MID_Y = 370
ASK_TOP = 60
BID_BOTTOM = 650
COLS = 6
ROWS_PER_COL = 19


def preprocess(img, x1, y1, x2, y2, scale=2, thresh=130):
    region = img.crop((x1, y1, x2, y2))
    w, h = region.size
    region = region.resize((w * scale, h * scale), Image.LANCZOS)
    region = ImageEnhance.Contrast(region).enhance(2.5)
    region = region.filter(ImageFilter.SHARPEN)
    region = region.point(lambda x: 255 if x > thresh else 0, '1')
    return region


def ocr(img, psm=6):
    tmp = "/tmp/_ocr_tmp.jpg"
    img.save(tmp)
    r = subprocess.run(
        ['tesseract', tmp, '-', '-l', 'chi_sim+eng', '--psm', str(psm), '--oem', '1'],
        capture_output=True, text=True
    )
    os.remove(tmp)
    return r.stdout


def parse_column(raw_text, price_min=None, price_max=None):
    """解析一列OCR文本，自适应价格范围"""
    entries = []
    lines = raw_text.strip().split('\n')

    for line in lines:
        line = line.strip()
        if not line or len(line) < 5:
            continue

        fixed = line
        fixed = fixed.replace('«', '').replace('»', '').replace('=', ' ')
        fixed = fixed.replace('#', ' ').replace('*', ' ').replace('+', ' ')
        fixed = fixed.replace('o', '0').replace('O', '0')
        fixed = fixed.replace('l', '1').replace('I', '1')
        fixed = re.sub(r'[^\d.\s]', ' ', fixed)

        tokens = re.findall(r'\d+\.?\d*|\d+', fixed)
        if len(tokens) < 2:
            continue

        prices = []
        for i, t in enumerate(tokens):
            try:
                v = float(t)
                if '.' in t and (price_min is None or v > price_min) and (price_max is None or v < price_max):
                    prices.append((i, v))
            except:
                pass

        if not prices:
            continue

        idx, price = prices[0]

        remaining = []
        for i2, t in enumerate(tokens):
            if i2 == idx:
                continue
            try:
                v = float(t)
                if '.' not in t and 0 < v < 1000000:
                    remaining.append(int(v))
            except:
                pass

        if len(remaining) >= 2:
            entries.append({
                'price': price,
                'vol': max(remaining),
                'orders': min(remaining)
            })
        elif len(remaining) == 1:
            entries.append({
                'price': price,
                'vol': remaining[0],
                'orders': 0
            })

    seen = set()
    unique = []
    for e in entries:
        if e['price'] not in seen:
            seen.add(e['price'])
            unique.append(e)
    return unique


def detect_and_parse(img_path, debug=False):
    img = Image.open(img_path).convert('L')
    w, h = img.size

    if w / h < 1.3 or h > 1000:
        return None

    if debug:
        print(f"📐 网格格式: {w}x{h} (6×19)", file=sys.stderr)

    col_width = w // COLS

    # 自适应价格范围：先做一次全图OCR探测
    full_region = preprocess(img, 0, ASK_TOP, w, BID_BOTTOM)
    full_raw = ocr(full_region, psm=6)
    all_prices = []
    for token in re.findall(r'\d{2,3}\.\d{1,2}', full_raw):
        try:
            v = float(token)
            if 5.0 < v < 500.0:
                all_prices.append(v)
        except:
            pass

    if all_prices:
        price_center = sorted(all_prices)[len(all_prices)//2]
        price_min = price_center * 0.85
        price_max = price_center * 1.15
        if debug:
            print(f"📊 自动价格范围: {price_min:.2f} - {price_max:.2f} (中心: {price_center:.2f})", file=sys.stderr)
    else:
        price_min, price_max = 10.0, 200.0

    all_asks = []
    all_bids = []

    for col in range(COLS):
        x1 = col * col_width
        x2 = (col + 1) * col_width
        region = preprocess(img, x1, ASK_TOP, x2, MID_Y)
        raw = ocr(region, psm=6)
        if debug:
            print(f"\n=== Ask col{col+1} ===", file=sys.stderr)
            print(raw[:500], file=sys.stderr)
        entries = parse_column(raw, price_min, price_max)
        all_asks.extend(entries)

    for col in range(COLS):
        x1 = col * col_width
        x2 = (col + 1) * col_width
        region = preprocess(img, x1, MID_Y, x2, BID_BOTTOM)
        raw = ocr(region, psm=6)
        if debug:
            print(f"\n=== Bid col{col+1} ===", file=sys.stderr)
            print(raw[:500], file=sys.stderr)
        entries = parse_column(raw, price_min, price_max)
        all_bids.extend(entries)

    seen = set()
    unique_asks = []
    for a in all_asks:
        if a['price'] not in seen:
            seen.add(a['price'])
            unique_asks.append(a)

    seen = set()
    unique_bids = []
    for b in all_bids:
        if b['price'] not in seen:
            seen.add(b['price'])
            unique_bids.append(b)

    unique_asks.sort(key=lambda x: x['price'])
    unique_bids.sort(key=lambda x: -x['price'])

    for i, a in enumerate(unique_asks):
        a['idx'] = i + 1
        a['side'] = 'Ask'
    for i, b in enumerate(unique_bids):
        b['idx'] = i + 1
        b['side'] = 'Bid'

    total_ask = sum(a['vol'] for a in unique_asks)
    total_bid = sum(b['vol'] for b in unique_bids)
    ratio = round((total_bid - total_ask) / (total_bid + total_ask) * 100, 2) if (total_bid + total_ask) > 0 else 0

    return {
        'type': 'orderbook_grid',
        'asks': unique_asks,
        'bids': unique_bids,
        'total_ask': total_ask,
        'total_bid': total_bid,
        'ratio': ratio
    }


def main():
    if len(sys.argv) < 2:
        print("用法: python3 ocr_table.py <图片路径> [--debug]")
        sys.exit(1)

    img_path = sys.argv[1]
    debug = "--debug" in sys.argv

    if not os.path.exists(img_path):
        print(f"❌ 文件不存在: {img_path}")
        sys.exit(1)

    result = detect_and_parse(img_path, debug)
    if result is None:
        print("⚠️ 不是网格格式，请用 ocr_logic.py", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(result, indent=2, ensure_ascii=False))

    print(f"\n📊 委托挂单网格识别完成:", file=sys.stderr)
    print(f"   卖盘: {len(result['asks'])}档, 总量: {result['total_ask']:,}手", file=sys.stderr)
    print(f"   买盘: {len(result['bids'])}档, 总量: {result['total_bid']:,}手", file=sys.stderr)
    print(f"   委比: {result['ratio']}%", file=sys.stderr)
    if result['asks']:
        print(f"   卖1: {result['asks'][0]['price']:.2f} ({result['asks'][0]['vol']}手)", file=sys.stderr)
    if result['bids']:
        print(f"   买1: {result['bids'][0]['price']:.2f} ({result['bids'][0]['vol']}手)", file=sys.stderr)


if __name__ == "__main__":
    main()
