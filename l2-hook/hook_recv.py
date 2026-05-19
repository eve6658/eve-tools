#!/usr/bin/env python3
"""
hook_recv.py - Frida hook AX.exe recv/WSARecv
目标：稳定导出 recv 原始数据流

用法：
  python hook_recv.py                    # 自动找 AX.exe
  python hook_recv.py --pid 1234         # 指定 PID
  python hook_recv.py --save             # 保存原始数据包到 raw_packets/
  python hook_recv.py --no-print         # 不打印到终端（仅保存）

依赖：pip install frida-tools frida
"""

import frida
import sys
import os
import time
import argparse
import struct
from datetime import datetime

# ============================================================
#  Frida JS hook 脚本 (Frida 17.x 兼容)
# ============================================================

HOOK_SCRIPT = """
'use strict';

var packetCount = 0;
var totalBytes = 0;

// 找 ws2_32.dll
var mods = Process.enumerateModules();
var ws2 = null;
for (var i = 0; i < mods.length; i++) {
    if (mods[i].name.toLowerCase() === 'ws2_32.dll') {
        ws2 = mods[i];
        break;
    }
}

if (!ws2) {
    send({type: 'error', msg: 'ws2_32.dll not found'});
} else {
    // 枚举 exports 找 recv 和 WSARecv
    var exports = ws2.enumerateExports();
    var recvAddr = null;
    var wsaRecvAddr = null;
    
    for (var j = 0; j < exports.length; j++) {
        if (exports[j].name === 'recv') recvAddr = exports[j].address;
        if (exports[j].name === 'WSARecv') wsaRecvAddr = exports[j].address;
    }
    
    // hook recv
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
                var previewLen = Math.min(n, 32);
                var bytes = [];
                for (var i = 0; i < previewLen; i++) {
                    bytes.push(('0' + this.buf.add(i).readU8().toString(16)).slice(-2));
                }
                send({
                    type: 'packet',
                    func: 'recv',
                    length: n,
                    total: packetCount,
                    totalBytes: totalBytes,
                    hex: bytes.join(' ')
                });
            }
        });
    }
    
    // hook WSARecv
    if (wsaRecvAddr) {
        Interceptor.attach(wsaRecvAddr, {
            onEnter: function(args) {
                this.lpBuffers = args[1];
            },
            onLeave: function(retval) {
                var n = 0;
                try { n = Memory.readU32(args[5]); } catch(e) {}
                if (n <= 0) return;
                packetCount++;
                totalBytes += n;
                var firstBuf = Memory.readPointer(this.lpBuffers.add(4));
                var previewLen = Math.min(n, 32);
                var bytes = [];
                for (var i = 0; i < previewLen; i++) {
                    bytes.push(('0' + firstBuf.add(i).readU8().toString(16)).slice(-2));
                }
                send({
                    type: 'packet',
                    func: 'WSARecv',
                    length: n,
                    total: packetCount,
                    totalBytes: totalBytes,
                    hex: bytes.join(' ')
                });
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


# ============================================================
#  主程序
# ============================================================

class RecvHook:
    def __init__(self, save_dir="raw_packets", save_raw=False, print_packets=True):
        self.save_dir = save_dir
        self.save_raw = save_raw
        self.print_packets = print_packets
        self.session = None
        self.packet_file = None
        self.start_time = None
        self.last_stats_time = None

        if save_raw:
            os.makedirs(save_dir, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            fn = os.path.join(save_dir, f"packets_{ts}.bin")
            self.packet_file = open(fn, "wb")
            print(f"[SAVE] 原始数据包保存到: {fn}", flush=True)

    def on_message(self, message, data):
        """Frida 消息回调"""
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

    def _handle_packet(self, msg, raw_data=None):
        """处理数据包消息"""
        now = time.time()
        elapsed = now - self.start_time

        if self.print_packets:
            ts = datetime.now().strftime("%H:%M:%S.%f")[:12]
            print(f"  {ts} #{msg['total']:5d} {msg['func']:8s} "
                  f"len={msg['length']:6d}  hex={msg['hex']}", flush=True)

        # 保存原始数据
        if self.save_raw and raw_data:
            self.packet_file.write(struct.pack("<I", msg["length"]))
            self.packet_file.write(raw_data)
            self.packet_file.flush()

        # 每 10 秒打印统计
        if self.last_stats_time is None or now - self.last_stats_time >= 10:
            rate = msg["total"] / elapsed if elapsed > 0 else 0
            bytes_rate = msg["totalBytes"] / elapsed if elapsed > 0 else 0
            print(f"  [STATS] {msg['total']} packets, "
                  f"{msg['totalBytes']:,} bytes, "
                  f"{rate:.1f} pkt/s, "
                  f"{bytes_rate/1024:.1f} KB/s, "
                  f"elapsed {elapsed:.0f}s", flush=True)
            self.last_stats_time = now

    def find_ax_process(self):
        """查找 AX.exe 进程"""
        try:
            device = frida.get_local_device()
            processes = device.enumerate_processes()
            for proc in processes:
                if proc.name == "AX.exe":
                    print(f"[FIND] AX.exe PID={proc.pid}", flush=True)
                    return proc.pid
        except Exception as e:
            print(f"[ERROR] 枚举进程失败: {e}", flush=True)
        return None

    def attach(self, pid=None):
        """附加到 AX.exe"""
        if pid is None:
            pid = self.find_ax_process()
            if pid is None:
                print("[ERROR] 未找到 AX.exe，请先启动客户端", flush=True)
                return False

        try:
            self.session = frida.attach(pid)
            print(f"[ATTACH] 已附加到 PID={pid}", flush=True)
        except frida.ProcessNotFoundError:
            print(f"[ERROR] 进程 {pid} 不存在", flush=True)
            return False
        except frida.PermissionDeniedError:
            print(f"[ERROR] 权限不足，请以管理员身份运行", flush=True)
            return False
        except Exception as e:
            print(f"[ERROR] 附加失败: {e}", flush=True)
            return False

        try:
            script = self.session.create_script(HOOK_SCRIPT)
            script.on("message", self.on_message)
            script.load()
            print("[SCRIPT] Hook 脚本已加载", flush=True)
            return True
        except Exception as e:
            print(f"[ERROR] 脚本加载失败: {e}", flush=True)
            return False

    def run(self):
        """运行直到 Ctrl+C"""
        self.start_time = time.time()
        self.last_stats_time = None
        print(f"\n{'='*60}", flush=True)
        print(f"  recv/WSARecv Hook 已启动", flush=True)
        print(f"  Ctrl+C 停止", flush=True)
        print(f"{'='*60}\n", flush=True)

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n\n[STOP] 正在停止...", flush=True)
        finally:
            self.cleanup()

    def cleanup(self):
        """清理资源"""
        if self.session:
            try:
                self.session.detach()
            except:
                pass
        if self.packet_file:
            self.packet_file.close()
            print(f"[SAVE] 数据包文件已关闭", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Frida hook AX.exe recv/WSARecv")
    parser.add_argument("--pid", type=int, help="指定 AX.exe PID")
    parser.add_argument("--save", action="store_true", help="保存原始数据包到 raw_packets/")
    parser.add_argument("--no-print", action="store_true", help="不打印到终端")
    parser.add_argument("--dir", default="raw_packets", help="数据包保存目录")
    args = parser.parse_args()

    hook = RecvHook(
        save_dir=args.dir,
        save_raw=args.save,
        print_packets=not args.no_print
    )

    if not hook.attach(args.pid):
        sys.exit(1)

    hook.run()


if __name__ == "__main__":
    main()
