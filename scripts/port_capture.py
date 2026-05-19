#!/usr/bin/env python3
"""
按端口分类捕获 AX.exe 的 recv 数据
找出哪个端口是 L2 行情
"""
import frida, struct, time, sys, os, zlib
from datetime import datetime

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
    
    var totalPkts = 0;
    var portData = {};
    
    function getPort(sock) {
        try {
            var buf = Memory.alloc(16);
            var lenPtr = Memory.alloc(4);
            lenPtr.writeU32(16);
            var getsockname = new NativeFunction(
                Module.getExportByName('ws2_32.dll', 'getsockname'),
                'int', ['int', 'pointer', 'pointer']
            );
            getsockname(sock.toInt32(), buf, lenPtr);
            return buf.add(2).readU16();
        } catch(e) { return 0; }
    }
    
    function saveData(port, data) {
        if (!portData[port]) {
            portData[port] = {count: 0, bytes: 0, files: {}};
        }
        portData[port].count++;
        portData[port].bytes += data.length;
    }
    
    if (recvAddr) {
        Interceptor.attach(recvAddr, {
            onEnter: function(args) {
                this.buf = args[1];
                this.sock = args[0];
            },
            onLeave: function(retval) {
                var n = retval.toInt32();
                if (n <= 0) return;
                totalPkts++;
                var port = getPort(this.sock);
                saveData(port, {length: n});
                
                // 发送完整数据 (通过 send message)
                if (n <= 131072) {
                    try {
                        send({port: port, len: n, total: totalPkts}, this.buf.readByteArray(n));
                    } catch(e) {}
                }
            }
        });
    }
    
    if (wsaRecvAddr) {
        Interceptor.attach(wsaRecvAddr, {
            onEnter: function(args) {
                this.sock = args[0];
                this.lpBuffers = args[1];
            },
            onLeave: function(retval) {
                var n = 0;
                try { n = Memory.readU32(args[5]); } catch(e) {}
                if (n <= 0) return;
                totalPkts++;
                var port = getPort(this.sock);
                saveData(port, {length: n});
                
                try {
                    var firstBuf = Memory.readPointer(this.lpBuffers.add(4));
                    send({port: port, len: n, total: totalPkts}, firstBuf.readByteArray(Math.min(n, 131072)));
                } catch(e) {}
            }
        });
    }
    
    send({ready: true, pid: Process.id});
}
"""

class PortCapture:
    def __init__(self):
        self.files = {}
        self.stats = {}
        self.start_time = time.time()
    
    def get_file(self, port):
        if port not in self.files:
            os.makedirs('port_caps', exist_ok=True)
            fn = f'port_caps/port_{port}.bin'
            self.files[port] = open(fn, 'wb')
            self.stats[port] = {'count': 0, 'bytes': 0}
            print(f'  [NEW] Port {port} -> {fn}')
        return self.files[port]
    
    def on_msg(self, msg, data):
        if msg['type'] == 'send':
            payload = msg['payload']
            if 'ready' in payload:
                print(f'  Hooks ready, PID={payload["pid"]}')
                return
            
            port = payload.get('port', 0)
            length = payload.get('len', 0)
            
            if data and port:
                f = self.get_file(port)
                f.write(struct.pack('<I', length))
                f.write(data)
                f.flush()
                
                self.stats[port]['count'] += 1
                self.stats[port]['bytes'] += length
        
        elif msg['type'] == 'error':
            print(f'  [ERROR] {msg.get("description", "")}')
    
    def report(self):
        elapsed = time.time() - self.start_time
        print(f'\n=== Port Stats ({elapsed:.0f}s) ===')
        for port, info in sorted(self.stats.items()):
            rate = info['count'] / elapsed if elapsed > 0 else 0
            print(f'  Port {port}: {info["count"]} pkts, {info["bytes"]:,} bytes, {rate:.1f} pkt/s')
    
    def close(self):
        for f in self.files.values():
            f.close()

def main():
    print('=== AX.exe 端口分类捕获 ===\n')
    
    cap = PortCapture()
    
    dev = frida.get_local_device()
    for p in dev.enumerate_processes():
        if p.name == 'AX.exe':
            print(f'Target: AX.exe PID={p.pid}')
            sess = frida.attach(p.pid)
            s = sess.create_script(JS)
            s.on('message', cap.on_msg)
            s.load()
            
            print('Capturing 60s (try to open L2 data window)...')
            time.sleep(60)
            
            cap.report()
            cap.close()
            sess.detach()
            return
    
    print('AX.exe not found')

if __name__ == '__main__':
    main()
