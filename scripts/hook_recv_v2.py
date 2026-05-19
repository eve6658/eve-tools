#!/usr/bin/env python3
"""
hook_recv_v2.py - 修复版：完整保存 recv/WSARecv 原始数据
关键修复：Frida send() 的第二个参数传二进制数据
"""
import frida, sys, os, time, argparse, struct, zlib
from datetime import datetime

HOOK_SCRIPT = """
'use strict';

var packetCount = 0;
var totalBytes = 0;

var ws2 = null;
var mods = Process.enumerateModules();
for (var i = 0; i < mods.length; i++) {
    if (mods[i].name.toLowerCase() === 'ws2_32.dll') {
        ws2 = mods[i];
        break;
    }
}

if (!ws2) {
    send({type: 'error', msg: 'ws2_32.dll not found'});
} else {
    var exports = ws2.enumerateExports();
    var recvAddr = null;
    var wsaRecvAddr = null;
    
    for (var j = 0; j < exports.length; j++) {
        if (exports[j].name === 'recv') recvAddr = exports[j].address;
        if (exports[j].name === 'WSARecv') wsaRecvAddr = exports[j].address;
    }
    
    if (recvAddr) {
        Interceptor.attach(recvAddr, {
            onEnter: function(args) {
                this.buf = args[1];
            },
            onLeave: function(retval) {
                var n = retval.toInt32();
                if (n <= 0) return;
                packetCount++;
                totalBytes += n;
                
                // 发送完整二进制数据 (Frida send 的第二个参数)
                try {
                    var fullData = this.buf.readByteArray(Math.min(n, 65536));
                    send({
                        type: 'packet',
                        func: 'recv',
                        length: n,
                        total: packetCount,
                        totalBytes: totalBytes
                    }, fullData);
                } catch(e) {}
            }
        });
    }
    
    if (wsaRecvAddr) {
        Interceptor.attach(wsaRecvAddr, {
            onEnter: function(args) {
                this.lpBuffers = args[1];
                this.lpNumberOfBytesRecvd = args[5];
            },
            onLeave: function(retval) {
                var n = 0;
                try { n = Memory.readU32(this.lpNumberOfBytesRecvd); } catch(e) {}
                if (n <= 0) return;
                packetCount++;
                totalBytes += n;
                
                // WSARecv: 读取 WSABUF 数组
                try {
                    // WSABUF: { ULONG len; CHAR* buf; }
                    var bufCount = 1; // 通常只有一个 buffer
                    try { bufCount = Memory.readU32(args[4]); } catch(e) {}
                    
                    var allData = [];
                    var totalRead = 0;
                    for (var i = 0; i < bufCount && totalRead < n; i++) {
                        var bufLen = Memory.readU32(this.lpBuffers.add(i * 16));
                        var bufPtr = Memory.readPointer(this.lpBuffers.add(i * 16 + 8));
                        var readLen = Math.min(bufLen, n - totalRead, 65536 - totalRead);
                        var chunk = bufPtr.readByteArray(readLen);
                        allData.push(new Uint8Array(chunk));
                        totalRead += readLen;
                    }
                    
                    // 合并所有 buffer
                    var merged = new Uint8Array(totalRead);
                    var offset = 0;
                    for (var i = 0; i < allData.length; i++) {
                        merged.set(allData[i], offset);
                        offset += allData[i].length;
                    }
                    
                    send({
                        type: 'packet',
                        func: 'WSARecv',
                        length: n,
                        total: packetCount,
                        totalBytes: totalBytes
                    }, merged.buffer);
                } catch(e) {}
            }
        });
    }
    
    send({
        type: 'ready',
        message: 'Hooks installed: recv=' + (recvAddr ? 'OK' : 'MISSING') +
                 ', WSARecv=' + (wsaRecvAddr ? 'OK' : 'MISSING')
    });
}
"""

class RecvHookV2:
    def __init__(self, save_dir="raw_packets", decode=True):
        self.save_dir = save_dir
        self.decode = decode
        self.session = None
        self.packet_file = None
        self.start_time = None
        self.last_stats_time = None
        self.packet_count = 0
        self.zlib_count = 0
        
        os.makedirs(save_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fn = os.path.join(save_dir, f"packets_{ts}.bin")
        self.packet_file = open(fn, "wb")
        print(f"[SAVE] 原始数据包保存到: {fn}", flush=True)

    def on_message(self, message, data):
        if message["type"] == "send":
            msg = message["payload"]
            if msg["type"] == "ready":
                print(f"[HOOK] {msg['message']}", flush=True)
                return
            if msg["type"] == "error":
                print(f"[ERROR] {msg['msg']}", flush=True)
                return
            if msg["type"] == "packet":
                self._handle_packet(msg, data)
        elif message["type"] == "error":
            print(f"[ERROR] {message.get('description', message)}", flush=True)

    def _try_decompress(self, data):
        if len(data) >= 2 and data[0] == 0x78:
            try: return zlib.decompress(data)
            except: pass
        for i in range(min(len(data), 16)):
            if data[i] == 0x78:
                try: return zlib.decompress(data[i:])
                except: pass
        return None

    def _find_strings(self, data):
        strings, cur = [], b''
        for b in data:
            if 32 <= b < 127:
                cur += bytes([b])
            else:
                if len(cur) >= 3:
                    strings.append(cur.decode('ascii', 'replace'))
                cur = b''
        if len(cur) >= 3:
            strings.append(cur.decode('ascii', 'replace'))
        return strings

    def _handle_packet(self, msg, raw_data):
        now = time.time()
        elapsed = now - self.start_time
        self.packet_count = msg['total']
        
        # 保存原始数据
        if raw_data and self.packet_file:
            self.packet_file.write(struct.pack("<I", msg["length"]))
            self.packet_file.write(raw_data)
            self.packet_file.flush()
        
        # 解码分析
        if raw_data and self.decode:
            ts = datetime.now().strftime("%H:%M:%S.%f")[:12]
            print(f'\n{"="*60}', flush=True)
            print(f'#{msg["total"]:5d} {ts} {msg["func"]:8s} len={msg["length"]:6d}', flush=True)
            
            # 尝试按帧解析 (FD FD FD FD + 8hex len + payload)
            payload = raw_data
            frames = []
            i = 0
            while i < len(payload):
                if i + 4 <= len(payload) and payload[i:i+4] == b'\xfd\xfd\xfd\xfd' and i + 12 <= len(payload):
                    try:
                        pl = int(payload[i+4:i+12].decode('ascii'), 16)
                        frames.append(payload[i+12:12+pl])
                        i = 12 + pl
                        continue
                    except:
                        pass
                i += 1
            
            if not frames:
                frames = [payload]
            
            for fi, frame in enumerate(frames):
                dec = self._try_decompress(frame)
                if dec:
                    self.zlib_count += 1
                    strs = self._find_strings(dec)
                    print(f'  [ZLIB #{self.zlib_count}] {len(frame)} -> {len(dec)} bytes', flush=True)
                    
                    # Hex dump
                    for j in range(0, min(192, len(dec)), 16):
                        c = dec[j:j+16]
                        h = ' '.join(f'{b:02x}' for b in c)
                        a = ''.join(chr(b) if 32 <= b < 127 else '.' for b in c)
                        print(f'    {j:04x}: {h:<48s} {a}', flush=True)
                    if len(dec) > 192:
                        print(f'    ... ({len(dec) - 192} more bytes)', flush=True)
                    
                    if strs:
                        print(f'  STRINGS({len(strs)}): {strs[:25]}', flush=True)
                else:
                    # 非压缩帧
                    if len(frame) <= 64:
                        h = ' '.join(f'{b:02x}' for b in frame[:32])
                        print(f'  FRAME[{fi}] {len(frame)}: {h}', flush=True)
                    else:
                        h = ' '.join(f'{b:02x}' for b in frame[:32])
                        print(f'  FRAME[{fi}] {len(frame)}: {h} ...', flush=True)
            
            sys.stdout.flush()
        
        # 统计
        if self.last_stats_time is None or now - self.last_stats_time >= 10:
            rate = msg['total'] / elapsed if elapsed > 0 else 0
            print(f'\n  [STATS] {msg["total"]} pkts, {msg["totalBytes"]:,} bytes, '
                  f'{rate:.1f} pkt/s, ZLIB: {self.zlib_count}', flush=True)
            self.last_stats_time = now

    def find_ax_process(self):
        try:
            device = frida.get_local_device()
            for proc in device.enumerate_processes():
                if proc.name == "AX.exe":
                    return proc.pid
        except:
            pass
        return None

    def attach(self, pid=None):
        if pid is None:
            pid = self.find_ax_process()
            if pid is None:
                print("[ERROR] AX.exe not found", flush=True)
                return False
        try:
            self.session = frida.attach(pid)
            print(f"[ATTACH] PID={pid}", flush=True)
            script = self.session.create_script(HOOK_SCRIPT)
            script.on("message", self.on_message)
            script.load()
            return True
        except Exception as e:
            print(f"[ERROR] {e}", flush=True)
            return False

    def run(self):
        self.start_time = time.time()
        print(f"\n{'='*60}", flush=True)
        print(f"  recv/WSARecv Hook V2 (完整数据捕获)", flush=True)
        print(f"  Ctrl+C 停止", flush=True)
        print(f"{'='*60}\n", flush=True)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n[STOP] Total: {self.packet_count} pkts, ZLIB: {self.zlib_count}", flush=True)
        finally:
            if self.session:
                try: self.session.detach()
                except: pass
            if self.packet_file:
                self.packet_file.close()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pid", type=int)
    parser.add_argument("--dir", default="raw_packets")
    parser.add_argument("--no-decode", action="store_true")
    args = parser.parse_args()
    
    hook = RecvHookV2(save_dir=args.dir, decode=not args.no_decode)
    if not hook.attach(args.pid):
        sys.exit(1)
    hook.run()

if __name__ == "__main__":
    main()
