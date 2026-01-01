# src/source_decoder.py
# 最终版静态 Huffman 信源解码器
# 兼容 list/bytes 返回、退化信源

import argparse
import numpy as np
import sys
import os
import time
from dahuffman_no_EOF import HuffmanCodec


class CustomParser(argparse.ArgumentParser):
    def error(self, message):
        self.print_help()
        sys.exit(1)


def setup_cli():
    parser = CustomParser(description="Static Huffman Source Decoder (final version)")
    parser.add_argument("-v", "--verbose", action="store_true", help="enable detailed output")
    parser.add_argument("INPUT", type=str, help="compressed file (.huf)")
    parser.add_argument("OUTPUT", type=str, help="recovered file (.dat)")
    return parser.parse_args()


def main():
    args = setup_cli()
    verbose = args.verbose

    start_time = time.time()

    if not os.path.exists(args.INPUT):
        print(f"Error: {args.INPUT} not found")
        sys.exit(1)

    with open(args.INPUT, 'rb') as f:
        data = f.read()

    if len(data) < 6:
        print("Error: File too short")
        sys.exit(1)

    # 解析头部
    header_size = int.from_bytes(data[:2], 'little')
    header = data[2:header_size]
    payload = data[header_size:]

    pos = 0
    symbol_count = header[pos] + 1
    pos += 1
    original_len = int.from_bytes(header[pos:pos+4], 'little')
    pos += 4

    # 重建码表
    code_table = {}
    for _ in range(symbol_count):
        symbol = header[pos]
        bits = header[pos + 1]
        pos += 2
        bytes_needed = (bits + 7) // 8
        value = int.from_bytes(header[pos:pos + bytes_needed], 'little')
        code_table[symbol] = (bits, value)
        pos += bytes_needed

    # 特殊处理：如果码表只有一个符号且码长为0或1
    if len(code_table) == 1:
        symbol, (bits, value) = next(iter(code_table.items()))
        if bits <= 1:  # 包括0或1的情况
            # 直接填充该符号
            recovered = np.full(original_len, symbol, dtype=np.uint8)
            if verbose:
                print("Degenerate source detected → direct fill with unique symbol")
        else:
            codec = HuffmanCodec(code_table)
            decoded = codec.decode(payload)
            decoded_bytes = bytes(decoded[:original_len]) if isinstance(decoded, list) else decoded[:original_len]
            recovered = np.frombuffer(decoded_bytes, dtype=np.uint8)
    else:
        # 正常解码
        codec = HuffmanCodec(code_table)
        decoded = codec.decode(payload)
        decoded_bytes = bytes(decoded[:original_len]) if isinstance(decoded, list) else decoded[:original_len]
        recovered = np.frombuffer(decoded_bytes, dtype=np.uint8)

    # 写入恢复文件
    recovered.tofile(args.OUTPUT)

    end_time = time.time()

    if verbose:
        print(f"[{end_time - start_time:.3f} sec] Decoding completed")
        print(f"    Expected: {original_len} bytes")
        print(f"    Recovered: {len(recovered)} bytes → {args.OUTPUT}")
        print(f"    {'Perfect recovery!' if len(recovered) == original_len else 'Length mismatch!'}")

if __name__ == "__main__":
    main()