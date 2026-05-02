#!/usr/bin/env python3
"""
盘口数据接收服务
Windows端POST盘口数据 → 本服务接收 → 分析后推送QQ

用法：python3 scripts/orderbook_receiver.py
端口：9876
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json, os, time
from datetime import datetime

PORT = 9876
DATA_DIR = '/home/adam/.openclaw/workspace/orderbook_data'
os.makedirs(DATA_DIR, exist_ok=True)

class OrderBookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        
        try:
            data = json.loads(body)
            stock = data.get('stock', 'unknown')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # 保存原始数据
            filename = f'{DATA_DIR}/{stock}_{timestamp}.json'
            with open(filename, 'w') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f'[{timestamp}] 收到 {stock} 数据 ({content_length} bytes)')
            
            # 输出关键数据供Eve分析
            self._analyze(data)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok', 'saved': filename}).encode())
            
        except Exception as e:
            print(f'错误: {e}')
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def do_GET(self):
        """查看最近的数据"""
        files = sorted(os.listdir(DATA_DIR))[-10:]
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'recent_files': files}).encode())
    
    def _analyze(self, data):
        """快速分析盘口"""
        stock = data.get('stock', '?')
        bids = data.get('bids', [])  # 买盘 [(price, volume), ...]
        asks = data.get('asks', [])  # 卖盘 [(price, volume), ...]
        
        if not bids or not asks:
            print(f'  数据不完整: bids={len(bids)}, asks={len(asks)}')
            return
        
        bid1_price = bids[0][0] if bids else 0
        ask1_price = asks[0][0] if asks else 0
        spread = ask1_price - bid1_price
        
        bid_total = sum(v for _, v in bids)
        ask_total = sum(v for _, v in asks)
        ratio = bid_total / ask_total if ask_total > 0 else 0
        
        print(f'  {stock}: 买1={bid1_price} 卖1={ask1_price} 价差={spread:.3f}')
        print(f'  买盘总量={bid_total} 卖盘总量={ask_total} 买卖比={ratio:.2f}')
        
        # 判断信号
        if ratio > 2.0:
            print(f'  ⚠️ 买盘异常偏多（可能是假托单）')
        elif ratio < 0.5:
            print(f'  ⚠️ 卖盘异常偏多（出货信号）')
        else:
            print(f'  ✅ 供需基本平衡')

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', PORT), OrderBookHandler)
    print(f'盘口数据接收服务启动，端口 {PORT}')
    print(f'数据保存目录: {DATA_DIR}')
    print(f'等待Windows端POST数据...')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n服务停止')
        server.server_close()
