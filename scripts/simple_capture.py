#!/usr/bin/env python3
"""最简单的 Frida raw capture - 只存文件，不打印"""
import frida, struct, time, sys

cnt = 0
f = open('C:/Users/john/raw_capture.bin', 'wb')

def on_msg(msg, data):
    global cnt
    if data:
        cnt += 1
        f.write(struct.pack('<I', len(data)))
        f.write(data)
        f.flush()

JS = """'use strict';
var ws2 = null;
var mods = Process.enumerateModules();
for (var i = 0; i < mods.length; i++) {
    if (mods[i].name.toLowerCase() === 'ws2_32.dll') { ws2 = mods[i]; break; }
}
if (ws2) {
    var exports = ws2.enumerateExports();
    var recvAddr = null;
    for (var j = 0; j < exports.length; j++) {
        if (exports[j].name === 'recv') recvAddr = exports[j].address;
    }
    if (recvAddr) {
        Interceptor.attach(recvAddr, {
            onEnter: function(args) { this.buf = args[1]; },
            onLeave: function(retval) {
                var n = retval.toInt32();
                if (n <= 0) return;
                send({len: n}, this.buf.readByteArray(Math.min(n, 65536)));
            }
        });
    }
    send({ready: true, ok: !!recvAddr});
}
"""

dev = frida.get_local_device()
for p in dev.enumerate_processes():
    if p.name == 'AX.exe':
        print(f'AX.exe PID={p.pid}')
        sess = frida.attach(p.pid)
        s = sess.create_script(JS)
        s.on('message', on_msg)
        s.load()
        print('Capturing 30s...')
        time.sleep(30)
        print(f'{cnt} packets saved')
        f.close()
        sess.detach()
        sys.exit(0)

print('AX.exe not found')
