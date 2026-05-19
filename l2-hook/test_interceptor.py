import frida
import sys
import time

print("START", flush=True)

session = frida.attach(6068)
print("ATTACHED", flush=True)

# Test: Find recv using different API approaches
script = session.create_script("""
'use strict';
// Try different ways to find recv
var results = {};

// Method 1: Process.findModuleByName
try {
    var mod = Process.findModuleByName('ws2_32.dll');
    results.m1 = mod ? mod.base.toString() : 'null';
} catch(e) { results.m1 = 'err:' + e.message; }

// Method 2: Module.load
try {
    var m2 = Module.load('ws2_32.dll');
    results.m2 = typeof m2;
} catch(e) { results.m2 = 'err:' + e.message; }

// Method 3: Check Module properties
try {
    results.m3 = Object.keys(Module).join(',');
} catch(e) { results.m3 = 'err:' + e.message; }

// Method 4: Process.enumerateExports
try {
    var mods = Process.enumerateModules();
    results.m4_count = mods.length;
    for (var i = 0; i < mods.length; i++) {
        if (mods[i].name === 'ws2_32.dll') {
            var exports = mods[i].enumerateExports();
            for (var j = 0; j < exports.length; j++) {
                if (exports[j].name === 'recv') {
                    results.m4_recv = exports[j].address.toString();
                    break;
                }
            }
            break;
        }
    }
} catch(e) { results.m4 = 'err:' + e.message; }

send(results);
""")

def on_message(msg, data):
    open("C:/l2-hook/test_result.txt", "a").write("API:" + str(msg) + "\n")

script.on("message", on_message)
script.load()
time.sleep(2)

session.detach()
print("DONE", flush=True)
