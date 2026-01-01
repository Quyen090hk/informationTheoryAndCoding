# src/source_encoder.py
# 最终版静态 Huffman 信源编码器
# 支持二元自动扩展、退化信源特殊处理、详细输出

import argparse
import csv
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
    parser = CustomParser(description="Static Huffman Source Encoder (final version)")
    parser.add_argument("-v", "--verbose", action="store_true", help="enable detailed output")
    parser.add_argument("PMF", type=str, help="original probability CSV (2-bit or 256-bit)")
    parser.add_argument("INPUT", type=str, help="raw message file (.dat)")
    parser.add_argument("OUTPUT", type=str, help="compressed file (.huf)")
    return parser.parse_args()


def get_256_prob_file(original_pmf_path):
    """如果原PMF是二元，生成或读取对应的256元PMF文件（路径与byteSource一致）"""
    temp_dir = os.path.join("..", "data", "temp", "file_2bit_to_256bit")
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    base_name = os.path.basename(original_pmf_path)
    name_without_ext = os.path.splitext(base_name)[0]
    prob_256_path = os.path.join(temp_dir, f"{name_without_ext}.256.csv")

    if os.path.exists(prob_256_path):
        return prob_256_path

    # 生成256元概率
    prob_2bit = np.zeros(2)
    with open(original_pmf_path, newline='', encoding='utf-8') as f:
        for row in csv.reader(f):
            if row:
                prob_2bit[int(row[0])] = float(row[1])

    with open(prob_256_path, "w", newline='') as f:
        for i in range(256):
            count_1 = bin(i).count('1')
            count_0 = 8 - count_1
            p = (prob_2bit[0] ** count_0) * (prob_2bit[1] ** count_1)
            if p == 0:
                p = 0.0  # 避免写科学计数法
            f.write(f"{i},{p:.8f}\n")

    return prob_256_path


def main():
    args = setup_cli()
    verbose = args.verbose

    start_time = time.time()

    # 判断是二元还是256元
    with open(args.PMF) as f:
        num_lines = sum(1 for _ in f if _.strip())

    if num_lines == 2:
        prob_file = get_256_prob_file(args.PMF)
        if verbose:
            print(f"Detected 2-symbol source → using 256-symbol PMF: {prob_file}")
    else:
        prob_file = args.PMF

    # 读取256元频率
    frequencies = {}
    with open(prob_file, newline='', encoding='utf-8') as f:
        for row in csv.reader(f):
            if row:
                symbol = int(row[0])
                prob = float(row[1])
                if prob > 0:
                    frequencies[symbol] = prob

    if not frequencies:
        print("Error: No valid symbols with positive probability")
        sys.exit(1)

    # 创建编码器
    codec = HuffmanCodec.from_frequencies(frequencies)

    # 读取消息
    data = np.fromfile(args.INPUT, dtype=np.uint8)
    original_len = len(data)
    if original_len == 0:
        print("Error: Input file is empty")
        sys.exit(1)

    # 获取码表
    code_table = codec.get_code_table()

    # 特殊处理退化信源（概率全为1或0，导致唯一符号）
    if len(code_table) == 1:
        symbol = next(iter(code_table))
        bits, value = code_table[symbol]
        if bits == 0:  # 码长为0的情况（dahuffman有时会这样）
            code_table[symbol] = (1, 0)  # 强制码长1，码字"0"
            if verbose:
                print("Degenerate source detected → forcing code length 1 for unique symbol")

    # 编码（退化情况也正常编码）
    try:
        encoded_payload = codec.encode(data.tobytes())
    except Exception as e:
        print("Encoding failed:", e)
        sys.exit(1)

    # 构建头部
    header = bytearray()
    header.append(len(code_table) - 1)
    header.extend(original_len.to_bytes(4, 'little'))

    for symbol in sorted(code_table.keys()):
        bits, value = code_table[symbol]
        bytes_needed = (bits + 7) // 8
        header.append(symbol)
        header.append(bits)
        header.extend(value.to_bytes(bytes_needed, 'little'))

    header_size = len(header) + 2
    full_header = header_size.to_bytes(2, 'little') + header

    # 写入压缩文件
    with open(args.OUTPUT, 'wb') as f:
        f.write(full_header)
        f.write(encoded_payload)

    end_time = time.time()

    if verbose:
        total_bits = sum(bits * frequencies.get(sym, 0) * original_len for sym, (bits, _) in code_table.items())
        avg_len = total_bits / original_len if original_len else 0
        entropy = -sum(p * np.log2(p) for p in frequencies.values() if p > 0)

        print(f"[{end_time - start_time:.3f} sec] Encoding completed")
        print(f"    Original: {original_len} bytes")
        print(f"    Compressed: {len(full_header) + len(encoded_payload)} bytes → {args.OUTPUT}")
        print(f"    Avg code length: {avg_len:.4f} bits/symbol")
        print(f"    Entropy: {entropy:.4f} bits/symbol")


if __name__ == "__main__":
    main()