#!/usr/bin/env python3
"""
实时解码 hook_recv_v2 捕获的 L2 数据包
用法: python decode_v2.py <packets_file.bin>
"""
import struct, zlib, sys, os, glob

def try_decompress(data):
    """尝试 zlib 解压"""
    for i in range(min(len(data), 32)):
        if i + 2 <= len(data) and data[i] == 0x78 and data[i+1] in (0x01, 0x5e, 0x9c, 0xda):
            try:
                return zlib.decompress(data[i:])
            except:
                pass
    return None

def find_strings(data):
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

def main():
    if len(sys.argv) < 2:
        candidates = (
            glob.glob(os.path.expanduser('~/raw_packets/packets_*.bin'))
            + glob.glob('raw_packets\\packets_*.bin')
            + glob.glob(os.path.expanduser('~\\raw_packets\\packets_*.bin'))
        )
        if not candidates:
            print('用法: python decode_v2.py <packets_file.bin>')
            return
        filepath = sorted(candidates)[-1]
    else:
        filepath = sys.argv[1]
    
    print(f'文件: {filepath}')
    with open(filepath, 'rb') as f:
        data = f.read()
    print(f'大小: {len(data)} bytes\n')
    
    # hook_recv_v2 保存格式: 4字节长度(小端) + raw_data
    # 解析
    packets = []
    i = 0
    while i + 4 <= len(data):
        pkt_len = struct.unpack('<I', data[i:i+4])[0]
        if pkt_len <= 0 or pkt_len > 65536:
            break
        if i + 4 + pkt_len > len(data):
            break
        raw = data[i+4:i+4+pkt_len]
        packets.append(raw)
        i = 4 + pkt_len
    
    print(f'解析出 {len(packets)} 个数据包\n')
    
    # 分析每个包
    zlib_count = 0
    for pi, raw in enumerate(packets):
        print(f'--- 包 #{pi+1} ({len(raw)} bytes) ---')
        
        # 尝试在任意位置找 zlib 流
        dec = try_decompress(raw)
        if dec:
            zlib_count += 1
            strs = find_strings(dec)
            print(f'  ✅ ZLIB 解压: {len(raw)} -> {len(dec)} bytes')
            
            # Hex dump
            for j in range(0, min(256, len(dec)), 16):
                c = dec[j:j+16]
                h = ' '.join(f'{b:02x}' for b in c)
                a = ''.join(chr(b) if 32 <= b < 127 else '.' for b in c)
                print(f'    {j:04x}: {h:<48s} {a}')
            if len(dec) > 256:
                print(f'    ... ({len(dec) - 256} more bytes)')
            
            if strs:
                print(f'  字符串({len(strs)}): {strs[:30]}')
        else:
            # 没有 zlib，显示原始内容
            try:
                text = raw.decode('ascii', errors='strict')
                print(f'  文本: {text[:200]}')
            except:
                # Hex dump
                for j in range(0, min(64, len(raw)), 16):
                    c = raw[j:j+16]
                    h = ' '.join(f'{b:02x}' for b in c)
                    a = ''.join(chr(b) if 32 <= b < 127 else '.' for b in c)
                    print(f'    {j:04x}: {h:<48s} {a}')
        
        print()
    
    print(f'总计: {len(packets)} 包, {zlib_count} 个 ZLIB 压缩包')

if __name__ == '__main__':
    main()
