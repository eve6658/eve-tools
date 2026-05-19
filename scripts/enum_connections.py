#!/usr/bin/env python3
"""
枚举 AX.exe 所有 TCP 连接，找出 L2 行情数据通道
"""
import frida, struct, time, sys, json
from datetime import datetime

JS_ENUM = """
'use strict';

// 枚举所有已建立的 TCP 连接
var connections = [];

// 方法1: 通过 iphlpapi 获取 TCP 表
var iphlpapi = Module.load('iphlpapi.dll');
var kernel32 = Module.load('kernel32.dll');

// GetExtendedTcpTable
var GetExtendedTcpTable = iphlpapi.getExportByName('GetExtendedTcpTable');
if (!GetExtendedTcpTable) {
    send({type: 'error', msg: 'GetExtendedTcpTable not found'});
} else {
    // 先调用获取所需大小
    var tcpTable = Memory.alloc(65536);
    var sizePtr = Memory.alloc(4);
    Memory.writeU32(sizePtr, 65536);
    var orderPtr = Memory.alloc(4); // 0 = sorted by local port
    
    // MIB_TCPROW_OWNERPID structure
    // dwState, dwLocalAddr, dwLocalPort, dwRemoteAddr, dwRemotePort, dwOwningPid
    
    // AF_INET=2, TCP_TABLE_OWNER_PID_ALL=5
    var ret = new NativeFunction(GetExtendedTcpTable, 'int', ['pointer', 'pointer', 'int', 'int', 'int', 'int']);
    
    // First call to get size
    sizePtr.writeU32(65536);
    ret(tcpTable, sizePtr, 0, 2, 5, 0); // AF_INET=2
    
    var size = sizePtr.readU32();
    var buf = Memory.alloc(size);
    sizePtr.writeU32(size);
    ret(buf, sizePtr, 0, 2, 5, 0);
    
    var numEntries = buf.readU32();
    send({type: 'info', msg: 'TCP entries: ' + numEntries});
    
    var myPid = Process.id;
    var rowSize = 24; // MIB_TCPROW_OWNERPID: 6 DWORDs
    
    for (var i = 0; i < numEntries; i++) {
        var row = buf.add(4 + i * rowSize);
        var state = row.readU32();
        var localAddr = row.add(4).readU32();
        var localPort = row.add(8).readU16();
        var remoteAddr = row.add(12).readU32();
        var remotePort = row.add(16).readU16();
        var pid = row.add(20).readU32();
        
        if (pid === myPid && state === 1) { // ESTABLISHED
            var la = (localAddr & 0xff) + '.' + ((localAddr>>8)&0xff) + '.' + ((localAddr>>16)&0xff) + '.' + ((localAddr>>24)&0xff);
            var ra = (remoteAddr & 0xff) + '.' + ((remoteAddr>>8)&0xff) + '.' + ((remoteAddr>>16)&0xff) + '.' + ((remoteAddr>>24)&0xff);
            connections.push({
                local: la + ':' + localPort,
                remote: ra + ':' + remotePort,
                localPort: localPort,
                remotePort: remotePort,
                remoteAddr: ra
            });
        }
    }
    
    send({type: 'connections', data: connections});
}

// 方法2: 枚举所有 socket 对象 (Frida 16+)
try {
    var sockets = Socketenumerate();
    send({type: 'info', msg: 'Enumerated sockets: ' + sockets.length});
    for (var i = 0; i < sockets.length; i++) {
        send({type: 'socket', handle: sockets[i].handle, domain: sockets[i].domain, type: sockets[i].type});
    }
} catch(e) {
    send({type: 'info', msg: 'Socketenumerate not available: ' + e.message});
}
"""

JS_HOOK_ALL = """
'use strict';

var ws2 = null;
var mods = Process.enumerateModules();
for (var i = 0; i < mods.length; i++) {
    if (mods[i].name.toLowerCase() === 'ws2_32.dll') { ws2 = mods[i]; break; }
}

if (ws2) {
    var exports = ws2.enumerateExports();
    var recvAddr = null;
    var WSARecvAddr = null;
    var connectAddr = null;
    
    for (var j = 0; j < exports.length; j++) {
        if (exports[j].name === 'recv') recvAddr = exports[j].address;
        if (exports[j].name === 'WSARecv') WSARecvAddr = exports[j].address;
        if (exports[j].name === 'connect') connectAddr = exports[j].address;
    }
    
    var pid = Process.id;
    var pktCount = 0;
    var portStats = {};  // port -> {count, bytes, firstPkt, lastPkt}
    
    // Hook connect to track which ports are established
    if (connectAddr) {
        Interceptor.attach(connectAddr, {
            onEnter: function(args) {
                var sockaddr = args[0];
                var family = sockaddr.readU16();
                if (family === 2) { // AF_INET
                    var port = sockaddr.add(2).readU16();
                    var addr = sockaddr.add(4).readU32();
                    var addrStr = (addr&0xff) + '.' + ((addr>>8)&0xff) + '.' + ((addr>>16)&0xff) + '.' + ((addr>>24)&0xff);
                    send({type: 'connect', remote: addrStr + ':' + port, port: port});
                }
            }
        });
    }
    
    // Hook ALL recv calls - track by source port
    if (recvAddr) {
        Interceptor.attach(recvAddr, {
            onEnter: function(args) {
                this.buf = args[1];
                this.sock = args[0];
            },
            onLeave: function(retval) {
                var n = retval.toInt32();
                if (n <= 0) return;
                pktCount++;
                
                // 尝试获取 socket 的本地端口
                var localPort = 0;
                try {
                    var sockAddrBuf = Memory.alloc(16);
                    var sockLenPtr = Memory.alloc(4);
                    sockLenPtr.writeU32(16);
                    var getsockname = Module.getExportByName('ws2_32.dll', 'getsockname');
                    var fn = new NativeFunction(getsockname, 'int', ['int', 'pointer', 'pointer']);
                    fn(this.sock.toInt32(), sockAddrBuf, sockLenPtr);
                    localPort = sockAddrBuf.add(2).readU16();
                } catch(e) {}
                
                var key = 'port_' + localPort;
                if (!portStats[key]) {
                    portStats[key] = {count: 0, bytes: 0, sample: null};
                }
                portStats[key].count++;
                portStats[key].bytes += n;
                
                // 保存第一个包的前 128 字节作为样本
                if (!portStats[key].sample) {
                    try {
                        portStats[key].sample = this.buf.readByteArray(Math.min(n, 128));
                    } catch(e) {}
                }
                
                // 每 100 个包报告一次
                if (pktCount % 100 === 0) {
                    var summary = {};
                    for (var k in portStats) {
                        summary[k] = {
                            count: portStats[k].count,
                            bytes: portStats[k].bytes
                        };
                    }
                    send({type: 'stats', pktCount: pktCount, ports: summary});
                }
            }
        });
    }
    
    // Hook WSARecv
    if (WSARecvAddr) {
        Interceptor.attach(WSARecvAddr, {
            onEnter: function(args) {
                this.sock = args[0];
                this.lpBuffers = args[1];
            },
            onLeave: function(retval) {
                var n = 0;
                try { n = Memory.readU32(args[5]); } catch(e) {}
                if (n <= 0) return;
                pktCount++;
                
                var localPort = 0;
                try {
                    var sockAddrBuf = Memory.alloc(16);
                    var sockLenPtr = Memory.alloc(4);
                    sockLenPtr.writeU32(16);
                    var getsockname = Module.getExportByName('ws2_32.dll', 'getsockname');
                    var fn = new NativeFunction(getsockname, 'int', ['int', 'pointer', 'pointer']);
                    fn(this.sock.toInt32(), sockAddrBuf, sockLenPtr);
                    localPort = sockAddrBuf.add(2).readU16();
                } catch(e) {}
                
                var key = 'port_' + localPort;
                if (!portStats[key]) {
                    portStats[key] = {count: 0, bytes: 0, sample: null};
                }
                portStats[key].count++;
                portStats[key].bytes += n;
                
                if (!portStats[key].sample) {
                    try {
                        var firstBuf = Memory.readPointer(this.lpBuffers.add(4));
                        portStats[key].sample = firstBuf.readByteArray(Math.min(n, 128));
                    } catch(e) {}
                }
                
                if (pktCount % 100 === 0) {
                    var summary = {};
                    for (var k in portStats) {
                        summary[k] = {
                            count: portStats[k].count,
                            bytes: portStats[k].bytes
                        };
                    }
                    send({type: 'stats', pktCount: pktCount, ports: summary});
                }
            }
        });
    }
    
    send({
        type: 'ready',
        recv: !!recvAddr,
        WSARecv: !!WSARecvAddr,
        connect: !!connectAddr,
        pid: pid
    });
}
"""

def on_msg(msg, data):
    if msg['type'] == 'send':
        payload = msg['payload']
        t = payload.get('type', '')
        
        if t == 'info':
            print(f'  [INFO] {payload["msg"]}')
        
        elif t == 'error':
            print(f'  [ERROR] {payload["msg"]}')
        
        elif t == 'connections':
            print(f'\n=== AX.exe TCP 连接 ({len(payload["data"])} 个) ===')
            for conn in payload['data']:
                print(f'  {conn["local"]} -> {conn["remote"]}')
        
        elif t == 'socket':
            print(f'  Socket: handle={payload["handle"]} domain={payload["domain"]} type={payload["type"]}')
        
        elif t == 'connect':
            print(f'  [CONNECT] -> {payload["remote"]} (port {payload["port"]})')
        
        elif t == 'stats':
            print(f'\n--- Stats: {payload["pktCount"]} pkts ---')
            for port, info in sorted(payload['ports'].items()):
                print(f'  {port}: {info["count"]} pkts, {info["bytes"]:,} bytes')
        
        elif t == 'ready':
            print(f'  Hooks: recv={payload["recv"]}, WSARecv={payload["WSARecv"]}, connect={payload["connect"]}')
    
    elif msg['type'] == 'error':
        print(f'  [FRIDA ERROR] {msg.get("description", msg)}')

def main():
    print('=== AX.exe 连接枚举 + 全量 Hook ===\n')
    
    dev = frida.get_local_device()
    target = None
    for p in dev.enumerate_processes():
        if p.name == 'AX.exe':
            target = p
            break
    
    if not target:
        print('AX.exe not found')
        return
    
    print(f'Target: AX.exe PID={target.pid}')
    sess = frida.attach(target.pid)
    
    # Step 1: 枚举连接
    print('\n[Step 1] 枚举 TCP 连接...')
    s1 = sess.create_script(JS_ENUM)
    s1.on('message', on_msg)
    s1.load()
    time.sleep(2)
    
    # Step 2: Hook 所有 recv
    print('\n[Step 2] Hook recv + WSARecv + connect...')
    s2 = sess.create_script(JS_HOOK_ALL)
    s2.on('message', on_msg)
    s2.load()
    
    print('\n[Step 3] 监控 60 秒...')
    time.sleep(60)
    
    print('\n=== Done ===')
    sess.detach()

if __name__ == '__main__':
    main()
