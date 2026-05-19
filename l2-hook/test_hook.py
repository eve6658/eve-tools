import frida
import sys
import time

SCRIPT = """
'use strict';
var count = 0;

// 找 ws2_32.dll 模块
var mods = Process.enumerateModules();
var ws2 = null;
for (var i = 0; i < mods.length; i++) {
    if (mods[i].name.toLowerCase() === 'ws2_32.dll') {
        ws2 = mods[i];
        break;
    }
}

if (!ws2) {
    send({type:'error', msg:'ws2_32.dll not found'});
} else {
    // 枚举 exports 找 recv
    var exports = ws2.enumerateExports();
    var recvAddr = null;
    for (var j = 0; j < exports.length; j++) {
        if (exports[j].name === 'recv') {
            recvAddr = exports[j].address;
            break;
        }
    }
    
    if (!recvAddr) {
        send({type:'error', msg:'recv not found in ws2_32.dll exports'});
    } else {
        Interceptor.attach(recvAddr, {
            onEnter: function(args) {
                this.buf = args[1];
            },
            onLeave: function(retval) {
                var n = retval.toInt32();
                if (n > 0) {
                    count++;
                    var b = this.buf.add(0).readU8();
                    send({type:'pkt', n:n, count:count, first_byte:b});
                }
            }
        });
        send({type:'ready', addr: recvAddr.toString()});
    }
}
"""

print("START", flush=True)

try:
    session = frida.attach(6068)
    print("ATTACHED", flush=True)
    
    script = session.create_script(SCRIPT)
    
    results = []
    def on_message(msg, data):
        results.append(msg)
        open("C:/l2-hook/hook_result.txt", "a").write(str(msg) + "\n")
    
    script.on("message", on_message)
    script.load()
    print("LOADED - waiting 10s for packets...", flush=True)
    
    time.sleep(10)
    session.detach()
    print("DONE", flush=True)
except Exception as e:
    print("ERROR:", e, flush=True)
