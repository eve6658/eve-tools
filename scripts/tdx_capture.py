#!/usr/bin/env python3
"""
tdx_capture.py - 通达信 L2 数据自动捕获
部署到 Windows，每天 9:15 自动运行

用法:
  python tdx_capture.py              # 捕获到 15:05
  python tdx_capture.py --hours 4    # 捕获 4 小时
  python tdx_capture.py --until 11:30  # 捕获到 11:30
"""
import frida, struct, time, sys, os, zlib, json
from datetime import datetime, timedelta

JS = """
'use strict';
var ws2 = null;
var mods = Process.enumerateModules();
for (var i = 0; i < mods.length; i++) {
    if (mods[i].name.toLowerCase() === 'ws2_32.dll') { ws2 = mods[i]; break; }
}
if (ws2) {
    var exports = ws2.enumerateExports();
    var recvAddr = null;
    var wsaRecvAddr = null;
    for (var j = 0; j < exports.length; j++) {
        if (exports[j].name === 'recv') recvAddr = exports[j].address;
        if (exports[j].name === 'WSARecv') wsaRecvAddr = exports[j].address;
    }
    
    var pktCount = 0;
    var totalBytes = 0;
    
    if (recvAddr) {
        Interceptor.attach(recvAddr, {
            onEnter: function(args) { this.buf = args[1]; },
            onLeave: function(retval) {
                var n = retval.toInt32();
                if (n <= 0) return;
                pktCount++;
                totalBytes += n;
                try {
                    send({len: n, total: pktCount, totalBytes: totalBytes},
                         this.buf.readByteArray(Math.min(n, 131072)));
                } catch(e) {}
            }
        });
    }
    
    if (wsaRecvAddr) {
        Interceptor.attach(wsaRecvAddr, {
            onEnter: function(args) {
                this.lpBuffers = args[1];
            },
            onLeave: function(retval) {
                var n = 0;
                try { n = Memory.readU32(args[5]); } catch(e) {}
                if (n <= 0) return;
                pktCount++;
                totalBytes += n;
                try {
                    var firstBuf = Memory.readPointer(this.lpBuffers.add(4));
                    send({len: n, total: pktCount, totalBytes: totalBytes},
                         firstBuf.readByteArray(Math.min(n, 131072)));
                } catch(e) {}
            }
        });
    }
    
    send({ready: true, pid: Process.id, recv: !!recvAddr, wsaRecv: !!wsaRecvAddr});
}
"""

class TDxCapture:
    def __init__(self, output_dir='tdx_data'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        ts = datetime.now().strftime('%Y%m%d')
        self.bin_file = open(os.path.join(output_dir, f'raw_{ts}.bin'), 'wb')
        self.log_file = open(os.path.join(output_dir, f'log_{ts}.txt'), 'w', encoding='utf-8')
        
        self.pkt_count = 0
        self.total_bytes = 0
        self.start_time = time.time()
        self.last_report = time.time()
        self.zlib_count = 0
        
        # 按大小分桶统计
        self.size_buckets = {}
    
    def log(self, msg):
        ts = datetime.now().strftime('%H:%M:%S')
        line = f'{ts} {msg}'
        print(line, flush=True)
        self.log_file.write(line + '\n')
        self.log_file.flush()
    
    def on_msg(self, msg, data):
        if msg['type'] == 'send':
            payload = msg['payload']
            if 'ready' in payload:
                self.log(f'Hook ready: PID={payload["pid"]}, recv={payload["recv"]}, WSARecv={payload["wsaRecv"]}')
                return
            
            length = payload.get('len', 0)
            self.pkt_count = payload.get('total', self.pkt_count + 1)
            self.total_bytes = payload.get('totalBytes', self.total_bytes + length)
            
            # 保存原始数据
            if data:
                self.bin_file.write(struct.pack('<I', length))
                self.bin_file.write(data)
                self.bin_file.flush()
            
            # 统计大小分布
            bucket = min(length // 100, 20)  # 0-100, 100-200, ...
            self.size_buckets[bucket] = self.size_buckets.get(bucket, 0) + 1
            
            # 检测 zlib
            if data and length >= 14:
                raw = bytes(data) if isinstance(data, bytes) else data
                if raw[:4] == b'\xfd\xfd\xfd\xfd' and length >= 26:
                    try:
                        pl = int(raw[4:12].decode('ascii'), 16)
                        payload_data = raw[12:12+pl]
                        for j in range(min(len(payload_data), 20)):
                            if j+1 < len(payload_data) and payload_data[j] == 0x78 and payload_data[j+1] in (0x01,0x5e,0x9c,0xda):
                                try:
                                    dec = zlib.decompress(payload_data[j:])
                                    self.zlib_count += 1
                                    # 尝试解码
                                    try:
                                        text = dec.decode('gbk')
                                        route = ''
                                        try:
                                            obj = json.loads(text)
                                            route = obj.get('route', '')
                                        except:
                                            pass
                                        self.log(f'  ZLIB#{self.zlib_count}: {len(payload_data)}->{len(dec)} route={route}')
                                    except:
                                        self.log(f'  ZLIB#{self.zlib_count}: {len(payload_data)}->{len(dec)} binary')
                                    break
                                except:
                                    pass
                elif raw[:4] == b'\xfd\xfd\xfd\xfd':
                    pass  # 非 zlib 帧
                elif b'78 9c' in raw[:20].hex():
                    pass  # 裸 zlib
            
            # 每 30 秒报告
            now = time.time()
            if now - self.last_report >= 30:
                elapsed = now - self.start_time
                rate = self.pkt_count / elapsed if elapsed > 0 else 0
                byte_rate = self.total_bytes / elapsed if elapsed > 0 else 0
                self.log(f'[STATS] {self.pkt_count} pkts, {self.total_bytes:,} bytes, '
                        f'{rate:.1f} pkt/s, {byte_rate/1024:.1f} KB/s, '
                        f'zlib: {self.zlib_count}')
                
                # 大小分布
                dist = ', '.join(f'{k*100}-{(k+1)*100}:{v}' for k, v in sorted(self.size_buckets.items()) if v > 0)
                if dist:
                    self.log(f'  Size dist: {dist}')
                
                self.last_report = now
        
        elif msg['type'] == 'error':
            self.log(f'[ERROR] {msg.get("description", "")}')
    
    def close(self):
        elapsed = time.time() - self.start_time
        self.log(f'\n=== Final: {self.pkt_count} pkts, {self.total_bytes:,} bytes, '
                f'{elapsed:.0f}s, zlib: {self.zlib_count} ===')
        self.bin_file.close()
        self.log_file.close()


def find_ax_pid():
    """查找 AX.exe PID"""
    try:
        dev = frida.get_local_device()
        for p in dev.enumerate_processes():
            if p.name == 'AX.exe':
                return p.pid
    except:
        pass
    return None


def main():
    import argparse
    parser = argparse.ArgumentParser(description='通达信 L2 数据捕获')
    parser.add_argument('--hours', type=float, help='捕获小时数')
    parser.add_argument('--until', type=str, help='捕获到 HH:MM')
    parser.add_argument('--dir', default='tdx_data', help='输出目录')
    parser.add_argument('--pid', type=int, help='指定 PID')
    args = parser.parse_args()
    
    # 计算结束时间
    if args.until:
        h, m = map(int, args.until.split(':'))
        end_time = datetime.now().replace(hour=h, minute=m, second=0)
    elif args.hours:
        end_time = datetime.now() + timedelta(hours=args.hours)
    else:
        # 默认到 15:05
        end_time = datetime.now().replace(hour=15, minute=5, second=0)
        if end_time < datetime.now():
            end_time += timedelta(days=1)
    
    pid = args.pid or find_ax_pid()
    if not pid:
        print('AX.exe not found. Please start the client first.')
        sys.exit(1)
    
    cap = TDxCapture(output_dir=args.dir)
    cap.log(f'Starting capture: PID={pid}, until={end_time.strftime("%H:%M:%S")}')
    
    dev = frida.get_local_device()
    sess = frida.attach(pid)
    s = sess.create_script(JS)
    s.on('message', cap.on_msg)
    s.load()
    
    try:
        while datetime.now() < end_time:
            time.sleep(1)
    except KeyboardInterrupt:
        cap.log('Interrupted by user')
    
    cap.close()
    sess.detach()
    cap.log('Done')


if __name__ == '__main__':
    main()
